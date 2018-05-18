import re
import time
import pickle
from selenium import webdriver
from pyquery import PyQuery as pq
from db import RedisQueue
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import pymongo
import threading

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument(
    '--user-data-dir=C:\\Users\\lx\\AppData\\Local\\Google\\Chrome\\User Data')
browser = webdriver.Firefox()
wait = WebDriverWait(browser, 10)


MONGO_URL = 'localhost'
MONGO_DB = 'wenshu'
MONGO_COLLECTION = 'wenshu'
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

queue = RedisQueue()
URL = 'http://wenshu.court.gov.cn/list/list/?sorttype=1&number=GKXHF5CE&guid=0aef5a25-a03b-3dfcb27f-7af4bb80f708&conditions=searchWord+2+AJLX++%E6%A1%88%E4%BB%B6%E7%B1%BB%E5%9E%8B:%E6%B0%91%E4%BA%8B%E6%A1%88%E4%BB%B6&conditions=searchWord+%E5%B9%BF%E4%B8%9C%E7%9C%81%E6%B7%B1%E5%9C%B3%E5%B8%82%E4%B8%AD%E7%BA%A7%E4%BA%BA%E6%B0%91%E6%B3%95%E9%99%A2+++%E4%B8%AD%E7%BA%A7%E6%B3%95%E9%99%A2:%E5%B9%BF%E4%B8%9C%E7%9C%81%E6%B7%B1%E5%9C%B3%E5%B8%82%E4%B8%AD%E7%BA%A7%E4%BA%BA%E6%B0%91%E6%B3%95%E9%99%A2'
PAGE = 10


def index_page():
        # 爬取页面的超链接并放入redis，并且点击下一页,(看能否使用多线程，一个爬主页，一个存信息T)
    try:
        url = 'http://wenshu.court.gov.cn/list/list/?sorttype=1&number=GKXHF5CE&guid=0aef5a25-a03b-3dfcb27f-7af4bb80f708&conditions=searchWord+2+AJLX++%E6%A1%88%E4%BB%B6%E7%B1%BB%E5%9E%8B:%E6%B0%91%E4%BA%8B%E6%A1%88%E4%BB%B6&conditions=searchWord+%E5%B9%BF%E4%B8%9C%E7%9C%81%E6%B7%B1%E5%9C%B3%E5%B8%82%E4%B8%AD%E7%BA%A7%E4%BA%BA%E6%B0%91%E6%B3%95%E9%99%A2+++%E4%B8%AD%E7%BA%A7%E6%B3%95%E9%99%A2:%E5%B9%BF%E4%B8%9C%E7%9C%81%E6%B7%B1%E5%9C%B3%E5%B8%82%E4%B8%AD%E7%BA%A7%E4%BA%BA%E6%B0%91%E6%B3%95%E9%99%A2'
        browser.get(url)
        wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '#resultList > div:nth-child(1) > table > tbody > tr:nth-child(2) > td > div'), '广东'))
        time.sleep(5)
        html = browser.page_source
        page = re.findall('<span.class="current">(\d+)</span>', html, re.S)
        print('正在爬取第%d页' % (int(page[0])))
        for i in range(1, PAGE):
            if i > 1:
                print('正在爬取第%d页' % i)
                wait.until(EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, '#resultList > div:nth-child(1) > table > tbody > tr:nth-child(2) > td > div'), '广东'))
                browser.find_element_by_link_text("下一页").click()
                time.sleep(10)
            if i == 10:
                browser.close()
            get_page(html)
    except TimeoutException:
        browser.refresh()


def get_page(h):

    pq_html = pq(h)
    doc = pq_html('.wstitle').items()
    for t in doc:
        # 这里不知道为什么，如果不把pquery对象转为html，就没办法提取a节点的href
        links = 'http://wenshu.court.gov.cn' + \
            pq(pq(t).html()).find('a').eq(1).attr('href')
        queue.add(links)


def get_text():
        # 判断队列是否为空，不为空就循环下去
    url_text = queue.pop()
    browser2 = webdriver.Firefox()
    browser2.get(url_text)
    # wait.until(EC.presence_of_element_located((By.ID, 'DivContent')))
    time.sleep(5)
    html_text = browser2.page_source
    doc_text = pq(html_text)
    contents = {
        'title': doc_text.find('#contentTitle').text(),
        'date': doc_text.find('#tdFBRQ').text(),
        'text': doc_text.find('#DivContent').text(),
    }
    print(len(contents))

    save_to_mongo(contents)
    browser2.quit()


def save_to_mongo(result):
    # 保存图片信息到mongo
    try:
        if db[MONGO_COLLECTION].insert(result):
            print('储存成功')
    except Exception:
        print('储存失败')


def main():

    #t1 = threading.Thread(target=index_page)
    t2 = threading.Thread(target=get_text, args=())
    # t1.start()
    time.sleep(5)
    while not queue.empty():
        get_text()
    # t1.join()
    while queue.empty():

        browser2.close()


if __name__ == '__main__':
    main()
'''
threads = []
t1 = threading.Thread(target=index_page, args=())
threads.append(t1)

t2 = threading.Thread(target=get_text, args=())
threads.append(t2)

if __name__ == '__main__':
    for t in threads:
        t.start()
    for t in threads:
        t.join()
'''
