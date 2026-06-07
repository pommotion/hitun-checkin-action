#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hitun.io 自动签到
参考 beyond-motion/wxread 的 curl_bash 回放模式
"""

import json
import logging
import re
import sys
from typing import Optional

import requests

from config import (
    CHECKIN_CURL_BASH,
    PUSH_METHOD,
)
from log_utils import setup_logging
from push import push

logger = logging.getLogger(__name__)


# -------- 响应文本判定关键词 --------
SUCCESS_KEYWORDS = ["签到成功", "成功", "获得流量", "已领取", "续命"]  # hitun.io 叫"续命"
ALREADY_KEYWORDS = ["已签到", "今日已签", "已经签到", "签到过", "已领取过", "续命过", "已经续命", "似乎已经"]
AUTH_FAIL_KEYWORDS = ["未登录", "未注册", "请先登录", "session", "登录失败", "邮箱或密码", "token", "授权", "邮箱未"]
CF_FAIL_KEYWORDS = ["cloudflare", "turnstile", "captcha", "验证码", "challenge", "just a moment"]
NETWORK_FAIL_KEYWORDS = ["403", "503", "access denied", "forbidden"]


def parse_curl(curl_str: str) -> dict:
    """解析 curl bash 字符串，提取 method / url / headers / cookies / body

    兼容两种 cookie 写法：
      - -H 'Cookie: xxx'
      - -b 'xxx'
    """
    if not curl_str or not curl_str.strip():
        raise ValueError("curl bash 字符串为空")

    # 1. method（缺省 POST）
    method_match = re.search(r"-X\s+['\"]?([A-Z]+)['\"]?", curl_str, re.I)
    method = method_match.group(1).upper() if method_match else "POST"

    # 2. url
    url_match = re.search(
        r"curl\s+(?:-X\s+['\"]?[A-Z]+['\"]?\s+)?['\"]?(https?://[^'\"\s]+)['\"]?",
        curl_str,
        re.I,
    )
    if not url_match:
        raise ValueError("无法从 curl bash 中提取 URL")
    url = url_match.group(1)

    # 3. headers（引号配对：header 值可能含双引号如 sec-ch-ua）
    headers = {}
    for m in re.finditer(r"-H\s+", curl_str):
        rest = curl_str[m.end():]
        if not rest:
            continue
        # 找引号包裹的 header string
        first = rest[0]
        if first not in ("'", '"'):
            continue
        end = rest.find(first, 1)
        if end < 0:
            continue
        header_str = rest[1:end]
        colon = header_str.find(':')
        if colon < 0:
            continue
        key = header_str[:colon].strip()
        val = header_str[colon+1:].strip()
        if key.lower() == "cookie":
            continue
        headers[key] = val

    # 4. cookies：优先 -b，回退 -H 'Cookie:'
    cookies: dict[str, str] = {}
    cookie_str = ""
    b_match = re.search(r"-b\s+['\"]([^'\"]+)['\"]", curl_str)
    if b_match:
        cookie_str = b_match.group(1)
    else:
        c_match = re.search(r"-H\s+['\"]Cookie:\s*([^'\"]+)['\"]", curl_str, re.I)
        if c_match:
            cookie_str = c_match.group(1)

    if cookie_str:
        for item in cookie_str.split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()

    # 5. body
    body = None
    body_match = re.search(r"--data(?:-raw|-binary|-urlencode)?\s+", curl_str, re.I)
    if body_match:
        rest = curl_str[body_match.end():]
        if rest:
            first = rest[0]
            if first in ("'", '"'):
                # 引号包裹的 body：找到下一个同字符引号
                end = rest.find(first, 1)
                body = rest[1:end] if end > 0 else rest[1:]
            else:
                # 无引号：取到行尾
                body = rest.split("\n", 1)[0].rstrip("\\").strip()

    # 6. 补全关键 header
    if not any(k.lower() == "user-agent" for k in headers):
        headers["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    if not any(k.lower() == "accept" for k in headers):
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
    if not any(k.lower() == "x-requested-with" for k in headers):
        headers["X-Requested-With"] = "XMLHttpRequest"

    return {
        "method": method,
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "body": body,
    }


def classify(text: str, status: int) -> tuple[str, bool]:
    """根据响应文本/状态码分类：(结果描述, 是否成功)"""
    if status >= 500:
        return (f"❌ 服务器异常 HTTP {status}\n响应: {text[:200]}", False)

    # 尝试 JSON 解析
    ret, msg = None, text
    try:
        data = json.loads(text)
        ret = data.get("ret")
        msg = data.get("msg", "")
    except Exception:
        pass

    if ret == 1:
        return (f"✅ 签到成功 — {msg}", True)
    if any(k in msg for k in ALREADY_KEYWORDS):
        return (f"✅ 今日已签到 — {msg}", True)
    if any(k in msg for k in AUTH_FAIL_KEYWORDS):
        return (
            f"❌ Cookie 失效 — {msg}\n"
            f"💡 请浏览器重新登录 hitun.io 后抓包更新 HITUN_CURL_BASH",
            False,
        )
    if any(k.lower() in text.lower() for k in CF_FAIL_KEYWORDS):
        return (
            f"❌ Cloudflare 拦截 — {text[:200]}\n"
            f"💡 GitHub Action 跑 requests 容易被 CF 拦，可改用本地 Mac/NAS 跑",
            False,
        )
    if status == 403:
        return (f"❌ HTTP 403 拒绝访问 — {text[:200]}", False)
    if ret == 0:
        return (f"❌ 业务失败 ret=0 — {msg}", False)

    return (f"⚠️ 未知响应\nHTTP {status}\nret={ret}\nmsg={msg}\n原始: {text[:300]}", False)


def run_checkin() -> tuple[bool, str]:
    """执行一次签到，返回 (成功标志, 描述)"""
    if not CHECKIN_CURL_BASH:
        msg = "❌ 缺少 HITUN_CURL_BASH secret，请在 repo Settings → Secrets 中配置"
        logger.error(msg)
        return False, msg

    try:
        spec = parse_curl(CHECKIN_CURL_BASH)
    except Exception as e:
        msg = f"❌ 解析 curl_bash 失败: {e}"
        logger.exception(msg)
        return False, msg

    logger.info(f"目标: {spec['method']} {spec['url']}")
    logger.info(f"Cookie 数量: {len(spec['cookies'])} | Header 数量: {len(spec['headers'])}")
    if spec["body"]:
        logger.info(f"Body: {spec['body'][:120]}")

    session = requests.Session()
    session.headers.update(spec["headers"])
    session.cookies.update(spec["cookies"])

    try:
        if spec["method"] == "GET":
            resp = session.get(spec["url"], timeout=30)
        else:
            resp = session.request(
                spec["method"],
                spec["url"],
                data=spec["body"],
                timeout=30,
                allow_redirects=False,
            )
    except requests.RequestException as e:
        msg = f"❌ 网络异常: {e}"
        logger.exception(msg)
        return False, msg

    desc, success = classify(resp.text.strip(), resp.status_code)
    if success:
        logger.info(desc)
    else:
        logger.error(desc)

    # 补充元信息
    meta = (
        f"\n\n---\n"
        f"🕐 时间: {resp.headers.get('Date', '')}\n"
        f"🌐 端点: {spec['url']}\n"
        f"🍪 Cookie 字段: {', '.join(list(spec['cookies'].keys())[:6])}"
    )
    return success, desc + meta


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("hitun.io 自动签到启动")
    logger.info("=" * 60)

    success, desc = run_checkin()

    if PUSH_METHOD:
        logger.info(f"推送结果（{PUSH_METHOD}）...")
        push(desc, PUSH_METHOD, is_success=success)
    else:
        logger.info("未配置推送渠道，跳过推送")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
