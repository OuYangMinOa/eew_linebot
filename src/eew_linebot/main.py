"""程式進入點：啟動 ngrok（選用）、EEW 監聽任務與 web server。"""

from __future__ import annotations

import asyncio
import logging
import os

from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from hypercorn.middleware import AsyncioWSGIMiddleware

from .app import create_app
from .config import Settings
from .eew_client import EEWClient
from .monitor import AlertMonitor
from .notifier import LineNotifier
from .subscribers import SubscriberStore

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()

    if os.environ.get("NGROK_AUTHTOKEN"):
        import ngrok

        listener = ngrok.forward(settings.port, authtoken_from_env=True)
        logger.info("ngrok url: %s", listener.url())

    asyncio.run(run(settings))


async def run(settings: Settings) -> None:
    store = SubscriberStore(settings.data_file).load()
    notifier = LineNotifier(settings.channel_access_token)
    monitor = AlertMonitor(settings, store, notifier, EEWClient(settings))
    flask_app = create_app(settings, store)

    tasks = [
        asyncio.create_task(monitor.watch(region), name=f"watch-{region}")
        for region in settings.regions
    ]
    if settings.develop_user_id:
        tasks.append(asyncio.create_task(monitor.send_startup_test(settings.develop_user_id)))

    server_config = HypercornConfig()
    server_config.bind = [f"0.0.0.0:{settings.port}"]
    try:
        await serve(AsyncioWSGIMiddleware(flask_app), server_config)
    finally:
        for task in tasks:
            task.cancel()
        await notifier.close()


if __name__ == "__main__":
    main()
