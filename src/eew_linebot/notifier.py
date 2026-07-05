"""LINE push 訊息（async，共用一個 aiohttp session）。"""

from __future__ import annotations

import logging

import aiohttp

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LineNotifier:
    def __init__(self, channel_access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {channel_access_token}",
            "Content-Type": "application/json",
        }
        self._session: aiohttp.ClientSession | None = None

    async def push_text(self, to: str, text: str) -> int:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        body = {"to": to, "messages": [{"type": "text", "text": text}]}
        async with self._session.post(LINE_PUSH_URL, headers=self._headers, json=body) as resp:
            if resp.status != 200:
                logger.error("push to %s failed (%d): %s", to, resp.status, await resp.text())
            return resp.status

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


class PushRouter:
    """依訂閱者 id 前綴（tg: 開頭是 Telegram）把推播分流到對應平台。"""

    def __init__(self, line: LineNotifier, telegram=None) -> None:
        self._line = line
        self._telegram = telegram

    async def push_text(self, to: str, text: str) -> int:
        from .telegram import SUBSCRIBER_PREFIX

        if to.startswith(SUBSCRIBER_PREFIX):
            if self._telegram is None:
                logger.warning("telegram 未啟用，無法推播給 %s", to)
                return 0
            return await self._telegram.send_text(to[len(SUBSCRIBER_PREFIX):], text)
        return await self._line.push_text(to, text)
