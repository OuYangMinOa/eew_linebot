# EEW LINE Bot

LINE 地震速報 bot：監聽 [wolfx](https://wolfx.jp) 的 EEW WebSocket（台灣 / 日本 / 福建 / 四川），
依訂閱者所在縣市與震度門檻過濾後推播警報。

## Setup

需要 [uv](https://docs.astral.sh/uv/)。

1. 安裝相依套件

    ```shell
    uv sync
    ```

2. 設定憑證

    複製 `.env.example` 為 `.env`，填入 LINE channel 憑證（`CHANNEL_SECRET`、`CHANNEL_ACCESS_TOKEN`）。
    有設定 `NGROK_AUTHTOKEN` 才會自動開 ngrok tunnel。

3. 執行

    ```shell
    uv run eew-linebot
    ```

## 使用方式（LINE 對話）

- `地震 台灣` — 開啟按鈕選單：先選 全國/北部/中部/南部/東部/離島，再選縣市
- `地震 台灣 台北` — 訂閱台灣警報，所在地台北（縣市內近震必推，遠震依規模/震度過濾）
- `地震 台灣 all` — 訂閱台灣全國警報
- `地震 日本` / `地震 福建` / `地震 四川` — 訂閱其他地區
- `地震 查詢` — 查看目前訂閱
- `地震 取消 日本` — 取消訂閱
- `help` / `幫助` — 顯示說明

回覆訊息都附 Quick Reply 按鈕，點按鈕即可訂閱／查詢／取消，不用手打指令。

## 開發

```shell
uv run pytest
```

訂閱資料存在 `data/eew_listv3.txt`（每行 `id_縣市_國家...`，與舊版格式相容）。
