"""多种推送渠道：Server 酱 / PushPlus / Telegram / WxPusher

参考 beyond-motion/wxread 的 push.py 简化而来
"""
import json
import logging
import time

import requests

from config import (
    PUSHPLUS_TOKEN,
    SERVERCHAN_SPT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WXPUSHER_SPT,
)

logger = logging.getLogger(__name__)


class PushNotification:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}

    # -------- PushPlus --------
    def push_pushplus(self, content: str, token: str, is_success: bool) -> bool:
        url = "https://www.pushplus.plus/send"
        title = f"hitun.io-{'成功' if is_success else '失败'}"
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps({"token": token, "title": title, "content": content}),
                    headers=self.headers,
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info(f"PushPlus 响应: {resp.text[:200]}")
                return True
            except Exception as exc:
                logger.error(f"PushPlus 失败 attempt={attempt}: {exc}")
                time.sleep(2)
        return False

    # -------- Telegram --------
    def push_telegram(self, content: str, token: str, chat_id: str) -> bool:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps({"chat_id": chat_id, "text": content}),
                    headers=self.headers,
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info(f"Telegram 响应: {resp.text[:200]}")
                return True
            except Exception as exc:
                logger.error(f"Telegram 失败 attempt={attempt}: {exc}")
                time.sleep(2)
        return False

    # -------- WxPusher --------
    def push_wxpusher(self, content: str, spt: str) -> bool:
        # spt 格式：appToken|uid
        try:
            app_token, uid = spt.split("|", 1)
        except ValueError:
            logger.error("WXPUSHER_SPT 格式错误，应为 appToken|uid")
            return False
        url = f"https://wxpusher.zjiecode.com/api/send/message/{app_token}/{uid}"
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps({"content": content}),
                    headers=self.headers,
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info(f"WxPusher 响应: {resp.text[:200]}")
                return True
            except Exception as exc:
                logger.error(f"WxPusher 失败 attempt={attempt}: {exc}")
                time.sleep(2)
        return False

    # -------- Server 酱 --------
    def push_serverchan(self, content: str, spt: str, is_success: bool) -> bool:
        # spt 是 SendKey，形如 SCT... 开头的字符串
        url = f"https://sctapi.ftqq.com/{spt}.send"
        title = f"hitun.io-{'成功' if is_success else '失败'}"
        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps({"title": title, "desp": content}),
                    headers=self.headers,
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info(f"Server 酱响应: {resp.text[:200]}")
                return True
            except Exception as exc:
                logger.error(f"Server 酱失败 attempt={attempt}: {exc}")
                time.sleep(2)
        return False


def push(content: str, method: str, is_success: bool = True) -> bool:
    """统一入口：选一个推送方式把 content 发出去"""
    if not method:
        logger.warning("未配置推送渠道，跳过推送。")
        return False

    notifier = PushNotification()
    method = str(method).lower().strip()

    if method == "pushplus":
        return notifier.push_pushplus(content, PUSHPLUS_TOKEN, is_success)
    if method == "telegram":
        return notifier.push_telegram(content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    if method == "wxpusher":
        return notifier.push_wxpusher(content, WXPUSHER_SPT)
    if method == "serverchan":
        return notifier.push_serverchan(content, SERVERCHAN_SPT, is_success)

    logger.warning(f"未知推送方式: {method}，支持 pushplus/telegram/wxpusher/serverchan")
    return False
