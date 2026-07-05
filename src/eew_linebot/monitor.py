"""監聽各地區 EEW，過濾重複警報後推播給符合條件的訂閱者。"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from .config import Settings
from .eew_client import EEWClient
from .models import EEWData
from .notifier import LineNotifier
from .subscribers import SubscriberStore

logger = logging.getLogger(__name__)

ORIGIN_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S")


def parse_origin_time(origin_time: str) -> datetime | None:
    for fmt in ORIGIN_TIME_FORMATS:
        try:
            return datetime.strptime(origin_time, fmt)
        except ValueError:
            continue
    return None


class AlertMonitor:
    # 同地區 60 秒內、規模沒有變大的續報不重發
    RESEND_WINDOW_S = 60
    # 台灣（CWA）已發布的地震，120 秒內不再重複發福建警報
    FJ_SUPPRESS_S = 120
    # 續報規模要比上次「發送出去」的大超過這個值，才視為需要補發
    MAG_STEP = 0.2

    def __init__(
        self,
        settings: Settings,
        store: SubscriberStore,
        notifier: LineNotifier,
        client: EEWClient,
    ) -> None:
        self.settings = settings
        self.store = store
        self.notifier = notifier
        self.client = client
        # 以下三個記錄的是「上一次實際發送」的事件 id / 規模 / 時間
        self._last_event_id: dict[str, str] = {}
        self._last_magnitude: dict[str, float] = defaultdict(float)
        self._last_sent_at: dict[str, datetime] = {}
        self._last_tw_origin: datetime | None = None
        # 福建的逐報記錄（不論有沒有發送）
        self._last_fj_origin: datetime | None = None
        self._last_fj_magnitude: float | None = None

    async def watch(self, region: str) -> None:
        logger.info("start watching %s", region)
        async for eew in self.client.stream(region):
            logger.info("[%s] %s", region, eew)
            try:
                if region == "fj":
                    await self._handle_fj(eew)
                else:
                    await self._handle(eew, region)
            except Exception:
                logger.exception("[%s] failed to handle alert", region)

    def _is_repeat_of_sent_event(self, eew: EEWData, region: str) -> bool:
        """第一道去重：同一事件（event_id 相同）的續報，規模沒有明顯上調就視為重複。"""
        magnitude = eew.magnitude or 0.0
        return (
            eew.event_id == self._last_event_id.get(region)
            and magnitude <= self._last_magnitude[region] + self.MAG_STEP
        )

    async def _handle(self, eew: EEWData, region: str) -> None:
        magnitude = eew.magnitude or 0.0
        if self._is_repeat_of_sent_event(eew, region):
            return
        # 第二道去重：不同事件但 60 秒內、規模比上次發送的小
        last_sent = self._last_sent_at.get(region)
        in_window = (
            last_sent is not None
            and (datetime.now() - last_sent).total_seconds() < self.RESEND_WINDOW_S
        )
        if in_window and magnitude < self._last_magnitude[region]:
            # 續報仍刷新時間窗，避免一長串續報結束後又被重發
            self._last_sent_at[region] = datetime.now()
            return
        await self._broadcast(eew, region)
        self._mark_sent(eew, region)
        if region == "tw":
            self._last_tw_origin = parse_origin_time(eew.origin_time)

    def _mark_sent(self, eew: EEWData, region: str) -> None:
        self._last_event_id[region] = eew.event_id
        self._last_magnitude[region] = eew.magnitude or 0.0
        self._last_sent_at[region] = datetime.now()

    async def _handle_fj(self, eew: EEWData) -> None:
        origin = parse_origin_time(eew.origin_time)
        magnitude = eew.magnitude or 0.0
        if self._is_repeat_of_sent_event(eew, "fj"):
            self._last_fj_origin = origin
            self._last_fj_magnitude = magnitude
            return
        not_covered_by_tw = (
            origin is None
            or self._last_tw_origin is None
            or (origin - self._last_tw_origin).total_seconds() > self.FJ_SUPPRESS_S
        )
        is_new_event = (
            origin is None
            or self._last_fj_origin is None
            or (origin - self._last_fj_origin).total_seconds() > self.FJ_SUPPRESS_S
            or (
                self._last_fj_magnitude is not None
                and magnitude > self._last_fj_magnitude + self.MAG_STEP
            )
        )
        if not_covered_by_tw and is_new_event:
            await self._broadcast(eew, "fj")
            self._mark_sent(eew, "fj")
        self._last_fj_origin = origin
        self._last_fj_magnitude = magnitude

    async def _broadcast(self, eew: EEWData, region: str) -> None:
        text = eew.to_text()
        targets = []
        for sub in self.store:
            if region not in sub.countries:
                continue
            try:
                if sub.wants_alert(eew, region):
                    targets.append(sub.id)
            except Exception:
                logger.exception("threshold check failed for %r", sub)
        if not targets:
            logger.info("[%s] no subscribers matched: %s", region, eew.hypocenter)
            return
        logger.info("[%s] pushing alert to %d subscribers", region, len(targets))
        results = await asyncio.gather(
            *(self.notifier.push_text(to, text) for to in targets),
            return_exceptions=True,
        )
        for to, result in zip(targets, results):
            if isinstance(result, Exception):
                logger.error("push to %s failed: %s", to, result)

    async def send_startup_test(self, to: str) -> None:
        """開機時發一筆測試警報給開發者，確認推播路徑正常。"""
        eew = EEWData(
            event_id="startup-test",
            report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            origin_time=datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
            hypocenter="臺灣東部海域（啟動測試）",
            latitude=23.92,
            longitude=121.59,
            magnitude=5.6,
            depth=40,
            max_intensity="4弱",
        )
        status = await self.notifier.push_text(to, eew.to_text())
        logger.info("startup test push to %s -> %d", to, status)
