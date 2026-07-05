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
