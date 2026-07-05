import asyncio

from eew_linebot.models import EEWData
from eew_linebot.monitor import AlertMonitor
from eew_linebot.subscribers import SubscriberStore


class FakeNotifier:
    def __init__(self):
        self.sent = []

    async def push_text(self, to, text):
        self.sent.append((to, text))
        return 200


def make_eew(event_id="e1", magnitude=5.6, origin_time="2026-01-01 00:00:00", **kwargs):
    defaults = dict(
        event_id=event_id,
        report_time=origin_time,
        origin_time=origin_time,
        hypocenter="花蓮縣近海",
        latitude=23.92,
        longitude=121.59,
        magnitude=magnitude,
        depth=40,
        max_intensity="4弱",
    )
    defaults.update(kwargs)
    return EEWData(**defaults)


def make_monitor(tmp_path):
    store = SubscriberStore(tmp_path / "subs.txt").load()
    store.subscribe("u1", "tw", "all")
    store.subscribe("u1", "fj")
    notifier = FakeNotifier()
    monitor = AlertMonitor(settings=None, store=store, notifier=notifier, client=None)
    return monitor, notifier


def test_same_event_similar_magnitude_not_resent(tmp_path):
    monitor, notifier = make_monitor(tmp_path)

    asyncio.run(monitor._handle(make_eew("e1", 5.6), "tw"))
    assert len(notifier.sent) == 1

    # 同 event_id、規模相同或只微幅變動（±0.2 內）→ 不重發
    asyncio.run(monitor._handle(make_eew("e1", 5.6), "tw"))
    asyncio.run(monitor._handle(make_eew("e1", 5.8), "tw"))
    asyncio.run(monitor._handle(make_eew("e1", 5.4), "tw"))
    assert len(notifier.sent) == 1

    # 同 event_id 但規模明顯上調 → 補發
    asyncio.run(monitor._handle(make_eew("e1", 6.0), "tw"))
    assert len(notifier.sent) == 2

    # 補發後基準更新為 6.0，再來 6.1 仍算類似 → 不重發
    asyncio.run(monitor._handle(make_eew("e1", 6.1), "tw"))
    assert len(notifier.sent) == 2


def test_new_event_window_rule(tmp_path):
    monitor, notifier = make_monitor(tmp_path)

    asyncio.run(monitor._handle(make_eew("e1", 5.6), "tw"))
    # 不同 event_id、60 秒內、規模較小 → 沿用時間窗規則不重發
    asyncio.run(monitor._handle(make_eew("e2", 5.0), "tw"))
    assert len(notifier.sent) == 1
    # 不同 event_id、60 秒內、規模更大 → 發
    asyncio.run(monitor._handle(make_eew("e3", 6.2), "tw"))
    assert len(notifier.sent) == 2


def test_fj_same_event_not_resent(tmp_path):
    monitor, notifier = make_monitor(tmp_path)

    asyncio.run(monitor._handle_fj(make_eew("f1", 5.6, "2026-01-01 00:00:00")))
    assert len(notifier.sent) == 1

    # 同 event_id 續報（時間相近、規模類似）→ 不重發
    asyncio.run(monitor._handle_fj(make_eew("f1", 5.7, "2026-01-01 00:00:10")))
    assert len(notifier.sent) == 1

    # 同 event_id 但規模明顯上調 → 補發
    asyncio.run(monitor._handle_fj(make_eew("f1", 6.0, "2026-01-01 00:00:20")))
    assert len(notifier.sent) == 2


def test_fj_suppressed_when_tw_already_reported(tmp_path):
    monitor, notifier = make_monitor(tmp_path)

    # 台灣先發布
    asyncio.run(monitor._handle(make_eew("e1", 5.6, "2026-01-01 00:00:00"), "tw"))
    assert len(notifier.sent) == 1

    # 福建在 120 秒內通報同一時段的地震 → 抑制
    asyncio.run(monitor._handle_fj(make_eew("f1", 5.6, "2026-01-01 00:00:30")))
    assert len(notifier.sent) == 1

    # 發震時間差超過 120 秒的福建地震 → 正常發
    asyncio.run(monitor._handle_fj(make_eew("f2", 5.6, "2026-01-01 00:10:00")))
    assert len(notifier.sent) == 2
