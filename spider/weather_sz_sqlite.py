# -*- coding: utf-8 -*-
"""深圳 7 天天气 → SQLite（lxml XPath）

相比原版的改动：
1. 补上建表语句 CREATE TABLE IF NOT EXISTS tt（原版直接 insert，报 no such table）
2. 数据库统一放到 spider-requests/sqlite/weather.db（原版写 D:/weather.db）
3. 请求加 timeout，XPath 取值全部做空值保护
4. 同一天重复运行先删后插，避免重复行
"""
import html
import os
import sqlite3
import sys

import lxml.etree as etree
import requests

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "sqlite", "weather.db")

URL = "http://www.weather.com.cn/weather/101280601.shtml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
}
TIMEOUT = 15


class WeatherDB:
    """天气数据的 SQLite 封装"""

    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.cur = self.conn.cursor()
        # 关键修复：没有这条建表语句就会报 no such table: tt
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS tt (
                date  varchar(20),
                tq    varchar(30),
                temp  varchar(30),
                wind  varchar(30)
            )
        """)
        self.conn.commit()

    def delete_date(self, date):
        self.cur.execute("DELETE FROM tt WHERE date = ?", (date,))

    def insert(self, data):
        """data = (date, tq, temp, wind)"""
        try:
            self.cur.execute("INSERT INTO tt VALUES(?,?,?,?)", data)
        except sqlite3.Error as e:
            print("  写入失败：%s" % e)

    def count(self):
        self.cur.execute("SELECT COUNT(*) FROM tt")
        return self.cur.fetchone()[0]

    def close(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()


def xp_first(node, path, default=""):
    """取 XPath 第一个文本，取不到返回默认值"""
    vals = node.xpath(path)
    return vals[0].strip() if vals else default


def parse(text):
    """解析 7 天预报，返回入库元组列表"""
    tree = etree.HTML(text)
    rows = []
    for li in tree.xpath('//ul[@class="t clearfix"]/li'):
        day = xp_first(li, "./h1/text()")
        if not day:
            continue
        weather = xp_first(li, './p[@class="wea"]/text()')
        high = xp_first(li, './p[@class="tem"]/span/text()')
        low = xp_first(li, './p[@class="tem"]/i/text()')
        wind_lvl = html.unescape(xp_first(li, './p[@class="win"]/i/text()'))
        # 当天（今天）网页只给夜间温度，没有 span，此时只写一个温度，避免出现 "/20℃"
        if high and low:
            temp = "%s/%s" % (high, low)
        else:
            temp = high or low
        rows.append((day, weather, temp, wind_lvl))
    return rows


def main():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
        res.encoding = "utf-8"
        if res.status_code != 200:
            print("状态码异常：%s" % res.status_code)
            return
    except requests.RequestException as e:
        print("请求失败：%s %s" % (type(e).__name__, str(e)[:120]))
        return

    rows = parse(res.text)
    if not rows:
        print("未解析到天气数据，页面结构可能已变化")
        return

    db = WeatherDB()
    for row in rows:
        db.delete_date(row[0])   # 同一天覆盖，避免重复行
        db.insert(row)
        print("  ", row)

    print("\n写入 %d 条，数据库当前 %d 行" % (len(rows), db.count()))
    db.close()
    print("数据库：%s" % os.path.abspath(DB_PATH))


if __name__ == "__main__":
    main()
