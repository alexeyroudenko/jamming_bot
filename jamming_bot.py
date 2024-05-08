import os
import sys
import csv
from datetime import datetime
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from databases import Database
import asyncio

from tld import get_tld
import validators
import signal
import time
import logging, sys


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
        return {"hostname": urlparse(url).hostname, "url": url, "visited":0}

    def init_data(self):
        with open('top500Domains.csv', newline='') as csv_file:
            spamreader = csv.reader(csv_file, delimiter=',', quotechar='\"')
            for row in spamreader:
                self.filters.append(self.clean_url(''.join(row[1])))
                self.filters.append("mailto")



class NetSpider():
    """NetSpider my spider
       TODO: add sites screenshots
    """
    def __init__(self):
        self.step_number = 0
        self.is_active = True
        self.filter = UrlsFilter()
        pass

    async def create_db(self):
        logging.info("create_db")
        #now = datetime.now()
        #date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        #self.db_name = f"db_{date_time}.db"
        self.db_name = "database.db"
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
            print("Exception1:", e)
            pass

    async def step(self):
        #logging.info("self.step", str(self.step_number))
        self.step_number = self.step_number + 1
        query = "SELECT id, hostname, url, src_url, count(visited) FROM Urls where visited==0 GROUP BY hostname ORDER BY count(visited) LIMIT 1"
        rows = await self.database.fetch_all(query=query)
        try:
            #print(rows)
            url_id = rows[0][0]
            current_url = rows[0][2]
            src_url = rows[0][3]
            query = f"UPDATE Urls SET visited=1 WHERE id={url_id}"
            await self.database.execute(query=query)
            current_domain = urlparse(current_url).hostname
            current_site = urlparse(current_url).scheme + "://" + urlparse(current_url).netloc
            valid = validators.url(current_url)
            if valid:
                res = get_tld(current_url, as_object=True)
                current_base_domain = res.fld
                try:
                    response = requests.get(current_url, timeout=1)
                    soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")
                    logging.info(f"step {self.step_number} \t {src_url} > {current_url}")
                    link_elements = soup.select("a[href]")
                    for link_element in link_elements:
                        url = link_element['href']
                        url = requests.compat.urljoin(current_site, url)
                        url = self.filter.clean_url(url)
                        if not "javascript" in url and not current_base_domain in self.filter.filters and not "mailto" in url:
                            values = self.filter.get_values(url)
                            values['src_url'] = current_url
                            query = "INSERT OR IGNORE INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
                            await self.database.execute(query=query, values=values)
                        #if self.step > 5:
                        #    break
                except Exception as e:
                    #print("Exception1:", e)
                    pass

        except Exception as e:
            print(f"Exception2: {rows}", e)

    """
    Controls
    """
    async def start(self, start_url):
        logging.info("start")
        await self.create_db()
        await self.set_visited(start_url)
        self.step_number = 0

    def stop(self):
        pass

    def reset(self):
        pass



async def main():
    killer = GracefulKiller()
    spider = NetSpider()
    await spider.start('http://www.arthew0.ru/')
    try:
        while True:
            if spider.is_active:
                await spider.step()
            else:
                time.sleep(1)
            if killer.kill_now:
                break
    except KeyboardInterrupt as ex:
        print('goodbye!')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        handlers=[
                            logging.FileHandler("crowler.log"),
                            logging.StreamHandler(sys.stdout)
                        ],
                        # filemode='a',
                        encoding='utf-8',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')
    #main()
    asyncio.run(main())
