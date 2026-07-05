from eew_linebot.models import EEWData
from eew_linebot.subscribers import (
    Command,
    Subscriber,
    SubscriberStore,
    normalize_city,
    parse_command,
)


def make_eew(**kwargs) -> EEWData:
    defaults = dict(
        event_id="1",
        report_time="2026-01-01 00:00:00",
        origin_time="2026-01-01 00:00:00",
        hypocenter="花蓮縣近海",
        latitude=23.92,
        longitude=121.59,
        magnitude=5.6,
        depth=40,
        max_intensity="4弱",
    )
    defaults.update(kwargs)
    return EEWData(**defaults)


def test_normalize_city():
    assert normalize_city("台北") == "臺北市"
    assert normalize_city("臺北市") == "臺北市"
    assert normalize_city("all") == "all"
    assert normalize_city("全國") == "all"
    assert normalize_city("") == "all"
    assert normalize_city("火星") is None
    assert normalize_city(None) is None


def test_parse_command_subscribe():
    assert parse_command("台灣 台北") == Command("subscribe", "tw", "臺北市")
    assert parse_command("台灣 all") == Command("subscribe", "tw", "all")
    assert parse_command("台灣 全國") == Command("subscribe", "tw", "all")
    assert parse_command("日本") == Command("subscribe", "jp")
    assert parse_command("福建") == Command("subscribe", "fj")
    assert parse_command("四川") == Command("subscribe", "sc")
    assert parse_command("台北") == Command("subscribe", "tw", "臺北市")
    assert parse_command("台灣 火星") is None
    assert parse_command("胡言亂語") is None


def test_parse_command_menus():
    assert parse_command("台灣") == Command("tw_menu")
    assert parse_command("臺灣") == Command("tw_menu")
    assert parse_command("台灣 北部") == Command("tw_region", pos="北部")
    assert parse_command("東部") == Command("tw_region", pos="東部")
    assert parse_command("關閉") == Command("close")


def test_parse_command_status_and_cancel():
    assert parse_command("查詢") == Command("status")
    assert parse_command("我的訂閱") == Command("status")
    assert parse_command("取消 日本") == Command("unsubscribe", "jp")
    assert parse_command("取消台灣") == Command("unsubscribe", "tw")
    assert parse_command("取消") == Command("unsubscribe")
    assert parse_command("取消 火星") is None


def test_subscriber_serialization_roundtrip():
    sub = Subscriber("1234")
    sub.pos = "臺北市"
    sub.countries = ["tw", "jp"]
    assert sub.to_line() == "1234_臺北市_tw_jp"

    restored = Subscriber.from_line(sub.to_line())
    assert restored.id == "1234"
    assert restored.pos == "臺北市"
    assert restored.countries == ["tw", "jp"]

    no_pos = Subscriber.from_line("5678_None_jp")
    assert no_pos.pos is None


def test_subscribe_and_unsubscribe():
    sub = Subscriber("u1")
    assert "發生地震時" in sub.subscribe("tw", "臺北市")
    assert sub.countries == ["tw"] and sub.pos == "臺北市"

    # 改地點
    assert "所在地" in sub.subscribe("tw", "高雄市")
    assert sub.pos == "高雄市"

    # 加日本不影響台灣所在地
    sub.subscribe("jp")
    assert sub.pos == "高雄市"
    assert sub.countries == ["tw", "jp"]

    # 重複訂閱不再是取消，只提示已訂閱
    assert "已經在監測" in sub.subscribe("jp")
    assert sub.countries == ["tw", "jp"]

    assert "不再監測" in sub.unsubscribe("jp")
    assert sub.countries == ["tw"]
    assert "沒有訂閱" in sub.unsubscribe("jp")

    assert sub.status_lines() == ["台灣 - 高雄市"]


def test_store_roundtrip(tmp_path):
    path = tmp_path / "subs.txt"
    store = SubscriberStore(path).load()

    store.subscribe("u1", "tw", "臺北市")
    store.subscribe("u2", "jp")
    assert len(store) == 2
    assert store.get("u1").pos == "臺北市"
    assert store.get("u3") is None

    reloaded = SubscriberStore(path).load()
    assert len(reloaded) == 2

    # 取消最後一個訂閱後會從檔案移除
    reloaded.unsubscribe("u2", "jp")
    assert len(SubscriberStore(path).load()) == 1
    assert "沒有訂閱" in reloaded.unsubscribe("u9", "jp")


def test_regions_consistent_with_city_coords():
    from eew_linebot.geo import CITY_COORDS, REGIONS

    region_cities = [city for cities in REGIONS.values() for city in cities]
    assert sorted(region_cities) == sorted(CITY_COORDS)  # 不重複、不遺漏
    # LINE Quick Reply 上限 13 顆：最大的區 + 關閉鈕不能超過
    assert max(len(cities) for cities in REGIONS.values()) + 1 <= 13
    assert len(REGIONS) + 2 <= 13  # 區域選單：全國 + 各區 + 關閉


def test_wants_alert_tw():
    sub = Subscriber("u1")
    sub.countries = ["tw"]
    sub.pos = "all"
    assert sub.wants_alert(make_eew(), "tw")

    sub.pos = "花蓮縣"  # 離震央 < 60km，一定收到
    assert sub.wants_alert(make_eew(magnitude=3.0, max_intensity=1), "tw")

    sub.pos = "金門縣"  # 遠處小震不收
    assert not sub.wants_alert(make_eew(magnitude=4.0, max_intensity=2), "tw")
    assert sub.wants_alert(make_eew(magnitude=6.5, max_intensity=5), "tw")


def test_wants_alert_other_regions():
    sub = Subscriber("u1")
    sub.countries = ["jp", "fj", "sc"]
    assert sub.wants_alert(make_eew(max_intensity="5強"), "jp")
    assert not sub.wants_alert(make_eew(max_intensity="4弱"), "jp")
    assert sub.wants_alert(make_eew(magnitude=5.1), "fj")
    assert not sub.wants_alert(make_eew(magnitude=4.9), "fj")
    assert sub.wants_alert(make_eew(), "sc")
