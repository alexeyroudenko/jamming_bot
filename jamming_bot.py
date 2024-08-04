#!/home/pi/jamming_bot/.venv/bin/python
import os
import sys
import csv
from datetime import datetime
import time
from urllib.parse import urlparse
import traceback
import requests
from bs4 import BeautifulSoup
from databases import Database
import asyncio

from tld import get_tld
import validators
import signal
import time
import coloredlogs,logging, sys
import yaml
from yaml.loader import SafeLoader

from pythonosc import udp_client

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


class UrlsFilter():
    """UrlsFilter big sites
       TODO: add big sites automaticaly
    """
    def __init__(self):
        self.filters = []
        self.init_data()

    def clean_url(self, url):
        return url.replace("www.", "")

    def get_values(self, url):
        hostname = urlparse(url).hostname
        data = {"hostname": hostname, "url": url, "visited":0}
        logger.debug(f"get values {hostname} {url} {data}")
        return data

    def init_data(self):
        filename = 'top500Domains.csv'
        logging.info(f"init_data {filename}")
        with open(filename, newline='') as csv_file:
            spamreader = csv.reader(csv_file, delimiter=',', quotechar='\"')
            for row in spamreader:
                self.filters.append(self.clean_url(''.join(row[1])))
                self.filters.append("mailto")

