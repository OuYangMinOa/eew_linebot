from ..proxies import Proxies
from dataclasses import dataclass
from requests_html import AsyncHTMLSession
from datetime import datetime
from typing   import AsyncIterator
from opencc   import OpenCC


import websockets
import threading
import asyncio
import random
import time
import json
import math


# lat 經度
# log 緯度 
def distance_to_taipei(lat, lon, tar_lat = 121.554219963632562, tar_lon=25.04201771824424 ):
    taipei_lat = tar_lat  # 125
    taipei_lon = tar_lon  # 121

    dlat = (lat - taipei_lat) * math.pi / 180
    dlon = (lon - taipei_lon) * math.pi / 180

    taipei_lat1 = taipei_lat * math.pi / 180
    lat2        =        lat * math.pi / 180

    a = math.pow(math.sin(dlat / 2), 2) + math.pow(math.sin(dlon / 2), 2) * math.cos(taipei_lat1) * math.cos(lat2)

    rad = 6371
    c   = 2 * math.asin(math.sqrt(a))

    return rad * c


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
    MaxIntensity: int

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def send_threshold(self):
        if (self.get_dis()<60 ): return True
        if (self.get_dis()<180): return self.Magnitude >= 5 or self.MaxIntensity >= 4
        else : return self.Magnitude >= 6 or self.MaxIntensity >= 5
        raise ValueError(f"Invalid threshold")

    def get_dis(self):
        return distance_to_taipei(self.Latitude, self.Longitude)

    def to_text(self):
        return (f"{self.HypoCenter} 發生規模{self.Magnitude}有感地震, 最大震度{self.MaxIntensity}級\n"
                "發生時間  : " + f" {self.OriginTime}\n"
                "地震規模  : " + f" {EEW.circle_mag(self.Magnitude)} 芮氏 {self.Magnitude}\n"
                "地震深度  : " + f" {EEW.circle_depth(self.Depth)} {self.Depth}公里\n"
                "最大震度  : " + f" {EEW.circle_intensity(self.MaxIntensity)} {self.MaxIntensity}級\n"
                "震央位置  : " + f" {self.HypoCenter}\n\n"
                f"💭 發布於：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}" 
        )


