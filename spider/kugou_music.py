# -*- coding: utf-8 -*-
"""酷狗音乐排行榜采集（requests + BeautifulSoup）→ CSV

相比原版的改动：
1. 请求加 timeout
2. 单条解析加容错（缺 span / 缺 title 时跳过，不再 IndexError）
3. 每页 try/except，单页失败不中断
4. 抽出 parse_page / main，加上 __main__ 入口
"""
import csv
import os
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
OUT_CSV = os.path.join(BASE_DIR, "kugou_music.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
}
TIMEOUT = 15
PAGE_SLEEP = 1
PAGES = 23


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
    total = 0
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["排名", "歌曲", "歌手", "时长"])

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
                    writer.writerow(row)
                total += len(rows)
                print("  本页 %d 条，累计 %d 条" % (len(rows), total))
            except requests.RequestException as e:
                print("  请求失败：%s %s" % (type(e).__name__, str(e)[:120]))
            except Exception as e:
                print("  解析异常：%s %s" % (type(e).__name__, str(e)[:120]))
            time.sleep(PAGE_SLEEP)

    print("\n完成：共采集 %d 首" % total)
    print("输出文件：%s" % OUT_CSV)


if __name__ == "__main__":
    main()
