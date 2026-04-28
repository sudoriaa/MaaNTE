import time
import json
import cv2
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.resource import Resource
from maa.tasker import Tasker
from maa.pipeline import JRecognitionType, JOCR

from utils.logger import logger
from .utils import get_image, match_template_in_region, click_rect, press_key


@AgentServer.custom_action("auto_buy_fish_bait")
class AutoBuyFishBait(CustomAction):
    abs_path = Path(__file__).parents[3]
    if Path.exists(abs_path / "assets"):
            image_dir = abs_path / "assets/resource/base/image/auto_buy_fish_bait"
    else:
        image_dir = abs_path / "resource/base/image/auto_buy_fish_bait"
    bait_img = image_dir / "bait.png"
    find_bait_success_img = image_dir / "find_bait_success.png"
    select_max_img = image_dir / "select_max.png"
    buy_img = image_dir / "buy.png"
    buy_confirm_img = image_dir / "buy_confirm.png"
    buy_success_img = image_dir / "buy_success.png"
    bait_template = cv2.imread(str(bait_img), cv2.IMREAD_COLOR)
    find_bait_success_template = cv2.imread(str(find_bait_success_img), cv2.IMREAD_COLOR)
    select_max_template = cv2.imread(str(select_max_img), cv2.IMREAD_COLOR)
    buy_template = cv2.imread(str(buy_img), cv2.IMREAD_COLOR)
    buy_confirm_template = cv2.imread(str(buy_confirm_img), cv2.IMREAD_COLOR)
    buy_success_template = cv2.imread(str(buy_success_img), cv2.IMREAD_COLOR)

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        bait_region = [208, 209, 59, 27]
        fish_shop_region = [35, 88, 410, 475]
        find_bait_success_region = [1044, 131, 68, 23]
        select_max_region = [1202, 620, 33, 32]
        buy_region = [1050, 674, 50, 25]
        buy_confirm_region = [749, 462, 47, 25]
        buy_success_region = [569, 629, 145, 19]
        not_enough_shell_region = [1170, 585, 18, 16]
        shell_count_region = [961, 31, 70, 21]
        KEY_R = 82
        KEY_ESC = 27
        controller = context.tasker.controller
        logger.task("自动购买鱼饵 开始")

        # 在鱼铺中找到鱼饵
        while True:
            img = get_image(controller)
            found_bait, _, x, y = match_template_in_region(img, fish_shop_region, self.bait_template, 0.8)
            if found_bait:
                for _ in range(3):
                    click_rect(controller, [x, y, bait_region[2], bait_region[3]])
                    time.sleep(0.1)
                img = get_image(controller)
                found_bait_success, _, _, _ = match_template_in_region(img, find_bait_success_region, self.find_bait_success_template, 0.8)
                if found_bait_success:
                    time.sleep(0.5)
                    break
            else:
                logger.warning("鱼铺中未找到鱼饵，按 R 键刷新")
                press_key(controller, KEY_R, "R")
                time.sleep(1)

        # 点击最大数量
        while True:
            img = get_image(controller)
            found_select_max, _, _, _ = match_template_in_region(img, select_max_region, self.select_max_template, 0.8)
            if found_select_max:
                for _ in range(3):
                    click_rect(controller, select_max_region)
                    time.sleep(0.1)
                time.sleep(0.5)
                break
            else:
                time.sleep(1)

        # 点击购买
        while True:
            img = get_image(controller)
            found_buy, _, _, _ = match_template_in_region(img, buy_region, self.buy_template, 0.8)
            if found_buy:
                for _ in range(3):
                    click_rect(controller, buy_region)
                    time.sleep(0.1)
                time.sleep(0.5)
                break
            else:
                time.sleep(1)

        # 点击确认购买
        for _ in range(5):
            img = get_image(controller)
            found_buy_confirm, _, _, _ = match_template_in_region(img, buy_confirm_region, self.buy_confirm_template, 0.8)
            if found_buy_confirm:
                for _ in range(3):
                    click_rect(controller, buy_confirm_region)
                    time.sleep(0.1)
                time.sleep(0.5)
                break
            else:
                time.sleep(0.2)

        # 等待购买成功
        while True:
            img = get_image(controller)
            found_buy_success, _, _, _ = match_template_in_region(img, buy_success_region, self.buy_success_template, 0.8)
            if found_buy_success:
                logger.info("购买成功")
                press_key(controller, KEY_ESC, "ESC")
                time.sleep(0.5)
                press_key(controller, KEY_ESC, "ESC")
                break
            else:
                time.sleep(1)

        logger.task("自动购买鱼饵 完成")
        return CustomAction.RunResult(success=True)
