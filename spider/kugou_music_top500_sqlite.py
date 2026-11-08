# -*- coding: utf-8 -*-
"""酷狗音乐排行榜 → SQLite

相比原版的改动：
1. 补上建表语句 CREATE TABLE IF NOT EXISTS kugou（原版直接 insert，报 no such table）
2. 数据库统一放到 spider-requests/sqlite/music.db（原版写 D:/music.db，那个库并不存在）
3. 请求加 timeout，单页 try/except
4. 运行前清空旧数据，避免重复运行产生重复行
5. 整轮只开一个连接，每页插入统一提交（原版每页开关一次连接）
"""
import os
import sqlite3
import sys
import time

import requests
from bs4 import BeautifulSoup

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "sqlite", "music.db")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
}
TIMEOUT = 15
PAGE_SLEEP = 1
PAGES = 23


class MusicDB:
    """酷狗榜单的 SQLite 封装"""

    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.cur = self.conn.cursor()
        # 关键修复：没有这条建表语句就会报 no such table: kugou
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS kugou (
                num      VARCHAR(10),
                song     VARCHAR(50),
                singer   VARCHAR(50),
                duration VARCHAR(20)
            )
        """)
        self.conn.commit()

    def clear(self):
        self.cur.execute("DELETE FROM kugou")
        self.conn.commit()

    def insert(self, data):
        try:
            self.cur.execute("INSERT INTO kugou VALUES(?,?,?,?)", data)
        except sqlite3.Error as e:
            print("  写入失败：%s" % e)

    def count(self):
        self.cur.execute("SELECT COUNT(*) FROM kugou")
        return self.cur.fetchone()[0]

    def close(self):
        self.conn.commit()
        self.cur.close()
        self.conn.close()


def parse_page(page_html):
    """解析一页榜单，返回 [(排名, 歌曲, 歌手, 时长), ...]"""
    soup = BeautifulSoup(page_html, "lxml")
    rows = []
    for li in soup.select("div.pc_temp_songlist ul li"):
        try:
            num_tag = li.select_one("span.pc_temp_num")
            time_tag = li.select_one("span.pc_temp_time")
            a_tag = li.find("a")
            if not (num_tag and time_tag and a_tag):
                continue
            title = a_tag.get("title") or a_tag.get_text(strip=True) or ""
            if "-" in title:
                singer, song = title.split("-", 1)
            else:
                singer, song = "", title
            rows.append((
                num_tag.get_text(strip=True),
                song.strip(),
                singer.strip(),
                time_tag.get_text(strip=True),
            ))
        except Exception as e:
            print("  单条解析失败：%s" % e)
    return rows


def main():
    db = MusicDB()
    db.clear()
    total = 0

    for i in range(1, PAGES + 1):
        url = "https://www.kugou.com/yy/rank/home/%d-8888.html" % i
        print("=" * 60)
        print("第 %d 页：%s" % (i, url))
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.encoding = "utf-8"
            rows = parse_page(res.text)
            if not rows:
                print("  未解析到数据")
            for row in rows:
                print("  " + " | ".join(row))
                db.insert(row)
            total += len(rows)
            print("  本页 %d 条，累计 %d 条" % (len(rows), total))
        except requests.RequestException as e:
            print("  请求失败：%s %s" % (type(e).__name__, str(e)[:120]))
        except Exception as e:
            print("  解析异常：%s %s" % (type(e).__name__, str(e)[:120]))
        time.sleep(PAGE_SLEEP)

    print("\n完成：共写入 %d 首，数据库当前 %d 行" % (total, db.count()))
    db.close()
    print("数据库：%s" % os.path.abspath(DB_PATH))


if __name__ == "__main__":
    main()
