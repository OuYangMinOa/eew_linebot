from multiprocessing import Pool
from tqdm.auto       import tqdm
from threading       import Thread


import requests
import json
import time
import bs4
import re



class Proxies:
    def __init__(self,url='https://www.microsoft.com/',p=6,num=10):
        self.unverify_proxy = []
        self.proxy_list     = []
        self.url = url          
        self.p   = p            
        self.num = num          
        self.geo_start_page = 0 
        
        self.run_func = []

    def add_ssl_proxies(self):
        self.run_func.append(self._ssl_proxies)
        return self
    
    def add_geo_proxies(self):
        self.run_func.append(self._geo_proxies)
        return self

    def set_p(self,p):
        self.p = p
        return self

    def set_num(self, num):
        self.num = num
        return self

    def set_url(self, url):
        self.url = url
        return self

    def build(self):
        for func in self.run_func:
            func()
        self._verify_proxy()
        return self
    
    def get_proxies(self):
        return self.proxy_list

    def _ssl_proxies(self):
        response = requests.get("https://www.sslproxies.org/")
        self.unverify_proxy.extend(re.findall('\d+\.\d+\.\d+\.\d+:\d+', response.text))

    def _geo_proxies(self):
        headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
        for self.geonode_page in range(self.geo_start_page + 1,self.geo_start_page + 4):
            url = f'https://proxylist.geonode.com/api/proxy-list?limit=500&page={self.geonode_page}&sort_by=lastChecked&sort_type=desc'
            response = requests.get(url,headers=headers).json()
            for each_ip in response['data']:
                this_proxy = f"{each_ip['ip']}:{each_ip['port']}"
                # print(this_proxy)
                self.unverify_proxy.append(this_proxy)
            self.geo_start_page = self.geonode_page

    def _verify_proxy(self):
        self.finish = 0
        self.pro = tqdm(total=len(self.unverify_proxy))
        for each_proxy in self.unverify_proxy:
            Thread(target=self._test_connect, args=(each_proxy,),daemon=True).start()
            
        while self.finish<len(self.unverify_proxy):
            time.sleep(1)
        self.pro.close()
        self.unverify_proxy = []

    def _test_connect(self,proxy):
        if (len(self.proxy_list)>=self.num):
            return
        try:
            result = requests.get(self.url,# 'https://ip.seeip.org/jsonip?',
                        proxies={'http': proxy, 'https': proxy},
                        timeout=5)
            self.proxy_list.append(proxy)
        except Exception as e:
            pass
        finally:
            self.pro.update(1)
            self.finish += 1


if __name__ == "__main__":
    p = Proxies(url = "https://api.wolfx.jp/cwa_eew.json")\
        .set_p(6)\
        .set_num(10)\
        .add_ssl_proxies()\
        .build()



    print(p.proxy_list)