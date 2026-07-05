from eew_linebot.bot_logic import CLOSE_BUTTON, HELP_TEXT, handle_text
from eew_linebot.subscribers import SubscriberStore


def make_store(tmp_path) -> SubscriberStore:
    return SubscriberStore(tmp_path / "subs.txt").load()


def test_irrelevant_message_ignored(tmp_path):
    store = make_store(tmp_path)
    assert handle_text(store, "u1", "早安") is None


def test_help(tmp_path):
    store = make_store(tmp_path)
    reply = handle_text(store, "u1", "help")
    assert reply.text == HELP_TEXT
    assert reply.buttons[-1] == CLOSE_BUTTON


def test_menu_flow_subscribes(tmp_path):
    store = make_store(tmp_path)

    reply = handle_text(store, "u1", "地震 台灣")
    assert "區域" in reply.text
    assert ("北部", "地震 台灣 北部") in reply.buttons

    reply = handle_text(store, "u1", "地震 台灣 北部")
    assert ("臺北市", "地震 台灣 臺北市") in reply.buttons

    reply = handle_text(store, "u1", "地震 台灣 臺北市")
    assert "發生地震時" in reply.text
    assert store.get("u1").pos == "臺北市"


def test_close(tmp_path):
    store = make_store(tmp_path)
    reply = handle_text(store, "u1", "地震 關閉")
    assert reply.text == "👌"
    assert reply.buttons is None


def test_status_and_cancel(tmp_path):
    store = make_store(tmp_path)
    handle_text(store, "u1", "地震 日本")

    reply = handle_text(store, "u1", "地震 查詢")
    assert "日本" in reply.text
    assert ("取消日本", "地震 取消 日本") in reply.buttons

    reply = handle_text(store, "u1", "地震 取消 日本")
    assert "不再監測" in reply.text
    assert store.get("u1") is None
