"""wolfx EEW WebSocket 客戶端：連線、斷線重連、把 JSON 轉成 EEWData。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import websockets
from opencc import OpenCC

from .config import Settings
from .models import EEWData

logger = logging.getLogger(__name__)

RECONNECT_DELAY_S = 0.5


class EEWClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cc = OpenCC("s2tw")  # 簡體轉繁體（震央名稱）

    async def stream(self, region: str) -> AsyncIterator[EEWData]:
        """持續產出指定地區的 EEW 警報，斷線自動重連。"""
        url = self.settings.ws_url(region)
        while True:
            try:
                async with websockets.connect(url) as websocket:
                    logger.info("[%s] connected to %s", region, url)
                    async for raw in websocket:
                        data = json.loads(raw)
                        if data.get("type") == "heartbeat":
                            continue
                        yield self._parse(data, region)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[%s] connection closed: %s, reconnecting", region, exc)
                await asyncio.sleep(RECONNECT_DELAY_S)

    def _parse(self, data: dict, region: str) -> EEWData:
        # 注意：'Magunitude' 是 wolfx API 本身的拼字
        if region == "jp":
            return EEWData(
                event_id=str(data["EventID"]),
                report_time=data["AnnouncedTime"],
                origin_time=data["OriginTime"],
                hypocenter=data["Hypocenter"],
                latitude=data["Latitude"],
                longitude=data["Longitude"],
                magnitude=data["Magunitude"],
                depth=data["Depth"],
                max_intensity=data["MaxIntensity"],
            )
        if region == "fj":
            return EEWData(
                event_id=str(data["EventID"]),
                report_time=data["ReportTime"],
                origin_time=data["OriginTime"],
                hypocenter=self._cc.convert(data["HypoCenter"]),
                latitude=data["Latitude"],
                longitude=data["Longitude"],
                magnitude=data["Magunitude"],
                depth=None,
                max_intensity=None,
            )
        return EEWData(
            event_id=str(data["ID"]),
            report_time=data["ReportTime"],
            origin_time=data["OriginTime"],
            hypocenter=self._cc.convert(data["HypoCenter"]),
            latitude=data["Latitude"],
            longitude=data["Longitude"],
            magnitude=data["Magunitude"],
            depth=data["Depth"],
            max_intensity=data["MaxIntensity"],
        )
