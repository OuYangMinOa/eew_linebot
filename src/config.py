import os

from .file_os              import readfile
from flask                import Flask
from linebot.v3           import WebhookHandler
from linebot.v3.messaging import Configuration


PORT = 9002
DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)

EEW_LIST_FILE = f"{DATA_FOLDER}/eew_listv2.txt"
TAIWAN_CITY_FILE = f"{DATA_FOLDER}/taiwan_city.txt"

POS_LIST = readfile(TAIWAN_CITY_FILE)
EEW_LIST = readfile(EEW_LIST_FILE)

LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'

app = Flask(__name__)
configuration  = Configuration(access_token=os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

headers = {'Authorization':f'Bearer {os.environ["CHANNEL_ACCESS_TOKEN"]}','Content-Type':'application/json'}

locations = {
    "新北市": {"經度": 121.6739, "緯度": 24.91571},
    "高雄市": {"經度": 120.666, "緯度": 23.01087},
    "臺中市": {"經度": 120.9417, "緯度": 24.23321},
    "臺北市": {"經度": 121.5598, "緯度": 25.09108},
    "桃園縣": {"經度": 121.2168, "緯度": 24.93759},
    "臺南市": {"經度": 120.2513, "緯度": 23.1417},
    "彰化縣": {"經度": 120.4818, "緯度": 23.99297},
    "屏東縣": {"經度": 120.62, "緯度": 22.54951},
    "雲林縣": {"經度": 120.3897, "緯度": 23.75585},
    "苗栗縣": {"經度": 120.9417, "緯度": 24.48927},
    "嘉義縣": {"經度": 120.574, "緯度": 23.45889},
    "新竹縣": {"經度": 121.1252, "緯度": 24.70328},
    "南投縣": {"經度": 120.9876, "緯度": 23.83876},
    "宜蘭縣": {"經度": 121.7195, "緯度": 24.69295},
    "新竹市": {"經度": 120.9647, "緯度": 24.80395},
    "基隆市": {"經度": 121.7081, "緯度": 25.10898},
    "花蓮縣": {"經度": 121.3542, "緯度": 23.7569},
    "嘉義市": {"經度": 120.4473, "緯度": 23.47545},
    "臺東縣": {"經度": 120.9876, "緯度": 22.98461},
    "金門縣": {"經度": 118.3186, "緯度": 24.43679},
    "澎湖縣": {"經度": 119.6151, "緯度": 23.56548},
    "連江縣": {"經度": 119.5397, "緯度": 26.19737}
}