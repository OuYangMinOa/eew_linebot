from .proxies import Proxies
from dataclasses import dataclass
from requests_html import AsyncHTMLSession
import threading
import asyncio
import random
import time
import json

@dataclass
class EEW_data:
    id: int
    ReportTime: str
    OriginTime: str
    HypoCenter: str
    Latitude: float 
    Longitude: float
    Magnitude: float
    Depth: int
    MaxIntensity: str



class EEW:
    WHITE_CIRCLE  = "⚪"
    GREEN_CIRCLE  = "🟢"
    BLUE_CIRCLE   = "🔵"
    RED_CIRCLE    = "🔴"
    YELLOW_CIRCLE = "🟡"

    URL = "https://api.wolfx.jp/cwa_eew.json"  ## The taiwan earthquake url endpoint.
    def __init__(self) -> None:
        self.session = AsyncHTMLSession()
        self.state    = True
        self.last_eew = None
        self.use_proxy = True

    def build_proxy(self):
        if (self.use_proxy):
            self.builder  = Proxies(url = self.URL)\
                                .set_p(6)\
                                .set_num(10)\
                                .add_ssl_proxies()
            
            self.proxies  = self.builder\
                                .build()\
                                .get_proxies()
            print(f"[*] proxies num : {len(self.proxies)}")
            
    @classmethod
    def circle_depth(self,Depth):
        if Depth > 300:
            return self.WHITE_CIRCLE
        elif Depth > 70:
            return self.GREEN_CIRCLE
        elif Depth > 30:
            return self.BLUE_CIRCLE
        else:
            return self.RED_CIRCLE
    @classmethod
    def circle_mag(self,mag):
        if mag < 4 :
            return self.WHITE_CIRCLE
        elif mag < 5:
            return self.GREEN_CIRCLE
        elif mag <= 6:
            return self.BLUE_CIRCLE
        else:
            return self.RED_CIRCLE
    @classmethod
    def circle_intensity(self,intensity):
        intensity = int(intensity)
        if intensity == 1:
            return self.WHITE_CIRCLE
        if intensity == 2:
            return self.GREEN_CIRCLE
        if intensity == 3:
            return self.BLUE_CIRCLE
        if intensity == 4:
            return self.YELLOW_CIRCLE
        return self.RED_CIRCLE
    
    def json_to_eewdata(self,json_data) -> EEW_data:
        return EEW_data(
            json_data['ID'],
            json_data['ReportTime'].replace(" ","\n"),
            json_data['OriginTime'].replace(" ","\n"),
            json_data['HypoCenter'],
            json_data['Latitude'],
            json_data['Longitude'],
            json_data['Magunitude'],
            json_data['Depth'],
            json_data['MaxIntensity'],
        )

    async def grab_result(self) -> EEW_data:
        try:
            r = await self.session.get(self.URL)
            await r.html.arender()
        except Exception as e:
            print(e)
            print("[*] use proxy")
            this_proxy = random.choice(self.proxies)
            try:
                r = await self.session.get(self.URL,proxies={'http':this_proxy,'https':this_proxy})
                await r.html.arender()
            except Exception as e:
                print(e)
                print(f"{this_proxy} proxy error")
                self.proxies.remove(this_proxy)
                if (len(self.proxies) == 0):
                    self.proxies = self.builder.build().get_proxies()
                    print(f"[*] New proxies num : {len(self.proxies)}")
                    r = await self.session.get(self.URL,proxies={'http':this_proxy,'https':this_proxy})
                    await r.html.arender()

        r.json()
        alert_json = r.json()
        return self.json_to_eewdata(alert_json)
    

    async def alert(self):
        if self.last_eew is None:
            self.last_eew = await self.grab_result()
        while (self.state):
            time.sleep(5)
            this_eew = await self.grab_result()
            if (this_eew.id != self.last_eew.id):
                yield this_eew
                self.last_eew = this_eew

    async def close(self):
        self.state = False
        await self.session.close()


async def test():
    eew = EEW()
    print(await eew.grab_result())
    print("Listen to alert system")
    async for each in eew.alert():
        print(each)
    await eew.close()

if __name__ == '__main__':
    asyncio.run(test())