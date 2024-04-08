from .config  import app, configuration, handler, eew_list, EEW_LIST_FILE
from .file_os import addtxt
from .user    import Subsriber, SubsribeController
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
    line_bot_api = MessagingApi(ApiClient(configuration))
    if (msg[:2] == "地震"):

        command = msg[2:]
        if (command==""):
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請輸入所在地 (輸入`全國`以接收全國的地震警報)")]
                )
            )
            return
        
        this_sub = Subsriber().from_command(user_id, command)

        check_result = SubsribeController.check_contains(this_sub,eew_list)
        if (check_result[1]):
            eew_list[check_result[0]].from_command(user_id, command)
            SubsribeController.to_file(EEW_LIST_FILE, eew_list)
        else:
            addtxt(EEW_LIST_FILE, str(this_sub))
            eew_list.append( this_sub)


        if (this_sub.pos=="all"):
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
                    messages=[TextMessage(text=f"好的 當{this_sub.pos}有可能感受到地震時，我會提醒您。\n(此預警並非百分百精準。)")]
                )
            )
