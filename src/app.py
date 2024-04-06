from .config  import app, configuration, handler, EEW_LIST, EEW_LIST_FILE
from .file_os import addtxt
from flask import request, abort

from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

import dotenv


dotenv.load_dotenv()

def get_source(event):
    if event.source.type == 'user':  # 使用者
        return event.source.user_id, event.source.user_id
    elif event.source.type == 'group': # 聊天室
        return event.source.group_id, event.source.user_id
    elif event.source.type == 'room': # 群組
        return event.source.room_id, event.source.user_id

@app.route("/", methods=['GET'])
def home():
    return 'OK'

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event:MessageEvent):
    msg = event.message.text.strip().lower()
    source_id, user_id= get_source(event)
    print(f"[*] {source_id} {user_id} : {msg}")

    if (msg == "地震"):
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            if(source_id not in EEW_LIST):
                EEW_LIST.append(source_id)
                addtxt(EEW_LIST_FILE,source_id)
                line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="好的 當有地震我會提醒你的")]
                )
                )
            else:
                line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="好的 當有地震我會提醒你的")]
                )
                )

            
            
