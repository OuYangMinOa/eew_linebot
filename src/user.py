from abc      import ABC, abstractmethod
from .eew     import distance_to_taipei, EEW_data
from .file_os import readfile

import os


class IdPos():
    POS_LIST = ['基隆市','臺北市','新北市','桃園市','新竹市','臺中市','臺南市','高雄市','宜蘭縣','新竹縣','苗栗縣','彰化縣','南投縣','雲林縣','嘉義縣','屏東縣','台東縣','花蓮縣','澎湖縣','基隆縣','金門縣','連江縣',]
    @classmethod
    def correct_pos(self, pos):
        pos = pos.strip()
        if (pos.lower() == "all" or pos=="全國"):
            return "all"
        if '台' in pos:
            pos = pos.replace('台','臺')

        for each in self.POS_LIST:
            if pos in each:   
                return each
        return 'all'
            
    @classmethod
    def from_str(self,line_text):
        line_split = line_text.strip().split("_")
        return {'id': line_split[0], 'pos': line_split[1]}
    
    @classmethod
    def from_command(self, id, cmd):
        return {'id': id, 'pos': self.correct_pos(cmd)}


class Subsriber:
    locations = {
        "新北市": {"經度": 121.6739, "緯度": 24.91571},
        "臺北市": {"經度": 121.5598, "緯度": 25.09108},
        "臺中市": {"經度": 120.9417, "緯度": 24.23321},
        "桃園市": {"經度": 121.2168, "緯度": 24.93759},
        "高雄市": {"經度": 120.666 , "緯度": 23.01087},
        "臺南市": {"經度": 120.2513, "緯度": 23.1417 },
        "彰化縣": {"經度": 120.4818, "緯度": 23.99297},
        "屏東縣": {"經度": 120.62  , "緯度": 22.54951},
        "雲林縣": {"經度": 120.3897, "緯度": 23.75585},
        "苗栗縣": {"經度": 120.9417, "緯度": 24.48927},
        "嘉義縣": {"經度": 120.574 , "緯度": 23.45889},
        "新竹縣": {"經度": 121.1252, "緯度": 24.70328},
        "南投縣": {"經度": 120.9876, "緯度": 23.83876},
        "宜蘭縣": {"經度": 121.7195, "緯度": 24.69295},
        "新竹市": {"經度": 120.9647, "緯度": 24.80395},
        "基隆市": {"經度": 121.7081, "緯度": 25.10898},
        "花蓮縣": {"經度": 121.3542, "緯度": 23.7569},
        "嘉義市": {"經度": 120.4473, "緯度": 23.47545},
        "臺東縣": {"經度": 120.9876, "緯度": 22.98461},
        "金門縣": {"經度": 118.3186, "緯度": 24.43679},
        "澎湖縣": {"經度": 119.6151, "緯度": 23.56548},
        "連江縣": {"經度": 119.5397, "緯度": 26.19737},
    }

    def __init__(self) -> None:
        self.id  = None
        self.pos = None

    def from_str(self, text, method = IdPos): 
        req = method.from_str(text)
        self.id  = req['id' ]
        self.pos = req['pos']
        if (self.pos != "all"):
            self._set_lat_lon()
        return self
        
    def from_command(self,id, command, method = IdPos):
        req = method.from_command(id, command)
        self.id  = req['id' ]
        self.pos = req['pos']
        if (self.pos != "all"):
            self._set_lat_lon()
        return self

    def calcultae_distance(self, lat, lon):
        return distance_to_taipei(lat,lon,self.lat,self.lon)

    def threshold(self, _eew : EEW_data):
        if (self.pos == "all"):
            return True
        this_dis = self.calcultae_distance(_eew.Latitude, _eew.Longitude)
        print(self.pos, this_dis, _eew.Magnitude, _eew.MaxIntensity)
        if (self.pos == "all"):
            return True
        
        if (this_dis<60  ): 
            return True
        if (this_dis<180): 
            return (_eew.Magnitude >= 5) or (_eew.MaxIntensity >= 4)
        else : 
            return (_eew.Magnitude >= 6) or (_eew.MaxIntensity >= 5)

    #  {"經度": 121.6739, "緯度": 24.91571}
    def _set_lat_lon(self):
        self.lat = self.locations[self.pos]["經度"]
        self.lon = self.locations[self.pos]["緯度"]

    def __str__(self) -> str:
        return f"{self.id}_{self.pos}"
    
    def __repr__(self) -> str:
        return f"{self.id}_{self.pos}"

    def check_contains(self,_list)->tuple[int, bool]:
        for num,each in enumerate(_list):
            if (self.id == each.id):
                return num ,True
            
        return -1,False
            

class SubsribeController:
    @classmethod
    def from_file(self,filename)->list:
        if os.path.exists(filename):
            subs = []
            with open(filename, "r",encoding="utf-8") as f:
                for line in f:
                    if (line!=""):
                        subs.append(Subsriber().from_str(line))
            return subs
        else:
            with open(filename, "w",encoding="utf-8") as f:
                pass
            return []
        
    @classmethod
    def to_file(self, filename, subs)->None:
        with open(filename, "w", encoding="utf-8") as f:
            for each in subs:
                f.write(f"{each}\n")
        

    @classmethod
    def check_contains(self, _sub_tar,_sub_list)->tuple[int, bool]:
        for num,each in enumerate(_sub_list):
            if (_sub_tar.id == each.id):
                return num ,True
        return -1,False
    
