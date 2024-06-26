import os

from .file_os             import readfile
from flask                import Flask
from linebot.v3           import WebhookHandler
from linebot.v3.messaging import Configuration
from .user                import SubsribeController


PORT = 9031
DATA_FOLDER = SubsribeController.DATA_FOLDER

os.makedirs(DATA_FOLDER, exist_ok=True)

EEW_LIST_FILE = f"{DATA_FOLDER}/eew_listv3.txt"

# eew_list = SubsribeController.from_file(EEW_LIST_FILE)  # readfile(EEW_LIST_FILE)
eew_dict = SubsribeController.from_file(EEW_LIST_FILE) 
print(eew_dict)




LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'

print(os.environ['CHANNEL_SECRET'])
print(os.environ["CHANNEL_ACCESS_TOKEN"])
app = Flask(__name__)
configuration  = Configuration(access_token=os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

headers = {'Authorization':f'Bearer {os.environ["CHANNEL_ACCESS_TOKEN"]}','Content-Type':'application/json'}
