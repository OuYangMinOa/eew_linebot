"""Telegram bot（長輪詢）：與 LINE 共用 bot_logic 的指令邏輯與訂閱資料。

訂閱者 id 存成 "tg:<chat_id>"，推播由 PushRouter 依前綴分流。
按鈕渲染成 Inline Keyboard，點按觸發 callback：
- 選單導覽直接編輯原訊息（聊天室不會被選單洗版）
- 「關閉」把原訊息的鍵盤移除
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .bot_logic import CLOSE_TEXT, Button, handle_text
from .subscribers import SubscriberStore

logger = logging.getLogger(__name__)

SUBSCRIBER_PREFIX = "tg:"
POLL_TIMEOUT_S = 50
RETRY_DELAY_S = 3
BUTTONS_PER_ROW = 3


def keyboard(buttons: list[Button]) -> dict:
    rows = [
        [
            {"text": label, "callback_data": text}
            for label, text in buttons[i : i + BUTTONS_PER_ROW]
        ]
        for i in range(0, len(buttons), BUTTONS_PER_ROW)
    ]
    return {"inline_keyboard": rows}


class TelegramBot:
    def __init__(self, token: str, store: SubscriberStore) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self.store = store
        self._session: aiohttp.ClientSession | None = None
        self._offset = 0

    async def _api(self, method: str, **params):
        """呼叫 Bot API；失敗回傳 None（記 log 不拋出）。"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=POLL_TIMEOUT_S + 20)
            self._session = aiohttp.ClientSession(timeout=timeout)
        async with self._session.post(f"{self._base}/{method}", json=params) as resp:
            data = await resp.json()
            if not data.get("ok"):
                logger.error("telegram %s failed: %s", method, data.get("description"))
                return None
            return data.get("result")

    async def send_text(
        self, chat_id: int | str, text: str, buttons: list[Button] | None = None
    ) -> int:
        params: dict = {"chat_id": chat_id, "text": text}
        if buttons:
            params["reply_markup"] = keyboard(buttons)
        result = await self._api("sendMessage", **params)
        return 200 if result is not None else 0

    async def poll(self) -> None:
        logger.info("telegram long polling started")
        while True:
            try:
                updates = await self._api(
                    "getUpdates",
                    offset=self._offset,
                    timeout=POLL_TIMEOUT_S,
                    allowed_updates=["message", "callback_query"],
                )
                if updates is None:  # API 錯誤（如 token 無效），別無延遲狂打
                    await asyncio.sleep(RETRY_DELAY_S)
                    continue
                for update in updates:
                    self._offset = update["update_id"] + 1
                    try:
                        await self._handle_update(update)
                    except Exception:
                        logger.exception("telegram update failed: %s", update)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("telegram poll error: %s", exc)
                await asyncio.sleep(RETRY_DELAY_S)

    async def _handle_update(self, update: dict) -> None:
        if "message" in update:
            await self._handle_message(update["message"])
        elif "callback_query" in update:
            await self._handle_callback(update["callback_query"])

    async def _handle_message(self, message: dict) -> None:
        text = message.get("text")
        if not text:
            return
        if text.startswith(("/start", "/help")):
            text = "help"
        chat_id = message["chat"]["id"]
        logger.info("telegram message from %s: %s", chat_id, text)
        result = handle_text(self.store, f"{SUBSCRIBER_PREFIX}{chat_id}", text)
        if result is not None:
            await self.send_text(chat_id, result.text, result.buttons)

    async def _handle_callback(self, query: dict) -> None:
        await self._api("answerCallbackQuery", callback_query_id=query["id"])
        message = query.get("message")
        data = query.get("data", "")
        if message is None:
            return
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]

        if data == CLOSE_TEXT:
            await self._api(
                "editMessageReplyMarkup", chat_id=chat_id, message_id=message_id
            )
            return

        result = handle_text(self.store, f"{SUBSCRIBER_PREFIX}{chat_id}", data)
        if result is None:
            return
        params: dict = {"chat_id": chat_id, "message_id": message_id, "text": result.text}
        if result.buttons:
            params["reply_markup"] = keyboard(result.buttons)
        edited = await self._api("editMessageText", **params)
        if edited is None:  # 訊息太舊等原因不能編輯時，改發新訊息
            await self.send_text(chat_id, result.text, result.buttons)

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
