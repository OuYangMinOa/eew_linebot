from pathlib import Path

from eew_linebot.app import create_app
from eew_linebot.config import Settings
from eew_linebot.subscribers import SubscriberStore


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        channel_secret="test-secret",
        channel_access_token="test-token",
        develop_user_id=None,
        port=9031,
        ws_relay="",
        regions=("tw",),
        data_file=tmp_path / "subs.txt",
    )


def test_home_returns_ok(tmp_path):
    settings = make_settings(tmp_path)
    app = create_app(settings, SubscriberStore(settings.data_file).load())
    response = app.test_client().get("/")
    assert response.status_code == 200


def test_callback_rejects_bad_signature(tmp_path):
    settings = make_settings(tmp_path)
    app = create_app(settings, SubscriberStore(settings.data_file).load())
    response = app.test_client().post(
        "/callback",
        data="{}",
        headers={"X-Line-Signature": "bad"},
    )
    assert response.status_code == 400
