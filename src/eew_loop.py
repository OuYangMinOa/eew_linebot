import os
import json
import time
import aiohttp
import asyncio
import threading

from requests_html import AsyncHTMLSession
from .eew     import EEW, EEW_data
from .config  import configuration, eew_list, headers, LINE_PUSH_URL
from datetime import datetime
from .user    import Subsriber

def build_body(to, msg):
    return {'to':to,'messages':[{'type': 'text','text': msg }]}

class EEW_loop:
    def __init__(self,loop) -> None:
        self.loop = loop
        self.EEW  = EEW()

    def start_alert_tw(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("tw"),)).start()
        return self

    def start_alert_jp(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("jp"),)).start()
        return self

    async def loop_alert(self,pos="tw"):
        print(f"[*] Start alert {pos} !")
        await self.send_maker(EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),"花蓮縣吉安鄉",121.59,23.92,5.6,40,4))
        async for each in self.EEW.wss_alert(pos):
            await self.send(each)
            print(each)

    async def send(self, _EEW:EEW_data):   #  eew_list : list[Subsriber]
        this_message = _EEW.to_text()
        tasks = []
        for each_subscribe in eew_list:
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)


    async def send_single(self,body):
        async with aiohttp.ClientSession() as session:
            async with session.post(LINE_PUSH_URL, headers=headers, data=json.dumps(body).encode('utf-8')) as response:
                pass


    async def send_maker(self, _EEW):
        maker_sub = Subsriber().from_command(os.environ['DEVELOP'],"台北")
        tasks = []
        for each_subscribe in [maker_sub,]*2:
            this_message = _EEW.to_text()  # For testing reasons (grab the time), I put it in the loop.
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)


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
            this_message = _EEW.to_text()  # For testing reasons (grab the time), I put it in the loop.
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( send_single(body)))
        await asyncio.gather(*tasks)
        # requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))

    async def loop_alert():
        print("[*] Start alert !")
        await send_maker(EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),"花蓮縣吉安鄉",
                                121.59,
                                23.92,
                                5.6,
                                40,
                                4
                                ))

        async for each in eew.wss_alert():
            await send(each)
            print(each)


    threading.Thread(target=loop.create_task, args=(loop_alert(),)).start()