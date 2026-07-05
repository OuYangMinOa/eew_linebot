"""LINE webhook（Flask app factory）。"""

from __future__ import annotations

import logging

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessageAction,
    MessagingApi,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from .config import Settings
from .geo import REGIONS
from .subscribers import COUNTRY_NAMES, Subscriber, SubscriberStore, parse_command

logger = logging.getLogger(__name__)

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

# (label, 點下去送出的文字)
DEFAULT_BUTTONS = [
    ("台灣", "地震 台灣"),
    ("日本", "地震 日本"),
    ("福建", "地震 福建"),
    ("我的訂閱", "地震 查詢"),
]
STATUS_BUTTON = ("我的訂閱", "地震 查詢")
CLOSE_BUTTON = ("關閉", "地震 關閉")

TW_REGION_BUTTONS = [("全國", "地震 台灣 all")] + [
    (region, f"地震 台灣 {region}") for region in REGIONS
]


def _county_buttons(region: str) -> list[tuple[str, str]]:
    return [(city, f"地震 台灣 {city}") for city in REGIONS[region]]


def _quick_reply(buttons: list[tuple[str, str]]) -> QuickReply:
    # 每排按鈕最右邊固定加「關閉」收起選單
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label=label, text=text))
            for label, text in [*buttons, CLOSE_BUTTON]
        ]
    )


def _cancel_buttons(sub: Subscriber | None) -> list[tuple[str, str]]:
    if sub is None:
        return DEFAULT_BUTTONS
    buttons = [
        (f"取消{COUNTRY_NAMES[c]}", f"地震 取消 {COUNTRY_NAMES[c]}")
        for c in sub.countries
    ]
    return buttons + [STATUS_BUTTON] if buttons else DEFAULT_BUTTONS


def _status_text(sub: Subscriber | None) -> str:
    if sub is None or not sub.countries:
        return "你目前沒有任何訂閱。\n輸入「地震 台灣 台北」或點下面的按鈕開始訂閱！"
    lines = "\n".join(f"・{line}" for line in sub.status_lines())
    return f"你目前訂閱：\n{lines}\n\n取消請輸入「地震 取消 日本」這樣的格式，或點下面的按鈕。"


def _source_id(event: MessageEvent) -> str:
    """推播對象：群組/聊天室用群組 id，一對一用 user id。"""
    source = event.source
    return (
        getattr(source, "group_id", None)
        or getattr(source, "room_id", None)
        or source.user_id
    )


def create_app(settings: Settings, store: SubscriberStore) -> Flask:
    app = Flask(__name__)
    configuration = Configuration(access_token=settings.channel_access_token)
    handler = WebhookHandler(settings.channel_secret)

    def reply(
        reply_token: str,
        text: str,
        buttons: list[tuple[str, str]] | None = None,
    ) -> None:
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[
                        TextMessage(
                            text=text,
                            quick_reply=_quick_reply(buttons) if buttons else None,
                        )
                    ],
                )
            )

    @app.get("/")
    def home():
        return "OK"

    @app.post("/callback")
    def callback():
        signature = request.headers.get("X-Line-Signature", "")
        body = request.get_data(as_text=True)
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            logger.warning("invalid signature, check channel secret / access token")
            abort(400)
        return "OK"

    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event: MessageEvent) -> None:
        msg = event.message.text.strip().lower()
        source_id = _source_id(event)
        logger.info("message from %s: %s", source_id, msg)

        if msg in HELP_KEYWORDS:
            reply(event.reply_token, HELP_TEXT, DEFAULT_BUTTONS)
            return
        if not msg.startswith("地震"):
            return

        command = msg[2:].strip()
        if not command:
            reply(event.reply_token, HELP_TEXT, DEFAULT_BUTTONS)
            return

        cmd = parse_command(command)
        sub = store.get(source_id)

        if cmd is None:
            reply(
                event.reply_token,
                f"看不懂「{command}」🤔\n"
                "試試：地震 台灣 台北\n"
                "完整說明請輸入「地震」",
                DEFAULT_BUTTONS,
            )
        elif cmd.action == "close":
            reply(event.reply_token, "👌")
        elif cmd.action == "tw_menu":
            reply(event.reply_token, "要監測台灣哪個區域？", TW_REGION_BUTTONS)
        elif cmd.action == "tw_region":
            reply(event.reply_token, f"選擇{cmd.pos}的縣市：", _county_buttons(cmd.pos))
        elif cmd.action == "status":
            reply(event.reply_token, _status_text(sub), _cancel_buttons(sub))
        elif cmd.action == "unsubscribe":
            if cmd.country is None:
                reply(
                    event.reply_token,
                    "要取消哪一個？\n" + _status_text(sub),
                    _cancel_buttons(sub),
                )
            else:
                reply(
                    event.reply_token,
                    store.unsubscribe(source_id, cmd.country),
                    DEFAULT_BUTTONS,
                )
        else:
            reply(
                event.reply_token,
                store.subscribe(source_id, cmd.country, cmd.pos),
                [STATUS_BUTTON],
            )

    return app
