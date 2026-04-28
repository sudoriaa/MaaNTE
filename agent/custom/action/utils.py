import time
import cv2
import numpy as np

from utils.logger import logger


def get_image(controller):
    """截屏并返回图像。"""
    job = controller.post_screencap()
    job.wait()
    return controller.cached_image


def click_rect(controller, rect):
    """点击矩形区域中心，自动输出操作日志。"""
    x, y, w, h = rect
    cx = x + w // 2
    cy = y + h // 2
    controller.post_click(cx, cy).wait()
    logger.substep(f"点击 ({cx}, {cy})")


def click_at(controller, x, y):
    """点击指定坐标，自动输出操作日志。"""
    controller.post_click(x, y).wait()
    logger.substep(f"点击 ({x}, {y})")


def press_key(controller, key_code, key_name="?"):
    """按下并释放按键，自动输出操作日志。"""
    controller.post_key_down(key_code)
    time.sleep(0.1)
    controller.post_key_up(key_code)
    logger.substep(f"按键 [{key_name}]")


def match_template_in_region(img, region, template, min_similarity=0.8):
    """在指定区域内做模板匹配。

    region 格式: [x, y, w, h]
    返回: (found, similarity, match_x, match_y)
    """
    if img is None or not isinstance(img, np.ndarray):
        return False, 0.0, 0, 0

    x1, y1, w, h = region
    x2, y2 = x1 + w, y1 + h

    img_h, img_w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img_w, x2), min(img_h, y2)

    if x2 <= x1 or y2 <= y1:
        return False, 0.0, 0, 0

    roi = img[y1:y2, x1:x2]

    if len(roi.shape) == 3 and roi.shape[2] == 4:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

    res = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    if max_val >= min_similarity:
        return True, max_val, x1 + max_loc[0], y1 + max_loc[1]
    return False, max_val, 0, 0


def wait_for_template(controller, region, template, min_similarity=0.8,
                      timeout=60, check_freq=0.5, description=""):
    """轮询等待模板出现，自动输出等待和找到日志。

    Returns:
        (match_x, match_y) 或 (None, None) 超时未找到
    """
    label = f" ({description})" if description else ""
    logger.substep(f"等待目标{label}出现")
    start = time.time()
    while time.time() - start < timeout:
        img = get_image(controller)
        found, _, mx, my = match_template_in_region(img, region, template, min_similarity)
        if found:
            logger.substep(f"找到目标{label}")
            return mx, my
        time.sleep(check_freq)
    logger.warning(f"等待目标{label}超时")
    return None, None
