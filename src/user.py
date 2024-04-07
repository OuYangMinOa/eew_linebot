from abc      import ABC, abstractmethod
from .file_os import POS_LIST, locations
from .eew     import distance_to_taipei

class IdPos():
    @classmethod
    def correct_pos(self, pos):
        if pos.startswith('台'):
            pos = '臺' + pos[1:]
        for each in POS_LIST:
            if pos in each:
                return each
            
    @classmethod
    def from_str(self,line_text):
        line_split = line_text.split("_")
        return {'id': line_split[0], 'pos': line_split[1]}
    
    @classmethod
    def from_command(self, id, cmd):
        return {'id': id, 'pos': self.correct_pos(cmd)}


class Subsriber:

    def __init__(self) -> None:
        self.id  = None
        self.pos = None

    def from_str(self, text, method = IdPos): 
        req = method.from_str(text)
        self.id  = req['id' ]
        self.pos = req['pos']
        self._set_lat_lon()

    def from_command(self, command, method = IdPos):
        req = method.from_command(command)
        self.id  = req['id' ]
        self.pos = req['pos']
        self._set_lat_lon()

    def calcultae_distance(self, lat, lon):
        return distance_to_taipei(lat,lon,self.lat,self.lon)

    #  {"經度": 121.6739, "緯度": 24.91571}
    def _set_lat_lon(self):
        self.lat = locations[self.pos]["經度"]
        self.lon = locations[self.pos]["緯度"]

    def __str__(self) -> str:
        return f"{self.id}_{self.pos}"
    
    def __repr__(self) -> str:
        return f"{self.id}_{self.pos}"