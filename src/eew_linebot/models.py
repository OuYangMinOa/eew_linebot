"""EEW 資料模型與推播訊息格式。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

WHITE = "⚪"
GREEN = "🟢"
BLUE = "🔵"
RED = "🔴"
YELLOW = "🟡"

Intensity = int | float | str | None


def parse_intensity(value: Intensity) -> int | None:
    """各地區 API 的最大震度可能是數字或字串（如 "4弱"），統一轉成整數級數。"""
    if isinstance(value, (int, float)):
        return math.floor(value)
    if isinstance(value, str) and value[:1].isdigit():
        return int(value[0])
    return None


def depth_icon(depth: float | None) -> str:
    if depth is None or depth > 300:
        return WHITE
    if depth > 70:
        return GREEN
    if depth > 30:
        return BLUE
    return RED


def magnitude_icon(magnitude: float | None) -> str:
    if magnitude is None or magnitude < 4:
        return WHITE
    if magnitude < 5:
        return YELLOW
    return RED


def intensity_icon(value: Intensity) -> str:
    intensity = parse_intensity(value)
    icons = {1: WHITE, 2: BLUE, 3: GREEN, 4: YELLOW}
    if intensity is None:
        return WHITE
    return icons.get(intensity, RED)


@dataclass
class EEWData:
    event_id: str
    report_time: str
    origin_time: str
    hypocenter: str
    latitude: float | None
    longitude: float | None
    magnitude: float | None
    depth: float | None
    max_intensity: Intensity

    def to_text(self) -> str:
        return (
            f"{self.hypocenter} 發生規模{self.magnitude}有感地震, 最大震度{self.max_intensity}級\n"
            f"發生時間  :  {self.origin_time}\n"
            f"地震規模  :  {magnitude_icon(self.magnitude)} 芮氏 {self.magnitude}\n"
            f"地震深度  :  {depth_icon(self.depth)} {self.depth}公里\n"
            f"最大震度  :  {intensity_icon(self.max_intensity)} {self.max_intensity}級\n"
            f"震央位置  :  {self.hypocenter}\n\n"
            f"💭 發布於：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
        )
