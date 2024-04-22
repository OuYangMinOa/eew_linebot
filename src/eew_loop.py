import os
import json
import time
import uuid
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
        self._last_fj_time = None # 防止 福建 一直傳送
        self._last_tw_time = None
        self._last_fj_mag  = None 
        self.EEW  = EEW()
        # self.EEW.build_proxy()

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
        # await asyncio.sleep(5)
        await self.send_maker(EEW_data(1,datetime.now(),datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),pos,121.59,23.92,5.6,40,4),pos)
        if (pos == "fj"):
            async for each in self.EEW.wss_alert(pos):
                this_time =  self.fj_time(each.OriginTime)
                if (( self._last_tw_time is None or (this_time - self._last_tw_time).total_seconds() > 120 )): # 看台灣中央氣象局已發布此地震
                    if  ( self._last_fj_time is None or(
                        ( (this_time - self._last_fj_time).total_seconds() > 120 or each.Magnitude > self._last_fj_mag+0.2 ))):
                        await self.send(each)
                self._last_fj_time = this_time
                self._last_fj_mag  = each.Magnitude
                print(each)
        else:
            async for each in self.EEW.wss_alert(pos):
                await self.send(each)
                self._last_tw_time = self.fj_time(each.OriginTime)
                print(each)

    async def send(self, _EEW:EEW_data, pos):   #  eew_list : list[Subsriber]
        this_message = _EEW.to_text()
        tasks = []
        for each_id in eew_dict:
            each_subscribe = eew_dict[each_id]
            if (pos not in each_subscribe.country):
                continue
            if (each_subscribe.threshold(_EEW)):
                body = build_body(each_subscribe.id, this_message)
                # await self.send_single(body)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)


    async def send_single(self,body):
        # headers['X-Line-Retry-Key']=  f'{uuid.uuid4()}'   
        # print(headers)
        async with aiohttp.ClientSession() as session:
            async with session.post(LINE_PUSH_URL, headers=headers, data=json.dumps(body).encode('utf-8')) as response:
                print(response.status)
                return response.status

    async def send_maker(self, _EEW, pos="tw"):
        maker_sub : Subsriber = SubsribeController.handle_commamd(os.environ['DEVELOP'],"台灣 台北")
        maker_sub = maker_sub.from_command(os.environ['DEVELOP'],"jp")
        maker_sub = maker_sub.from_command(os.environ['DEVELOP'],"sc")
        maker_sub = maker_sub.from_command(os.environ['DEVELOP'],"fj")
        print(maker_sub)

        tasks = []
        for each_subscribe in [maker_sub,]:
            if (pos not in each_subscribe.country):
                continue
            this_message = _EEW.to_text()  # For testing reasons (grab the time), I put it in the loop.
            if (each_subscribe.threshold(_EEW)):
                print(pos, each_subscribe.country)
                body = build_body(each_subscribe.id, this_message)
                tasks.append(asyncio.create_task( self.send_single(body)))
        await asyncio.gather(*tasks)