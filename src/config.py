import os

from .file_os             import readfile
from flask                import Flask
from linebot.v3           import WebhookHandler
from linebot.v3.messaging import Configuration
from .user                import SubsribeController


PORT = 9012
DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)

EEW_LIST_FILE = f"{DATA_FOLDER}/eew_listv2.txt"

eew_list = SubsribeBuilder.from_file(EEW_LIST_FILE)  # readfile(EEW_LIST_FILE)
print(eew_list)
LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'

app = Flask(__name__)
configuration  = Configuration(access_token=os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

headers = {'Authorization':f'Bearer {os.environ["CHANNEL_ACCESS_TOKEN"]}','Content-Type':'application/json'}
