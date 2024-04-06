import json
import time
import asyncio
import threading
import requests


from .eew     import EEW, EEW_data
from .config  import configuration, EEW_LIST, headers
from datetime import datetime


def start_eew_loop(loop=None):
    eew = EEW()
    eew.build_proxy()
    time.sleep(5)
    
    async def send(_EEW:EEW_data):
        this_message = (f"{_EEW.HypoCenter} 發生規模{_EEW.Magnitude}有感地震, 最大震度{_EEW.MaxIntensity}級\n"
                        "地震規模  : " + f" {EEW.circle_mag(_EEW.Magnitude)} 芮氏 {_EEW.Magnitude}\n"
                        "地震深度  : " + f" {EEW.circle_depth(_EEW.Depth)} {_EEW.Depth}公里\n"
                        "最大震度  : " + f" {EEW.circle_intensity(_EEW.MaxIntensity)} {_EEW.MaxIntensity}級\n"
                        "震央位置  : " + f" {_EEW.HypoCenter}\n\n"
                        f"💭 發布於：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}" 
        )
        print(this_message)

        for each_subscribe in EEW_LIST:
            body = {
                'to':each_subscribe,
                'messages':[{
                        'type': 'text',
                        'text': this_message
                    }]
                }
            req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))
                

    async def loop_alert():
        print("[*] Start alert !")

        ## TESTING 
        # await send(
        #     EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日\n%H:%M:%S"),"test",5.0,1.0,5,100,'5')
        # )

        async for each in eew.alert():
            await send(each)

    threading.Thread(target=loop.create_task, args=(loop_alert(),)).start()