class NetSpider():
    """NetSpider my spider
       TODO: add sites screenshots
    """
    def __init__(self, sleep_time, osc_address):
        self.filter = UrlsFilter()
        self.sleep_time = sleep_time
        self.step_number = 0
        self.is_active = True
        self.count_errors = 0

        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        logging.info(f"my ip {ip}")
        logging.info(f"osc address ip {osc_address}")
        #mask = [0,0,0,255]
        #broadcast = [(ioctet | ~moctet) & 0xff for ioctet, moctet in zip(ip, mask)]
        #print(broadcast)

        self.osc = udp_client.SimpleUDPClient(osc_address, 8000)
        pass

    async def create_db(self):
        logging.info("create_db")
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.db_name = f"db_{date_time}.db"
        # self.db_name = "database.db"
        resume = False
        if os.path.exists(self.db_name):
            resume = True
            logging.info("resume db")
            #os.remove(self.db_name)
        self.database = Database(f'sqlite+aiosqlite:///{self.db_name}')
        await self.database.connect()
        if not resume:
            logging.info("create new db")
            query = """CREATE TABLE Urls (id INTEGER PRIMARY KEY, hostname VARCHAR(127), url VARCHAR(127) unique, src_url VARCHAR(127), visited INTEGER)"""
            await self.database.execute(query=query)

    async def set_visited(self, url):
        logging.info("set_visited", url)
        try:
            values = self.filter.get_values(url)
            query = "INSERT INTO Urls(hostname, url, visited) VALUES (:hostname, :url, :visited)"
            await self.database.execute(query=query, values=values)
        except Exception as e:
            print("Exception set_visited:", e)
            pass
    
    async def insert(self, url):
        logging.info(f"insert {url}")
        try:
            logging.info(f"self.filter {self.filter}")
            values = self.filter.get_values(url)
            logging.info(f"values {url}")
            query = "INSERT INTO Urls(hostname, url, visited) VALUES (:hostname, :url, :visited)"
            await self.database.execute(query=query, values=values)
        except Exception as e:
            logging.error(f"Exception insert {traceback.print_exc()}")
            pass

    async def step(self):
        #logging.debug(f"self.step {str(self.step_number)}")
        self.step_number = self.step_number + 1
        query = "SELECT id, hostname, url, src_url, count(visited) FROM Urls where visited==0 GROUP BY hostname ORDER BY count(visited) LIMIT 1"        
        rows = await self.database.fetch_all(query=query)
        try:
            url_id = rows[0][0]
            hostname = rows[0][1]
            current_url = rows[0][2]
            src_url = rows[0][3]
            query = f"UPDATE Urls SET visited=1 WHERE id={url_id}"            
            await self.database.execute(query=query)
            
            current_domain = urlparse(current_url).hostname
            current_site = urlparse(current_url).scheme + "://" + urlparse(current_url).netloc
            valid = validators.url(current_site)
            # id , hostname, current_url unique, src_url
            #logging.debug(f"try id:{url_id} hostname:{hostname} \t target:{current_url} \tsrc: {src_url} \t  valid:{valid}")

            if valid:
                res = get_tld(current_url, as_object=True)
                current_base_domain = res.fld
                try:
                    response = requests.get(current_url, timeout=1, stream=True)
                    ip, port = response.raw._connection.sock.getpeername()                    
                    soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")                    
                    link_elements = soup.select("a[href]")                    
                    logging.info(f"step {self.step_number} \t {src_url} > {current_url} \t {len(link_elements)} \t {ip}")
                    data = [self.step_number, src_url, current_url, len(link_elements), ip]
                    
                    try:
                        self.osc.send_message("/step", data)
                    except Exception as e0:
                        logging.error(f"error send OSC: {e0}")

                    count_elements = 0
                    for link_element in link_elements:
                        count_elements += 1
                        if count_elements > 10:
                           break

                        url = link_element['href']
                        href = link_element['href']
                        if not "javascript" in url and not "mailto" in url:
                            new_hostname = urlparse(url).hostname    
                            if not new_hostname:
                                #adding as subpage
                                full_url = requests.compat.urljoin(current_site, url)
                                url = self.filter.clean_url(full_url)
                            
                            if not new_hostname: 
                                values = self.filter.get_values(full_url)
                                values['src_url'] = current_url
                                values['hostname'] = current_domain
                                query = "INSERT OR IGNORE INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
                                #logger.debug(f"added urls {values}")
                                logger.debug(f"add local href {href} because host {new_hostname} \t values{values}")
                                await self.database.execute(query=query, values=values)
                            else:
                                if self.filter.clean_url(new_hostname) in self.filter.filters:
                                    logger.debug(f"skip href {href} because host {new_hostname}")
                                else:   
                                    values = self.filter.get_values(href)
                                    values['hostname'] = new_hostname
                                    values['url'] = href
                                    values['src_url'] = current_url
                                    logger.debug(f"add href {href} because host {new_hostname} \t values{values}")
                                    query = "INSERT OR IGNORE INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
                                    await self.database.execute(query=query, values=values)

                        # if self.step_number > 5:
                        #     exit()

                except Exception as e1:
                    logging.error(f"Exception step 1 {e1}")
                    #print("Exception in step 1:", e, traceback.print_exc())
                    pass

        except Exception as e2:
            self.count_errors += 1
            logging.error(f"Exception step 2 {e2}")
            #print(f"Exception in step 2: {rows}", e, traceback.print_exc())
            if self.count_errors > 10:
                self.stop()
                exit()
            pass

    """
    Controls
    """
    async def start(self, start_url):
        logging.info(f"start with {start_url}")
        await self.create_db()
        await self.insert(start_url)
        self.step_number = 0
        try:
            self.osc.send_message("/start", {})
        except Exception as e0:
            logging.error(f"error send OSC: {e0}")

    def stop(self):
        try:
            self.osc.send_message("/stop", {})
        except Exception as e0:
            logging.error(f"error send OSC: {e0}")
        pass

    def reset(self):
        pass



async def main():
    config_file = "jamming_bot.yaml"
    with open(config_file) as file:
        config = yaml.load(file, Loader=SafeLoader)

    killer = GracefulKiller()
    spider = NetSpider(config['sleep_time'], config['osc_adress'])
    await spider.start(config['start_url'])
    try:
        while True:
            if spider.is_active:
                await spider.step()
                time.sleep(spider.sleep_time)
                # if spider.step_number > 5:
                #     break
            # else:
                # time.sleep(spider.sleep_time)
            if killer.kill_now:
                break
    except KeyboardInterrupt as ex:
        print('goodbye!')


if __name__ == '__main__':
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"db_{date_time}.log"
    
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        handlers=[
                            logging.FileHandler(log_file_name),
                            logging.StreamHandler(sys.stdout)
                        ],
                        # filemode='a',
                        encoding='utf-8',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    logger = logging.getLogger() 
    coloredlogs.install(level="INFO", logger=logger)
    coloredlogs.install(fmt='%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s')
    asyncio.run(main())
