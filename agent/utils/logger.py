import html
import os
import sys
from typing import Any

from . import pienv

LEVEL_SHORT_NAMES = {
    "INFO": "info",
    "ERROR": "err",
    "WARNING": "warn",
    "DEBUG": "debug",
    "CRITICAL": "critical",
    "SUCCESS": "success",
    "TRACE": "trace",
}

ANSI_LEVEL_COLORS = {
    "TRACE": "\033[34m",
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "SUCCESS": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[41m\033[37m",
}

# ---- ANSI 样式常量 ----
# 通用 SGR 参数
ANSI_BOLD = "1"
ANSI_DIM = "2"
ANSI_ITALIC = "3"
ANSI_UNDERLINE = "4"

# 前景色 (3-bit)
ANSI_FG_BLACK = "30"
ANSI_FG_RED = "31"
ANSI_FG_GREEN = "32"
ANSI_FG_YELLOW = "33"
ANSI_FG_BLUE = "34"
ANSI_FG_MAGENTA = "35"
ANSI_FG_CYAN = "36"
ANSI_FG_WHITE = "37"
ANSI_FG_GRAY = "90"

# 背景色 (3-bit)
ANSI_BG_BLACK = "40"
ANSI_BG_RED = "41"
ANSI_BG_GREEN = "42"
ANSI_BG_YELLOW = "43"
ANSI_BG_BLUE = "44"
ANSI_BG_MAGENTA = "45"
ANSI_BG_CYAN = "46"
ANSI_BG_WHITE = "47"

ANSI_RESET = "[0m"


def styled(msg, fg=None, bg=None, bold=False, dim=False, italic=False, underline=False):
    """用 ANSI 转义码包裹消息，支持自定义前景色、背景色和样式。

    Args:
        msg: 消息文本
        fg: 前景色代码 (如 ANSI_FG_BLUE 或 "34")
        bg: 背景色代码 (如 ANSI_BG_YELLOW 或 "43")
        bold: 加粗
        dim: 暗淡
        italic: 斜体
        underline: 下划线
    Returns:
        带 ANSI 转义码的字符串
    """
    codes = []
    if bold:
        codes.append(ANSI_BOLD)
    if dim:
        codes.append(ANSI_DIM)
    if italic:
        codes.append(ANSI_ITALIC)
    if underline:
        codes.append(ANSI_UNDERLINE)
    if fg:
        codes.append(fg)
    if bg:
        codes.append(bg)
    if not codes:
        return msg
    prefix = "[" + ";".join(codes) + "m"
    return f"{prefix}{msg}{ANSI_RESET}"


# 预定义样式快捷函数
def style_task(msg):
    """任务名称样式：蓝色加粗"""
    return styled(msg, fg=ANSI_FG_BLUE, bold=True)


def style_substep(msg):
    """子步骤样式：灰色"""
    return styled(msg, fg=ANSI_FG_GRAY)


def style_warn_large(msg):
    """醒目警告样式：黄色背景 + 加粗 + 分隔线"""
    line = "─" * 52
    return styled(f"{line}
  {msg}
{line}", fg=ANSI_FG_YELLOW, bold=True, bg=ANSI_BG_BLACK)


HTML_LEVEL_COLORS = {
    "TRACE": "royalblue",
    "DEBUG": "deepskyblue",
    "INFO": "forestgreen",
    "SUCCESS": "forestgreen",
    "WARNING": "darkorange",
    "ERROR": "crimson",
    "CRITICAL": "firebrick",
}


def _client_name_key() -> str:
    return pienv.client_name().strip().upper()


def _is_mfaa_client() -> bool:
    return _client_name_key() == "MFAAVALONIA"


def _is_mxu_client() -> bool:
    return _client_name_key() == "MXU"


def _resolve_console_stream():
    if _is_mxu_client():
        return sys.stdout
    return sys.stderr


def _resolve_console_format() -> str:
    if _is_mfaa_client():
        return "{extra[level_short]}:{message}"
    if _is_mxu_client():
        return "{extra[mxu_html_message]}"
    return "{extra[level_color]}{time:HH:mm:ss.SSS} | {level: <8} | {name} | {message}{extra[color_reset]}"

def _short_level_name(level_name: str) -> str:
    return LEVEL_SHORT_NAMES.get(level_name, level_name.lower())


def _ansi_level_color(level_name: str) -> str:
    return ANSI_LEVEL_COLORS.get(level_name, "")


def _format_mxu_html_message(level_name: str, message: str) -> str:
    color = HTML_LEVEL_COLORS.get(level_name, "inherit")
    return f'<span style="color:{color};">{html.escape(message)}</span>'


def _enrich_record(record) -> bool:
    level_name = record["level"].name
    level_color = _ansi_level_color(level_name)

    record["extra"]["level_short"] = _short_level_name(level_name)
    record["extra"]["level_color"] = level_color
    record["extra"]["color_reset"] = "\033[0m" if level_color else ""
    record["extra"]["mxu_html_message"] = _format_mxu_html_message(
        level_name, str(record["message"])
    )
    return True


_HAS_LOGURU = False
_loguru_logger: Any = None

try:
    from loguru import logger as _imported_loguru_logger

    _loguru_logger = _imported_loguru_logger
    _HAS_LOGURU = True
except ImportError:
    pass

import logging
from logging.handlers import TimedRotatingFileHandler


class _ConsoleFormatter(logging.Formatter):
    def format(self, record):
        level_name = record.levelname
        message = record.getMessage()

        if _is_mfaa_client():
            return f"{_short_level_name(level_name)}:{message}"
        if _is_mxu_client():
            return _format_mxu_html_message(level_name, message)

        level_color = _ansi_level_color(level_name)
        color_reset = "[0m" if level_color else ""
        ts = self.formatTime(record, datefmt="%H:%M:%S")
        return f"{level_color}{ts} | {level_name:<8} | {record.name} | {message}{color_reset}"

_FILE_FORMAT = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)
_std_logger = logging.getLogger("maante")


def _resolve_level(level) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def _setup_loguru_logger(log_dir="debug/custom", console_level="INFO"):
    os.makedirs(log_dir, exist_ok=True)
    _loguru_logger.remove()

    _loguru_logger.add(
        _resolve_console_stream(),
        format=_resolve_console_format(),
        colorize=False,
        level=console_level,
        filter=_enrich_record,
    )
    _loguru_logger.add(
        f"{log_dir}/{{time:YYYY-MM-DD}}.log",
        rotation="00:00",
        retention="2 weeks",
        compression="zip",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=_enrich_record,
    )
    return _loguru_logger


def _setup_std_logger(log_dir="debug/custom", console_level="INFO"):
    os.makedirs(log_dir, exist_ok=True)

    _std_logger.handlers.clear()
    _std_logger.setLevel(logging.DEBUG)
    _std_logger.propagate = False

    console_handler = logging.StreamHandler(_resolve_console_stream())
    console_handler.setLevel(_resolve_level(console_level))
    console_handler.setFormatter(_ConsoleFormatter())
    _std_logger.addHandler(console_handler)

    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "runtime.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FILE_FORMAT)
    _std_logger.addHandler(file_handler)

    return _std_logger


def setup_logger(log_dir="debug/custom", console_level="INFO"):
    """设置 logger（优先 loguru，无 loguru 时回退到标准 logging）"""
    if _HAS_LOGURU:
        return _setup_loguru_logger(log_dir=log_dir, console_level=console_level)
    return _setup_std_logger(log_dir=log_dir, console_level=console_level)


def change_console_level(level="DEBUG"):
    """动态修改控制台日志等级"""
    setup_logger(console_level=level)
    logger.info(f"控制台日志等级已更改为: {level}")


logger = setup_logger()


# ---- 为 logger 注入样式方法 ----
def _logger_task(self, msg, *args, **kwargs):
    return self.info(style_task(str(msg)), *args, **kwargs)


def _logger_substep(self, msg, *args, **kwargs):
    return self.debug(style_substep(str(msg)), *args, **kwargs)


def _logger_warn_large(self, msg, *args, **kwargs):
    return self.warning(style_warn_large(str(msg)), *args, **kwargs)


def _logger_styled(self, msg, fg=None, bg=None, bold=False, dim=False, italic=False, underline=False, level="info", *args, **kwargs):
    """通用样式日志方法。
    
    Args:
        msg: 消息文本
        fg/bg/bold/dim/italic/underline: 样式参数，同 styled()
        level: 日志级别 ("debug"/"info"/"warning"/"error"/"critical")
    """
    wrapped = styled(str(msg), fg=fg, bg=bg, bold=bold, dim=dim, italic=italic, underline=underline)
    log_func = getattr(self, level, self.info)
    return log_func(wrapped, *args, **kwargs)


logger.task = _logger_task.__get__(logger)
logger.substep = _logger_substep.__get__(logger)
logger.warn_large = _logger_warn_large.__get__(logger)
logger.styled = _logger_styled.__get__(logger)

__all__ = ["setup_logger", "change_console_level", "logger", "styled", "style_task", "style_substep", "style_warn_large"]