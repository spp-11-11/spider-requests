# -*- coding: utf-8 -*-
"""豆瓣读书 Top250 采集（requests + 正则）→ CSV

相比原版的改动：
1. 输出到脚本所在目录的 douban_book_top250.csv（原版写的是 19.douban_book_top250.csv）
2. 请求加 timeout，网络卡住不会一直挂着
3. 每页单独 try/except，单页失败不影响整体
4. 解析逻辑抽成 parse_page，方便单独测试
"""
import csv
import os
import re
import sys
import time

import requests

# 让 Windows 控制台正常显示中文
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE_DIR, "douban_book_top250.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
    "Referer": "https://book.douban.com/",
}
TIMEOUT = 15
PAGE_SLEEP = 2


def parse_page(page_html):
    """解析一页，返回书籍 dict 列表"""
    books = []
    tr_list = re.findall(r'<tr class="item">(.*?)</tr>', page_html, re.S)
    for tr in tr_list:
        name = re.findall(r'<div class="pl2">.*?<a[^>]*title="([^"]*)"', tr, re.S)
        name = name[0].strip() if name else ""

        info = re.findall(r'<p class="pl">(.*?)</p>', tr, re.S)
        info_text = re.sub(r"<.*?>", "", info[0]).strip() if info else ""
        info_text = re.sub(r"\s+", " ", info_text)

        rating = re.findall(r'<span class="rating_nums">(.*?)</span>', tr, re.S)
        rating = rating[0].strip() if rating else ""

        votes = re.findall(r'<span class="pl">\(\s*(\d+)人评价\s*\)', tr, re.S)
        votes = votes[0] if votes else ""

        price = re.findall(r"([\d.]+元(?:/[\d.]+元)?)", info_text)
        price = price[0] if price else ""

        year = re.findall(r"(\d{4})", info_text)
        year = year[0] if year else ""

        pub = re.findall(r"([\u4e00-\u9fa5·]+(?:出版社|出版公司|书局|书店))", info_text)
        publisher = pub[0] if pub else ""

        parts = [x.strip() for x in info_text.split("/") if x.strip()]
        author = parts[0] if parts else ""

        if not name:
            continue

        books.append({
            "name": name,
            "author": author,
            "publisher": publisher,
            "year": year,
            "price": price,
            "rating": rating,
            "votes": votes,
        })
    return books


def main():
    total = 0
    failed = 0
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["书名", "作者", "出版社", "出版年份", "价格", "评分", "评价人数"])

        for page in range(10):
            url = "https://book.douban.com/top250?start=%d" % (page * 25)
            print("=" * 60)
            print("第 %d 页：%s" % (page + 1, url))
            try:
                res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                res.encoding = "utf-8"
                if res.status_code != 200:
                    print("  状态码异常：%s" % res.status_code)
                    failed += 1
                    continue
                books = parse_page(res.text)
                if not books:
                    print("  未解析到数据（页面结构变化或被反爬拦截）")
                    failed += 1
                    continue
                for b in books:
                    print("《%s》 | 作者: %s | 出版社: %s | 年份: %s | 价格: %s | 评分: %s | %s人评价"
                          % (b["name"], b["author"], b["publisher"], b["year"],
                             b["price"], b["rating"], b["votes"]))
                    writer.writerow([b["name"], b["author"], b["publisher"],
                                     b["year"], b["price"], b["rating"], b["votes"]])
                total += len(books)
                print("  本页 %d 条，累计 %d 条" % (len(books), total))
            except requests.RequestException as e:
                print("  请求失败：%s %s" % (type(e).__name__, str(e)[:120]))
                failed += 1
            except Exception as e:
                print("  解析异常：%s %s" % (type(e).__name__, str(e)[:120]))
                failed += 1
            time.sleep(PAGE_SLEEP)

    print("\n完成：共采集 %d 本，失败 %d 页" % (total, failed))
    print("输出文件：%s" % OUT_CSV)


if __name__ == "__main__":
    main()
