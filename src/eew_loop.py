import os
import json
import time
import aiohttp
import asyncio
import threading

from .eew     import EEW, EEW_data
from .config  import configuration, eew_list, headers, LINE_PUSH_URL
from datetime import datetime
from .user    import Subsriber

def build_body(to, msg):
    return {'to':to,'messages':[{'type': 'text','text': msg }]}

def start_eew_loop(loop=None):
    eew = EEW()
    # eew.build_proxy()
    time.sleep(5)
    
    async def send_single(body):
        async with aiohttp.ClientSession() as session:
            async with session.post(LINE_PUSH_URL, headers=headers, data=json.dumps(body).encode('utf-8')) as response:
                pass
            
    async def send(_EEW:EEW_data):

        #  eew_list : list[Subsriber]

        this_message = _EEW.to_text()
        tasks = []
        for each_subscribe in eew_list:
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( send_single(body)))
        await asyncio.gather(*tasks)
    
    ## for testing
    async def send_maker(_EEW):
        maker_sub = Subsriber().from_command(os.environ['DEVELOP'],"台北")
        tasks = []
        for each_subscribe in [maker_sub,]*2:
            this_message = _EEW.to_text()  # For testing reasons, I put it in the loop.
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( send_single(body)))
        await asyncio.gather(*tasks)
        # requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))

    async def loop_alert():
        print("[*] Start alert !")
        await send_maker(EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),"test",121.8,24.25,5.2,20,3))

        async for each in eew.ssw_alert():
            await send(each)
            print(each)

    threading.Thread(target=loop.create_task, args=(loop_alert(),)).start()