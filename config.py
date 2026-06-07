"""配置：从环境变量 / Secret 读取

GitHub Action 部署时，所有变量通过 Secrets 注入；本地调试时可直接 os.environ 设置。
"""
import os

# 推送方式：pushplus / wxpusher / telegram / serverchan
PUSH_METHOD: str = os.getenv("PUSH_METHOD", "")

# Server 酱
SERVERCHAN_SPT: str = os.getenv("SERVERCHAN_SPT", "")

# PushPlus
PUSHPLUS_TOKEN: str = os.getenv("PUSHPLUS_TOKEN", "")

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# WxPusher：格式 appToken|uid
WXPUSHER_SPT: str = os.getenv("WXPUSHER_SPT", "")

# ⭐ 核心：在浏览器登录后抓包 /user/checkin 得到的 curl bash 整段
CHECKIN_CURL_BASH: str = os.getenv("HITUN_CURL_BASH", "")
