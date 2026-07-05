"""環境變數與應用程式設定。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_PORT = 9031
DEFAULT_REGIONS = "tw,jp,fj"
DEFAULT_WS_RELAY = "ws://localhost:8080/relay"

# wolfx 各地區 EEW WebSocket 來源
WS_SOURCES = {
    "tw": "wss://ws-api.wolfx.jp/cwa_eew",
    "jp": "wss://ws-api.wolfx.jp/jma_eew",
    "fj": "wss://ws-api.wolfx.jp/fj_eew",
    "sc": "wss://ws-api.wolfx.jp/sc_eew",
}


@dataclass(frozen=True)
class Settings:
    channel_secret: str
    channel_access_token: str
    develop_user_id: str | None
    port: int
    ws_relay: str
    regions: tuple[str, ...]
    data_file: Path

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        regions = tuple(
            r.strip()
            for r in os.environ.get("EEW_REGIONS", DEFAULT_REGIONS).split(",")
            if r.strip()
        )
        unknown = set(regions) - set(WS_SOURCES)
        if unknown:
            raise ValueError(f"unknown EEW_REGIONS: {', '.join(sorted(unknown))}")
        return cls(
            channel_secret=os.environ["CHANNEL_SECRET"],
            channel_access_token=os.environ["CHANNEL_ACCESS_TOKEN"],
            develop_user_id=os.environ.get("DEVELOP") or None,
            port=int(os.environ.get("PORT", DEFAULT_PORT)),
            ws_relay=os.environ.get("EEW_WS_RELAY", DEFAULT_WS_RELAY),
            regions=regions,
            data_file=Path(os.environ.get("EEW_DATA_FILE", "data/eew_listv3.txt")),
        )

    def ws_url(self, region: str) -> str:
        source = WS_SOURCES[region]
        if self.ws_relay:
            return f"{self.ws_relay}?source={source}"
        return source
