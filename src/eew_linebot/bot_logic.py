"""平台無關的對話邏輯：把使用者文字轉成「回覆文字＋按鈕」。

LINE（Quick Reply）與 Telegram（Inline Keyboard）都吃這一層，
按鈕統一表示成 (label, 點下去等同送出的指令文字)。
"""

from __future__ import annotations

from dataclasses import dataclass

from .geo import REGIONS
from .subscribers import COUNTRY_NAMES, Subscriber, SubscriberStore, parse_command

HELP_KEYWORDS = {"help", "幫助", "小俠", "歐陽小俠"}
HELP_TEXT = (
    "📖 使用方式\n"
    "・地震 台灣 — 用按鈕選區域和縣市\n"
    "・地震 台灣 台北 — 訂閱台灣警報，所在地台北\n"
    "・地震 台灣 all — 訂閱台灣全國\n"
    "・地震 日本 / 福建 / 四川 — 訂閱其他地區\n"
    "・地震 查詢 — 看目前訂閱\n"
    "・地震 取消 日本 — 取消訂閱\n\n"
    "所在地支援台灣所有縣市。\n"
    "各國發布警報的標準不一致，推薦台灣與福建。\n"
    "(此預警並非百分百精準)"
)

# (label, 點下去送出的指令文字)
Button = tuple[str, str]

DEFAULT_BUTTONS: list[Button] = [
    ("台灣", "地震 台灣"),
    ("日本", "地震 日本"),
    ("福建", "地震 福建"),
    ("我的訂閱", "地震 查詢"),
]
STATUS_BUTTON: Button = ("我的訂閱", "地震 查詢")
CLOSE_BUTTON: Button = ("關閉", "地震 關閉")
CLOSE_TEXT = CLOSE_BUTTON[1]

TW_REGION_BUTTONS: list[Button] = [("全國", "地震 台灣 all")] + [
    (region, f"地震 台灣 {region}") for region in REGIONS
]


@dataclass(frozen=True)
class Reply:
    text: str
    buttons: list[Button] | None = None


def _with_close(buttons: list[Button]) -> list[Button]:
    # 每排按鈕最右邊固定加「關閉」
    return [*buttons, CLOSE_BUTTON]


def county_buttons(region: str) -> list[Button]:
    return [(city, f"地震 台灣 {city}") for city in REGIONS[region]]


def cancel_buttons(sub: Subscriber | None) -> list[Button]:
    if sub is None or not sub.countries:
        return DEFAULT_BUTTONS
    return [
        (f"取消{COUNTRY_NAMES[c]}", f"地震 取消 {COUNTRY_NAMES[c]}")
        for c in sub.countries
    ] + [STATUS_BUTTON]


def status_text(sub: Subscriber | None) -> str:
    if sub is None or not sub.countries:
        return "你目前沒有任何訂閱。\n輸入「地震 台灣 台北」或點下面的按鈕開始訂閱！"
    lines = "\n".join(f"・{line}" for line in sub.status_lines())
    return f"你目前訂閱：\n{lines}\n\n取消請輸入「地震 取消 日本」這樣的格式，或點下面的按鈕。"


def handle_text(store: SubscriberStore, source_id: str, text: str) -> Reply | None:
    """處理一則使用者訊息；與本 bot 無關的訊息回傳 None（不回覆）。"""
    msg = text.strip().lower()
    if msg in HELP_KEYWORDS:
        return Reply(HELP_TEXT, _with_close(DEFAULT_BUTTONS))
    if not msg.startswith("地震"):
        return None

    command = msg[2:].strip()
    if not command:
        return Reply(HELP_TEXT, _with_close(DEFAULT_BUTTONS))

    cmd = parse_command(command)
    sub = store.get(source_id)

    if cmd is None:
        return Reply(
            f"看不懂「{command}」🤔\n試試：地震 台灣 台北\n完整說明請輸入「地震」",
            _with_close(DEFAULT_BUTTONS),
        )
    if cmd.action == "close":
        return Reply("👌")
    if cmd.action == "tw_menu":
        return Reply("要監測台灣哪個區域？", _with_close(TW_REGION_BUTTONS))
    if cmd.action == "tw_region":
        return Reply(f"選擇{cmd.pos}的縣市：", _with_close(county_buttons(cmd.pos)))
    if cmd.action == "status":
        return Reply(status_text(sub), _with_close(cancel_buttons(sub)))
    if cmd.action == "unsubscribe":
        if cmd.country is None:
            return Reply(
                "要取消哪一個？\n" + status_text(sub),
                _with_close(cancel_buttons(sub)),
            )
        return Reply(
            store.unsubscribe(source_id, cmd.country),
            _with_close(DEFAULT_BUTTONS),
        )
    return Reply(
        store.subscribe(source_id, cmd.country, cmd.pos),
        _with_close([STATUS_BUTTON]),
    )
