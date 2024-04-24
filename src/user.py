from abc      import ABC, abstractmethod
from .eew     import distance_to_taipei, EEW_data
from .file_os import readfile
from glob     import glob

import os

#MARK: IdPos
class IdPos(): 
    """Stradegy for tw
    """
    POS_LIST = ['基隆市','臺北市','新北市','桃園市','新竹市','臺中市','臺南市','高雄市','宜蘭縣','新竹縣','苗栗縣','彰化縣','南投縣','雲林縣','嘉義縣','屏東縣','臺東縣','花蓮縣','澎湖縣','基隆縣','金門縣','連江縣',]
    @classmethod
    def correct_pos(self, pos):
        if (pos is None):
            return None

        pos = pos.strip()
        if (pos.lower() == "all" or pos=="全國" or pos == ""):
            return "all"
        if '台' in pos:
            pos = pos.replace('台','臺')
        
        for each in self.POS_LIST:
            if ((pos in each) or (each in pos)):   
                return each
        
        return None
            
    @classmethod
    def from_str(self,line_text):
        line_split = line_text.strip().split("_")
        return {'id': line_split[0], 'pos': line_split[1], 'country':line_split[2:]}
    
    @classmethod
    def from_command(self, id, cmd):
        return {'id': id, 'pos': self.correct_pos(cmd)}




#MARK: Subsriber
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
        "花蓮縣": {"經度": 121.3542, "緯度": 23.7569 },
        "嘉義市": {"經度": 120.4473, "緯度": 23.47545},
        "臺東縣": {"經度": 120.9876, "緯度": 22.98461},
        "金門縣": {"經度": 118.3186, "緯度": 24.43679},
        "澎湖縣": {"經度": 119.6151, "緯度": 23.56548},
        "連江縣": {"經度": 119.5397, "緯度": 26.19737},
    }

    def __init__(self) -> None:
        
        self.country_word_dict = {
            "tw":"台灣",
            "jp":"日本",
            "sc":"四川",
            "fj":"福建",
        }

        self.id  = None
        self.pos = None
        self.country = []
        self.last_cmd  = None
        self.notify = None
    
    def __str__(self) -> str:
        return f"{self.id}_{self.pos}_{'_'.join(self.country)}"
    
    def __repr__(self) -> str:
        return f"{self.id}_{self.pos}_{'_'.join(self.country)}"
    
    def get_notify(self) -> str:
        return self.notify # 

    def get_country_str(self):
        output = ""
        for c in self.country:
            output = output + self.country_word_dict[c] 
            if (c == "tw" and self.pos is not None):
                output = output + "-" + self.pos
            output = output + ", "
        return output

    def from_str(self, text, method = IdPos): 
        req = method.from_str(text)
        print(req)
        self.id       = req['id' ]
        self.pos      = req['pos']
        self.country  = req['country' ]
        
        if (self.pos == "None"):
            self.pos = None

        if (self.pos != "all" and self.pos is not None):
            self._set_lat_lon()
        return self
        
    def from_command(self,id, country, pos = None, method = IdPos):
        self.id  = id
        temp_pos = method.correct_pos(pos)
        # print(temp_pos)
        self.last_cmd = [id, country, pos]
        if (country not in self.country): # Add country to self.country
            self.country.append(country)
            this_country_str = self.get_country_str()
            self.pos = temp_pos
            self.notify = f"好的 ! \n[{this_country_str}]\n發生地震時，我會提醒您。\n(此預警並非百分百精準。)"
        elif (country in self.country):
            if (country != "tw"): # remove country from self.country
                self.country.remove(country)
                self.notify = f"將不再監測 {self.country_word_dict[country]}"
            elif (country == "tw" and temp_pos == self.pos):  # if country is "tw" and command's pos is same as self.pos, remove country from self.country
                self.country.remove(country)
                self.notify = f"將不再監測 {self.country_word_dict[country]} -> {temp_pos}"
            else:  # country is "tw" and pos id note diff self.pos
                self.notify = f"好的將改變你在台灣的所在地。\n{self.pos} -> {temp_pos}"
                self.pos = temp_pos

        return self

    def calcultae_distance(self, lat, lon):
        self._set_lat_lon()
        return distance_to_taipei(lat,lon,self.lat,self.lon)

    def threshold(self, _eew : EEW_data,pos="tw"):
        # if (self.pos is None):
        #     return True
        
        if (pos == "jp"):
            return True
        
        if (pos == "sc"):
            return True
        
        if (pos == "fj" ):
            if (_eew.Magnitude>5):
                return True
            else:
                return False

        # if (_eew.MaxIntensity is None or _eew.Magnitude is None or _eew.Depth is None):
        #     return True

        if (self.pos == "all" or self.pos is None):
            return True
        this_dis = self.calcultae_distance(_eew.Latitude, _eew.Longitude)
        this_inten = int(_eew.MaxIntensity[0])
        print(self.pos, this_dis, _eew.Magnitude, _eew.MaxIntensity)
        if (self.pos == "all"):
            return True
        
        if (this_dis<60  ): 
            return True
        if (this_dis<180): 
            return (_eew.Magnitude >= 5) or (this_inten >= 4)
        else : 
            return (_eew.Magnitude >= 6) or (this_inten >= 5)

    #  {"經度": 121.6739, "緯度": 24.91571}
    def _set_lat_lon(self):
        self.lon = self.locations[self.pos]["經度"]
        self.lat = self.locations[self.pos]["緯度"]

    

    def check_contains(self,_list)->tuple[int, bool]:
        for num,each in enumerate(_list):
            if (self.id == each.id):
                return num ,True
            
        return -1,False
            

#MARK: SubsribeController
class SubsribeController:

    DATA_FOLDER = "data"

    @classmethod
    def from_file(self,filename:str)->dict:
        """return a dict< id<str>, <Subsriber> >

        Args:
            filename (str): File that store the Subsriber data

        Returns:
            dict: dict< id<str>, <Subsriber> >
        """
        if os.path.exists(filename):
            subs = {}
            with open(filename, "r",encoding="utf-8") as f:
                for line in f:
                    if (line!=""):
                        
                        this_sub = Subsriber().from_str(line)
                        subs[this_sub.id] = this_sub
            return subs
        else:
            with open(filename, "w",encoding="utf-8") as f:
                pass
            return {}
        
    @classmethod
    def to_file(self, filename :str, subs:dict)->None:
        with open(filename, "w", encoding="utf-8") as f:
            for each_id in subs:
                f.write(f"{subs[each_id]}\n")
        

    @classmethod
    def check_contains(self, _sub_tar:Subsriber,_sub_list:Subsriber)->tuple[int, bool]:
        for num,each in enumerate(_sub_list):
            if (_sub_tar.id == each.id):
                return num ,True
        return -1,False
    

    @classmethod
    def handle_commamd(self, id:str, command:str, method=IdPos) -> Subsriber:
        command = command.strip()
        if (command.startswith("臺灣") or command.startswith("台灣")):
            return Subsriber().from_command(id,'tw',command[2:],method=method)
        
        if (command.startswith("日本")):
            return Subsriber().from_command(id,"jp")
        
        if (command.startswith("四川")):
            return Subsriber().from_command(id,"sc")
        
        if (command.startswith("福建")):
            return Subsriber().from_command(id,"fj")

        ## handle command like "地震 {台灣縣市}" ,ex: "地震 台北"         
        result = method.from_command(id,command)
        if (result['pos'] is not None ):
            return Subsriber().from_command(id,'tw',result['pos'],method=method)
        else:
            return None

