import os

from .file_os              import readfile
from flask                import Flask
from linebot.v3           import WebhookHandler
from linebot.v3.messaging import Configuration


PORT = 9001
DATA_FOLDER = "data"

os.makedirs(DATA_FOLDER, exist_ok=True)

EEW_LIST_FILE = f"{DATA_FOLDER}/eew_list.txt"
EEW_LIST = readfile(EEW_LIST_FILE)



app = Flask(__name__)
configuration  = Configuration(access_token=os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

headers = {'Authorization':f'Bearer {os.environ["CHANNEL_ACCESS_TOKEN"]}','Content-Type':'application/json'}
