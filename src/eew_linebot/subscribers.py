"""訂閱者模型、指令解析與檔案存取。

檔案格式維持與舊版相容：每行 `{id}_{pos}_{country1}_{country2}...`。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .geo import CITY_COORDS, REGIONS, haversine_km
from .models import EEWData, parse_intensity

logger = logging.getLogger(__name__)

COUNTRY_NAMES = {"tw": "台灣", "jp": "日本", "sc": "四川", "fj": "福建"}
COMMAND_PREFIXES = {"日本": "jp", "四川": "sc", "福建": "fj"}
STATUS_KEYWORDS = {"查詢", "狀態", "訂閱", "我的訂閱"}


def normalize_city(text: str | None) -> str | None:
    """把使用者輸入轉成標準縣市名；"all"/"全國"/空字串代表全國，無法辨識回傳 None。"""
    if text is None:
        return None
    text = text.strip()
    if text.lower() == "all" or text in ("全國", ""):
        return "all"
    text = text.replace("台", "臺")
    for city in CITY_COORDS:
        if text in city or city in text:
            return city
    return None


@dataclass(frozen=True)
class Command:
    # "subscribe" | "unsubscribe" | "status" | "tw_menu" | "tw_region" | "close"
    action: str
    country: str | None = None
    pos: str | None = None


def parse_country(text: str) -> str | None:
    text = text.strip()
    if text.startswith(("台灣", "臺灣")):
        return "tw"
    for prefix, code in COMMAND_PREFIXES.items():
        if text.startswith(prefix):
            return code
    return None


def parse_command(command: str) -> Command | None:
    """解析「地震」後面的指令；無法解析回傳 None。

    支援格式：
    - 訂閱：「台灣 台北」、「日本」、「四川」、「福建」，或直接輸入縣市名
    - 選單：「台灣」（選區域）、「台灣 北部」（選縣市）、「關閉」（收起按鈕）
    - 查詢：「查詢」、「狀態」、「我的訂閱」
    - 取消：「取消 日本」（只打「取消」會列出可取消的訂閱）
    """
    command = command.strip()
    if command == "關閉":
        return Command("close")
    if command in STATUS_KEYWORDS:
        return Command("status")
    if command.startswith("取消"):
        rest = command[2:].strip()
        if not rest:
            return Command("unsubscribe")
        country = parse_country(rest)
        return Command("unsubscribe", country) if country else None
    country = parse_country(command)
    if country == "tw":
        rest = command.replace("臺灣", "", 1).replace("台灣", "", 1).strip()
        if not rest:
            return Command("tw_menu")
        if rest in REGIONS:
            return Command("tw_region", pos=rest)
        city = normalize_city(rest)
        return Command("subscribe", "tw", city) if city else None
    if country is not None:
        return Command("subscribe", country)
    if command in REGIONS:
        return Command("tw_region", pos=command)
    city = normalize_city(command)
    if city is not None:
        return Command("subscribe", "tw", city)
    return None


class Subscriber:
    def __init__(self, id: str) -> None:
        self.id = id
        self.pos: str | None = None
        self.countries: list[str] = []

    def __repr__(self) -> str:
        return f"Subscriber({self.to_line()})"

    def to_line(self) -> str:
        return "_".join([self.id, str(self.pos), *self.countries])

    @classmethod
    def from_line(cls, line: str) -> Subscriber:
        parts = line.strip().split("_")
        sub = cls(parts[0])
        sub.pos = None if parts[1] == "None" else parts[1]
        sub.countries = parts[2:]
        return sub

    def pos_label(self) -> str:
        return "全國" if self.pos in (None, "all") else self.pos

    def status_lines(self) -> list[str]:
        """目前訂閱的條列，例如 ["台灣 - 臺北市", "日本"]。"""
        lines = []
        for country in self.countries:
            if country == "tw":
                lines.append(f"台灣 - {self.pos_label()}")
            else:
                lines.append(COUNTRY_NAMES[country])
        return lines

    def subscribe(self, country: str, pos: str | None = None) -> str:
        """新增或更新訂閱，回傳給使用者的回覆文字。"""
        if country not in self.countries:
            self.countries.append(country)
            if country == "tw":
                self.pos = pos
            return (
                f"好的！發生地震時，我會提醒您 🔔\n"
                f"目前訂閱：\n{self._status_block()}\n"
                "(此預警並非百分百精準)"
            )
        if country == "tw" and pos != self.pos:
            old_label = self.pos_label()
            self.pos = pos
            return f"好的，已更改你在台灣的所在地：\n{old_label} -> {self.pos_label()}"
        return (
            f"已經在監測 {COUNTRY_NAMES[country]} 了！\n"
            f"取消請輸入「地震 取消 {COUNTRY_NAMES[country]}」"
        )

    def unsubscribe(self, country: str) -> str:
        if country not in self.countries:
            return f"你沒有訂閱 {COUNTRY_NAMES[country]} 喔"
        self.countries.remove(country)
        return f"好的，將不再監測 {COUNTRY_NAMES[country]}"

    def _status_block(self) -> str:
        return "\n".join(f"・{line}" for line in self.status_lines())

    def wants_alert(self, eew: EEWData, region: str) -> bool:
        """依地區與訂閱者所在地判斷這筆警報是否要推播。"""
        if region == "jp":
            intensity = parse_intensity(eew.max_intensity)
            return intensity is not None and intensity >= 5
        if region == "sc":
            return True
        if region == "fj":
            return eew.magnitude is not None and eew.magnitude > 5

        # tw：依震央與所在縣市的距離分級過濾
        if self.pos in (None, "all"):
            return True
        if eew.latitude is None or eew.longitude is None:
            return True
        lat, lon = CITY_COORDS[self.pos]
        distance = haversine_km(eew.latitude, eew.longitude, lat, lon)
        intensity = parse_intensity(eew.max_intensity) or 0
        magnitude = eew.magnitude or 0
        if distance < 60:
            return True
        if distance < 100:
            return (magnitude >= 4.8 and intensity >= 3) or intensity >= 4
        if distance < 180:
            return (magnitude >= 5 and intensity >= 4) or intensity >= 5
        return (magnitude >= 6 and intensity >= 4) or intensity >= 5


class SubscriberStore:
    """訂閱者的記憶體快取 + 檔案持久化。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._subs: dict[str, Subscriber] = {}

    def load(self) -> SubscriberStore:
        self._subs.clear()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    sub = Subscriber.from_line(line)
                    self._subs[sub.id] = sub
        logger.info("loaded %d subscribers from %s", len(self._subs), self.path)
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(f"{sub.to_line()}\n" for sub in self._subs.values())
        self.path.write_text(content, encoding="utf-8")

    def get(self, source_id: str) -> Subscriber | None:
        return self._subs.get(source_id)

    def subscribe(self, source_id: str, country: str, pos: str | None = None) -> str:
        sub = self._subs.setdefault(source_id, Subscriber(source_id))
        notify = sub.subscribe(country, pos)
        self.save()
        return notify

    def unsubscribe(self, source_id: str, country: str) -> str:
        sub = self._subs.get(source_id)
        if sub is None:
            return f"你沒有訂閱 {COUNTRY_NAMES[country]} 喔"
        notify = sub.unsubscribe(country)
        if not sub.countries:
            del self._subs[source_id]
        self.save()
        return notify

    def __iter__(self):
        # 回傳快照，webhook 執行緒寫入時 monitor 端仍可安全迭代
        return iter(list(self._subs.values()))

    def __len__(self) -> int:
        return len(self._subs)
