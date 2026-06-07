"""日志初始化：输出到 stdout，GitHub Action 会自动捕获"""
import logging
import sys


def setup_logging() -> None:
    fmt = "%(asctime)s | %(levelname)-7s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # 抑制第三方库刷屏
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
