import time
import json
from pathlib import Path
import cv2

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from utils.logger import logger
from .utils import get_image, match_template_in_region, press_key


@AgentServer.custom_action("auto_fish")
class AutoFish(CustomAction):
    abs_path = Path(__file__).parents[3]
    if Path.exists(abs_path / "assets"):
            image_dir = abs_path / "assets/resource/base/image/auto_fish"
    else:
        image_dir = abs_path / "resource/base/image/auto_fish"
    continue_img = image_dir / "continue.png"
    valid_region_left_img = image_dir / "valid_region_left.png"
    valid_region_right_img = image_dir / "valid_region_right.png"
    slider_img = image_dir / "slider.png"
    success_catch_img = image_dir / "success_catch.png"
    escape_img = image_dir / "escape.png"

    slider_template = cv2.imread(str(slider_img), cv2.IMREAD_COLOR)
    valid_region_left_template = cv2.imread(str(valid_region_left_img), cv2.IMREAD_COLOR)
    valid_region_right_template = cv2.imread(str(valid_region_right_img), cv2.IMREAD_COLOR)
    continue_template = cv2.imread(str(continue_img), cv2.IMREAD_COLOR)
    success_catch_template = cv2.imread(str(success_catch_img), cv2.IMREAD_COLOR)
    escape_template = cv2.imread(str(escape_img), cv2.IMREAD_COLOR)

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        logger.task("自动钓鱼 开始")
        controller = context.tasker.controller

        fishing_count = 10
        check_freq = 0.01
        if argv.custom_action_param:
            try:
                params = json.loads(argv.custom_action_param)
                fishing_count = params.get("count", 10)
                check_freq = params.get("freq", 0.01)
            except:
                pass

        KEY_A = 65
        KEY_D = 68
        KEY_F = 70
        KEY_ESC = 27

        # 区域格式: [x, y, w, h]
        success_region = [520, 160, 265, 30]
        settlement_region = [564, 642, 642, 22]
        game_region = [400, 33, 482, 30]
        escape_region = [590, 349, 99, 22]

        for i in range(fishing_count):
            if context.tasker.stopping:
                return CustomAction.RunResult(success=False)
            logger.task(f"钓鱼 {i + 1}/{fishing_count}")

            while True:
                if context.tasker.stopping:
                    return CustomAction.RunResult(success=False)

                press_key(controller, KEY_F, "F (抛竿)")

                while True:
                    if context.tasker.stopping:
                        return CustomAction.RunResult(success=False)
                    time.sleep(check_freq)
                    img = get_image(controller)
                    m_catch, _, _, _ = match_template_in_region(img, success_region, self.success_catch_template, 0.8)
                    if m_catch:
                        press_key(controller, KEY_F, "F (提竿)")
                        logger.info("鱼已上钩！")
                        break

                start_time = time.time()
                frame = 0
                deadzone = 15

                while time.time() - start_time < 100:
                    if context.tasker.stopping:
                        return CustomAction.RunResult(success=False)
                    time.sleep(check_freq)
                    img = get_image(controller)
                    frame += 1

                    if frame % 10 == 0:
                        m_settle, _, _, _ = match_template_in_region(img, settlement_region, self.continue_template, 0.8)
                        if m_settle:
                            logger.info("鱼已钓上！")
                            break
                        m_escape, _, _, _ = match_template_in_region(img, escape_region, self.escape_template, 0.8)
                        if m_escape:
                            logger.warning("鱼逃脱，重新抛竿")
                            break

                    m_left, _, x_left, _ = match_template_in_region(img, game_region, self.valid_region_left_template, 0.7)
                    m_right, _, x_right, _ = match_template_in_region(img, game_region, self.valid_region_right_template, 0.7)
                    m_slider, _, x_slider, _ = match_template_in_region(img, game_region, self.slider_template, 0.7)

                    if m_slider:
                        if frame % 10 == 0:
                            press_key(controller, KEY_F, "F (拉竿)")

                        if m_left and m_right:
                            target = (x_left + x_right) / 2
                            offset = x_slider - target
                        elif not m_left and m_right:
                            offset = x_slider - x_right
                        elif m_left and not m_right:
                            offset = x_slider - x_left
                        else:
                            offset = 0

                        if m_left or m_right:
                            if offset > deadzone:
                                controller.post_key_up(KEY_D)
                                controller.post_key_down(KEY_A)
                            elif offset < -deadzone:
                                controller.post_key_up(KEY_A)
                                controller.post_key_down(KEY_D)
                            else:
                                controller.post_key_up(KEY_A)
                                controller.post_key_up(KEY_D)

                controller.post_key_up(KEY_D)
                controller.post_key_up(KEY_A)
                controller.post_key_up(KEY_F)

                img = get_image(controller)
                time.sleep(0.3)
                m_escape, _, _, _ = match_template_in_region(img, escape_region, self.escape_template, 0.8)
                if m_escape:
                    continue
                break

            # 关闭结算界面
            img = get_image(controller)
            match_settle, _, _, _ = match_template_in_region(img, settlement_region, self.continue_template, 0.8)
            if match_settle:
                logger.substep("关闭结算界面")
                for _ in range(5):
                    press_key(controller, KEY_ESC, "ESC")
                    time.sleep(1)
                    img = get_image(controller)
                    m, _, _, _ = match_template_in_region(img, settlement_region, self.continue_template, 0.8)
                    if not m:
                        break

        logger.task("自动钓鱼 完成")
        return CustomAction.RunResult(success=True)