class EEW:
    WHITE_CIRCLE  = "⚪"
    GREEN_CIRCLE  = "🟢"
    BLUE_CIRCLE   = "🔵"
    RED_CIRCLE    = "🔴"
    YELLOW_CIRCLE = "🟡"

    URL     = "https://api.wolfx.jp/c.json"  ## The taiwan earthquake url endpoint.
    URL_SSW = "wss://ws-api.wolfx.jp/cwa_eew"
    def __init__(self) -> None:
        self.state    = True
        self.last_eew = None
        self.use_proxy = True
        self.proxies = []
        self.session = None 
        self.pos_url_wss_dict = {
            "tw": "wss://ws-api.wolfx.jp/cwa_eew",
            "jp": "wss://ws-api.wolfx.jp/jma_eew",
            "fj": "wss://ws-api.wolfx.jp/fj_eew", # 福建
            "sc": "wss://ws-api.wolfx.jp/sc_eew", # 四川
        }


    def get_random_proxy(self) -> str:
        return random.choice(self.proxies)

    def build_proxy(self) -> None:
        if (self.use_proxy):
            self.builder  = Proxies(url = "https://api.line.me:443")\
                                .set_p(6)\
                                .set_num(10)\
                                .add_ssl_proxies()
            
            self.proxies  = self.builder\
                                .build()\
                                .get_proxies()
            print(f"[*] proxies num : {len(self.proxies)}")
            
    @classmethod
    def circle_depth(cls,Depth) -> str:
        if Depth is None:
            return cls.WHITE_CIRCLE
        if Depth > 300:
            return cls.WHITE_CIRCLE
        elif Depth > 70:
            return cls.GREEN_CIRCLE
        elif Depth > 30:
            return cls.BLUE_CIRCLE
        else:
            return cls.RED_CIRCLE
    @classmethod
    def circle_mag(cls,mag) -> str:
        if (mag is None):
            return cls.WHITE_CIRCLE
        if mag < 4 :
            return cls.WHITE_CIRCLE
        elif mag < 5:
            return cls.YELLOW_CIRCLE
        else:
            return cls.RED_CIRCLE
    @classmethod
    def circle_intensity(cls,intensity_str) -> str:
        if (intensity_str is None ):
            return cls.WHITE_CIRCLE
        
        if (isinstance(intensity_str,str)):
            if (intensity_str[0].isnumeric()):
                intensity = int(intensity_str[0])
            else:
                return cls.WHITE_CIRCLE
        elif(isinstance(intensity_str,float) or isinstance(intensity_str,int)):
            intensity = math.floor(intensity_str)
        else:
            return cls.WHITE_CIRCLE
        if intensity == 1:
            return cls.WHITE_CIRCLE
        if intensity == 2:
            return cls.BLUE_CIRCLE
        if intensity == 3:
            return cls.GREEN_CIRCLE
        if intensity == 4:
            return cls.YELLOW_CIRCLE
        return cls.RED_CIRCLE
    
    def json_to_eewdata(self,json_data,pos) -> EEW_data:
        cc = OpenCC('s2tw')
        if (pos == "jp"):        
            return EEW_data(
                json_data['EventID'],
                json_data['AnnouncedTime'].replace(" ","\n"),
                json_data['OriginTime'].replace(" ","\n"),
                json_data['Hypocenter'],
                json_data['Latitude'],
                json_data['Longitude'],
                json_data['Magunitude'],
                json_data['Depth'],
                json_data['MaxIntensity'],
            )
        elif (pos == "fj"):
            return EEW_data(
                json_data['EventID'],
                json_data['ReportTime'].replace(" ","\n"),
                json_data['OriginTime'].replace(" ","\n"),
                cc.convert(json_data['HypoCenter']),
                json_data['Latitude'],
                json_data['Longitude'],
                json_data['Magunitude'],
                None,
                None,
            )
        else:
            return EEW_data(
                json_data['ID'],
                json_data['ReportTime'].replace(" ","\n"),
                json_data['OriginTime'].replace(" ","\n"),
                cc.convert(json_data['HypoCenter']),
                json_data['Latitude'],
                json_data['Longitude'],
                json_data['Magunitude'],
                json_data['Depth'],
                json_data['MaxIntensity'],
            )
    
    def _get_url_by_pos(self,pos="tw"):
        if (pos in self.pos_url_wss_dict):
            return self.pos_url_wss_dict[pos]
        return self.pos_url_wss_dict["tw"]
    
    async def wss_grab_result(self,pos="tw")-> AsyncIterator[EEW_data]:
        while True:
            try:
                async with websockets.connect(self._get_url_by_pos(pos),timeout=600) as websocket:
                    print(f"{pos} Connected !")
                    while True:
                        recv = await websocket.recv() 
                        r    = json.loads(recv)
                        if (r["type"]!="heartbeat"):
                            yield self.json_to_eewdata(r,pos)
            except Exception as e:
                print(f"{pos} Connection closed : {e}")
                await asyncio.sleep(0.5)
                print(f"{pos} Reconnect")
            

    async def wss_alert(self,pos="tw") -> AsyncIterator[EEW_data]:
        async for each in self.wss_grab_result(pos):
            print(pos,each)
            yield each


    async def grab_result(self) -> EEW_data:
        try:
            r = await self.session.get(self.URL)
            await r.html.arender()
        except Exception as e:
            print(e)
            print("[*] use proxy")
            proxy_status = False
            for this_proxy in self.proxies:
                try:
                    r = await self.session.get(self.URL,proxies={'http':this_proxy,'https':this_proxy})
                    await r.html.arender()
                    proxy_status = True
                except Exception as e:
                    print(e)
                    print(f"{this_proxy} proxy error")
                    self.proxies.remove(this_proxy)

            ## However all proxy fails, SLEEP(10) and return the last_eew[EEW_DATA]
            if (not proxy_status):
                self.proxies = self.builder.build().get_proxies()
                print(f"[*] New proxies num : {len(self.proxies)}")
                time.sleep(10)
                return self.last_eew

        r.json()
        alert_json = r.json()
        return self.json_to_eewdata(alert_json)
    

    async def alert(self) -> AsyncIterator[EEW_data]:
        self.session = AsyncHTMLSession()
        if self.last_eew is None:
            self.last_eew = await self.grab_result() 

        while (self.state):
            time.sleep(5)
            this_eew = await self.grab_result()
            if (this_eew.id != self.last_eew.id):
                yield this_eew
                self.last_eew = this_eew

    async def close(self) -> None:
        self.state = False
        if (self.session is not None):
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
