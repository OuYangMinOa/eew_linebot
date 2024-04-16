from .config  import app, configuration, handler, eew_dict, EEW_LIST_FILE
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

    if (msg == "help" or msg == "幫助" or msg == "小俠" or msg == "歐陽小俠" ):
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=
                    ("目前只支援地震通知功能\n"
                    "若想要其他的功能請聯絡歐陽\n"
                    "請輸入國家跟所在地\n"
                    "(地震 國家 台灣縣市)。 \n"
                    "ex:\n\t1. 地震 台灣 台北\n\t2. 地震 日本\n"
                    "目前國家支援 (日本 台灣 四川 福建)\n所在地支援台灣所有縣市")
                )]
            )
        )

    if (msg[:2] == "地震"):
        command = msg[2:]
        # No country
        if (command==""):
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=("請輸入國家跟所在地\n"
                                                "(地震 國家 台灣縣市)。 \n"
                                                "ex:\n\t1. 地震 台灣 台北\n\t2. 地震 日本\n"
                                                "目前國家支援 (日本 台灣 四川 福建)\n"
                                                "所在地支援台灣所有縣市\n"
                                                "(若要監控全國 請輸入`all`)"
                                                ))]
                )
            )
            return
        
        this_sub = SubsribeController.handle_commamd(user_id, command)

        if (this_sub is None):
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=("請輸入國家跟所在地\n"
                                                "(地震 國家 台灣縣市)。 \n"
                                                "ex:\n\t1. 地震 台灣 台北\n\t2. 地震 日本\n"
                                                "目前國家支援 (日本 台灣 四川 福建)\n"
                                                "所在地支援台灣所有縣市\n"
                                                "(若要監控全國 請輸入`all`)"
                                                ))]
                )
            )
            return


        if (user_id in eew_dict):
            if (this_sub.last_cmd is not None):
                eew_dict[user_id].from_command(*this_sub.last_cmd)
            SubsribeController.to_file(EEW_LIST_FILE, eew_dict)
        else:
            eew_dict[user_id] = this_sub
            addtxt(EEW_LIST_FILE, str(this_sub))


        # check_result = SubsribeController.check_contains(this_sub,eew_list)
        # if (check_result[1]):
        #     this_index = check_result[0]
        #     eew_list[this_index] = this_sub
        #     SubsribeController.to_file(EEW_LIST_FILE, eew_list)
        # else:
        #     addtxt(EEW_LIST_FILE, str(this_sub))
        #     eew_list.append( this_sub)


        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"{eew_dict[user_id].get_notify()}")]
            )
        )
