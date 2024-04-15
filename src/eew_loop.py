import os
import json
import time
import aiohttp
import asyncio
import threading

from requests_html import AsyncHTMLSession
from .eew     import EEW, EEW_data
from .config  import configuration, headers, LINE_PUSH_URL, eew_dict
from datetime import datetime
from .user    import Subsriber, SubsribeController

def build_body(to, msg):
    return {'to':to,'messages':[{'type': 'text','text': msg }]}

class EEWLoop:
    def __init__(self,loop) -> None:
        self.loop = loop
        self.EEW  = EEW()

    def start_alert_tw(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("tw"),)).start()
        return self

    def start_alert_jp(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("jp"),)).start()
        return self
    
    def start_alert_fj(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("fj"),)).start()  
        return self
    
    def start_alert_sc(self):
        threading.Thread(target=self.loop.create_task, args=(self.loop_alert("sc"),)).start()
        return self

    async def loop_alert(self,pos="tw"):
        print(f"[*] Start alert {pos} !")
        await self.send_maker(EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),pos,121.59,23.92,5.6,40,4),pos)
        async for each in self.EEW.wss_alert(pos):
            await self.send(each, pos)
            print(pos,each)

    async def send(self, _EEW:EEW_data, pos):   #  eew_list : list[Subsriber]
        this_message = _EEW.to_text()
        tasks = []
        for each_id in eew_dict:
            each_subscribe = eew_dict[each_id]
            if (pos not in each_subscribe.country):
                continue
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)


    async def send_single(self,body):
        async with aiohttp.ClientSession() as session:
            async with session.post(LINE_PUSH_URL, headers=headers, data=json.dumps(body).encode('utf-8')) as response:
                pass

    async def send_maker(self, _EEW, pos="tw"):
        maker_sub : Subsriber = SubsribeController.handle_commamd(os.environ['DEVELOP'],"台灣 台北")
        maker_sub = maker_sub.from_command(os.environ['DEVELOP'],"jp")

        tasks = []
        for each_subscribe in [maker_sub,]:
            if (pos not in each_subscribe.country):
                continue
            this_message = _EEW.to_text()  # For testing reasons (grab the time), I put it in the loop.
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)