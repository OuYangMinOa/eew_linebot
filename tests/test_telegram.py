import asyncio

from eew_linebot.bot_logic import CLOSE_TEXT
from eew_linebot.notifier import PushRouter
from eew_linebot.subscribers import SubscriberStore
from eew_linebot.telegram import TelegramBot, keyboard


class StubTelegramBot(TelegramBot):
    """把 Bot API 呼叫記下來，不真的打網路。"""

    def __init__(self, store):
        super().__init__("dummy-token", store)
        self.calls = []

    async def _api(self, method, **params):
        self.calls.append((method, params))
        return {}

    def methods(self):
        return [method for method, _ in self.calls]


def make_bot(tmp_path) -> StubTelegramBot:
    return StubTelegramBot(SubscriberStore(tmp_path / "subs.txt").load())


def test_keyboard_rows():
    buttons = [(f"b{i}", f"cmd{i}") for i in range(7)]
    rows = keyboard(buttons)["inline_keyboard"]
    assert [len(r) for r in rows] == [3, 3, 1]
    assert rows[0][0] == {"text": "b0", "callback_data": "cmd0"}


def test_message_subscribes_with_tg_prefix(tmp_path):
    bot = make_bot(tmp_path)
    update = {
        "update_id": 1,
        "message": {"chat": {"id": 12345}, "text": "地震 台灣 台北"},
    }
    asyncio.run(bot._handle_update(update))

    assert bot.store.get("tg:12345").pos == "臺北市"
    method, params = bot.calls[-1]
    assert method == "sendMessage"
    assert params["chat_id"] == 12345
    assert "發生地震時" in params["text"]
    assert "reply_markup" in params


def test_slash_commands_show_help(tmp_path):
    bot = make_bot(tmp_path)
    update = {"update_id": 1, "message": {"chat": {"id": 1}, "text": "/start"}}
    asyncio.run(bot._handle_update(update))
    assert "使用方式" in bot.calls[-1][1]["text"]


def test_callback_navigates_by_editing_message(tmp_path):
    bot = make_bot(tmp_path)
    update = {
        "update_id": 1,
        "callback_query": {
            "id": "cb1",
            "data": "地震 台灣",
            "message": {"chat": {"id": 1}, "message_id": 99},
        },
    }
    asyncio.run(bot._handle_update(update))
    assert bot.methods() == ["answerCallbackQuery", "editMessageText"]
    _, params = bot.calls[-1]
    assert params["message_id"] == 99
    assert "區域" in params["text"]


def test_callback_close_removes_keyboard(tmp_path):
    bot = make_bot(tmp_path)
    update = {
        "update_id": 1,
        "callback_query": {
            "id": "cb1",
            "data": CLOSE_TEXT,
            "message": {"chat": {"id": 1}, "message_id": 99},
        },
    }
    asyncio.run(bot._handle_update(update))
    assert bot.methods() == ["answerCallbackQuery", "editMessageReplyMarkup"]


def test_push_router_routes_by_prefix(tmp_path):
    sent = []

    class FakeLine:
        async def push_text(self, to, text):
            sent.append(("line", to))
            return 200

    bot = make_bot(tmp_path)
    router = PushRouter(FakeLine(), bot)

    asyncio.run(router.push_text("U1234", "hi"))
    asyncio.run(router.push_text("tg:5678", "hi"))

    assert sent == [("line", "U1234")]
    assert bot.calls[-1][0] == "sendMessage"
    assert bot.calls[-1][1]["chat_id"] == "5678"


def test_push_router_telegram_disabled(tmp_path):
    class FakeLine:
        async def push_text(self, to, text):
            raise AssertionError("should not reach LINE")

    router = PushRouter(FakeLine(), telegram=None)
    assert asyncio.run(router.push_text("tg:5678", "hi")) == 0
