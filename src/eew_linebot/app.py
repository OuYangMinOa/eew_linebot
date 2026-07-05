"""LINE webhook（Flask app factory）：把 bot_logic 的回覆渲染成 Quick Reply。"""

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

from .bot_logic import Button, handle_text
from .config import Settings
from .subscribers import SubscriberStore

logger = logging.getLogger(__name__)


def _source_id(event: MessageEvent) -> str:
    """推播對象：群組/聊天室用群組 id，一對一用 user id。"""
    source = event.source
    return (
        getattr(source, "group_id", None)
        or getattr(source, "room_id", None)
        or source.user_id
    )


def _quick_reply(buttons: list[Button]) -> QuickReply:
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label=label, text=text))
            for label, text in buttons
        ]
    )


def create_app(settings: Settings, store: SubscriberStore) -> Flask:
    app = Flask(__name__)
    configuration = Configuration(access_token=settings.channel_access_token)
    handler = WebhookHandler(settings.channel_secret)

    def reply(reply_token: str, text: str, buttons: list[Button] | None = None) -> None:
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
        source_id = _source_id(event)
        logger.info("message from %s: %s", source_id, event.message.text)
        result = handle_text(store, source_id, event.message.text)
        if result is not None:
            reply(event.reply_token, result.text, result.buttons)

    return app
