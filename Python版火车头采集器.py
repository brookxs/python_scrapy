# -*- coding: utf-8 -*-
from pyquery import PyQuery
from Queue import Queue
import threading
import requests
import os
import re
import urlparse

headers = {
    "User-Agent": "YisouSpider"
}


def get_html(url, encoding, num_retries=3):
    print '正在抓取：', url,
    try:
        r = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        html = ''
        if num_retries > 0:
            return get_html(url, num_retries-1)
    else:
        print '状态码', r.status_code
        r.encoding = encoding
        html = r.text
    return html


def get_diy_links(host, html, pattern, suffix):
    d = PyQuery(html)
    pattern = '{} a'.format(pattern)
    try:
        link_list = d(pattern)
    except Exception:
        yield None
    else:
        for link in link_list:
            href = PyQuery(link).attr('href').encode('utf-8')
            loc = urlparse.urlparse(href).netloc
            if not loc:
                href = host + href
            if href.endswith(suffix):
                yield href


def get_chapter_urls(host, url, encoding, pattern, suffix):
    html = get_html(url, encoding)
    return get_diy_links(host, html, pattern, suffix)


class ContentSpider(threading.Thread):
    def __init__(self, queue, writer, title_pattern, content_pattern, encoding):
        super(ContentSpider, self).__init__()
        self.queue = queue
        self.writer = writer
        self.title_pattern = title_pattern
        self.content_pattern = content_pattern
        self.encoding = encoding
        self.headers = {"User-Agent": "YisouSpider"}

    def run(self):
        while True:
            url = self.queue.get()
            html = self.get_html(url)
            title = self.parse_title(html, self.title_pattern).encode('utf-8').strip()
            content_list = self.parse_content(html, self.content_pattern)
            self.writer.write(title + os.linesep)
            for p in self.process_content(content_list):
                if len(p.strip()) > 0:
                    self.writer.write(p + os.linesep)
                    self.writer.flush()
            self.writer.write(os.linesep)
            self.queue.task_done()

    def get_html(self, url, num_retries=3):
        print 'Downloading:', url
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
        except Exception as e:
            print e
            html = ''
            if num_retries > 0:
                return self.get_html(url, num_retries-1)
        else:
            r.encoding = self.encoding
            html = r.text
        return html

    def parse_title(self, html, pattern):
        try:
            d = PyQuery(html)
        except Exception:
            title = ''
        else:
            title = d(pattern).text()
        return title

    def parse_content(self, html, pattern):
        try:
            d = PyQuery(html)
        except Exception:
            content = ''
        else:
            content = d(pattern)
        return content

    def process_content(self, content_list):
        for content in content_list:
            content = PyQuery(content).text().encode('utf-8').lower().strip()
            yield content


if __name__ == '__main__':
    # 抓取配置
    # 结果保存文件, 无需手工创建，程序自动生成
    writer = open("shehuinews.txt", 'a')
    # 要抓取的url列表页配置
    start = 2  # 起始页
    end = 5  # 结束页
    step = 1  # 公差
    chapter_indexurl = 'http://www.mnw.cn/news/shehui/'  # 列表页首页，对于不符合分页规则的列表页首页可在此添加，符合的则留空
    chapter_url = "http://www.mnw.cn/news/shehui/index-{0}.html"  # 列表页规则配置 {0}为分页页码位置
    # 详情页url所在 css 路径
    url_pattern = '.list3 .item'
    # 详情页url后缀名
    suffix = '.html'
    # 详情页标题所在标签
    title_pattern = 'h1'
    # 详情页内容所在路径 精确到段落
    content_pattern = '.icontent p'
    # 网页编码，必须填写正确，否则会出现乱码
    encoding = 'utf-8'
    # 线程数量
    num_thread = 15

    # 主程序执行部分无需修改
    queue = Queue()
    chapter_url_list = [chapter_url.format(i) for i in xrange(start, end+1, step)]
    if chapter_indexurl: chapter_url_list.insert(0, chapter_indexurl)
    for chapter_url in chapter_url_list:
        host = "http://{0}".format(urlparse.urlparse(chapter_url).netloc)
        result_urls = {url for url in get_chapter_urls(host, chapter_url, encoding, url_pattern, suffix)}
        for url in result_urls:
            queue.put(url)
    total = queue.qsize()
    for i in range(num_thread):
        c = ContentSpider(queue, writer, title_pattern, content_pattern, encoding)
        c.setDaemon(True)
        c.start()
    queue.join()
    print '抓取完毕，共抓取{}条数据'.format(total)
