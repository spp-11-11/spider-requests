# -*- coding: utf-8 -*-
"""深圳 7 天天气（requests + 正则）

相比原版的改动：
1. 请求加 timeout
2. 所有 re.search(...).group(1) 换成 safe_search，匹配失败返回空串而不是抛 AttributeError
3. 输出加表头对齐，结构更清楚
"""
import html
import re
import sys

import requests

try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "http://www.weather.com.cn/weather/101280601.shtml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
}
TIMEOUT = 15


def safe_search(pattern, text, default=""):
    """正则取第一组，匹配不到返回默认值，避免 NoneType.group 报错"""
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else default


def parse(text):
    """解析 7 天预报，返回 dict 列表"""
    rows = []
    ul_match = re.search(r'<ul class="t clearfix">(.*?)</ul>', text, re.S)
    if not ul_match:
        return rows
    ul = ul_match.group(1)

    for li in re.findall(r'<li class="sky skyid[^"]*">(.*?)</li>', ul, re.S):
        day = safe_search(r"<h1>(.*?)</h1>", li)
        if not day:
            continue
        weather = safe_search(r'<p[^>]*class="wea"[^>]*>(.*?)</p>', li)
        tem = safe_search(r'<p class="tem">(.*?)</p>', li)
        high = safe_search(r"<span>(.*?)</span>", tem)
        low = safe_search(r"<i>(.*?)</i>", tem)
        win = safe_search(r'<p class="win">(.*?)</p>', li)
        wind_dir = re.findall(r'<span title="(.*?)"', win)
        wind_lvl = html.unescape(safe_search(r"<i>(.*?)</i>", win))
        rows.append({
            "day": day,
            "weather": weather,
            "high": high,
            "low": low,
            "wind_dir": wind_dir[0] if wind_dir else "",
            "wind_lvl": wind_lvl,
        })
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

    print("%-12s %-10s %-6s %-6s %-10s %s" % ("日期", "天气", "最高", "最低", "风向", "风力"))
    print("-" * 62)
    for r in rows:
        print("%-12s %-10s %-6s %-6s %-10s %s" % (
            r["day"], r["weather"], r["high"], r["low"], r["wind_dir"], r["wind_lvl"]))
    print("\n共 %d 天" % len(rows))


if __name__ == "__main__":
    main()
