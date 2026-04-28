import time
import json
from pathlib import Path
import cv2

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from utils.logger import logger
from .utils import get_image, match_template_in_region, click_rect, click_at, press_key, wait_for_template


@AgentServer.custom_action("auto_make_coffee")
class AutoMakeCoffee(CustomAction):
    def __init__(self):
        super().__init__()
        abs_path = Path(__file__).parents[3]
        if Path.exists(abs_path / "assets"):
            image_dir = abs_path / "assets/resource/base/image/auto_make_coffee"
        else:
            image_dir = abs_path / "resource/base/image/auto_make_coffee"
        start_img = image_dir / "start.png"
        star_img = image_dir / "star.png"
        claim_img = image_dir / "claim.png"

        self.start_template = cv2.imread(str(start_img), cv2.IMREAD_COLOR)
        self.star_template = cv2.imread(str(star_img), cv2.IMREAD_COLOR)
        self.claim_template = cv2.imread(str(claim_img), cv2.IMREAD_COLOR)

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        logger.task("Auto Make Coffee 开始")
        controller = context.tasker.controller
        make_count = 10
        check_freq = 0.5
        if argv.custom_action_param:
            try:
                params = json.loads(argv.custom_action_param)
                make_count = params.get("count", 10)
                check_freq = params.get("freq", 0.5)
            except:
                pass

        # Coordinates mapped from auto_make_coffee.json [x, y, w, h]
        select_level_target = [18, 230, 188, 66]
        click_roi = [28, 272, 65, 56]
        start_roi = [1057, 648, 178, 44]
        star_roi = [1204, 109, 29, 27]
        star_target = [11, 12, 38, 37]
        claim_roi = [681, 539, 187, 38]

        for count in range(make_count):
            if context.tasker.stopping:
                return CustomAction.RunResult(success=False)
            logger.task(f"制作咖啡 {count + 1}/{make_count}")

            # Step 1: 选择关卡
            click_rect(controller, select_level_target)
            time.sleep(1)

            # Step 2: 等待并点击开始营业
            mx, my = wait_for_template(controller, start_roi, self.start_template,
                                       0.8, 30, check_freq, "开始营业")
            if mx is None:
                return CustomAction.RunResult(success=False)
            click_at(controller, mx, my)
            time.sleep(3)

            # Step 3: 达成营业额
            while True:
                if context.tasker.stopping:
                    return CustomAction.RunResult(success=False)
                click_rect(controller, click_roi)
                img = get_image(controller)
                match_star, _, _, _ = match_template_in_region(img, star_roi, self.star_template, 0.9)
                if match_star:
                    click_rect(controller, star_target)
                    time.sleep(1)
                    break
                time.sleep(2)

            # Step 4: 等待并点击领取
            mx, my = wait_for_template(controller, claim_roi, self.claim_template,
                                       0.8, 30, check_freq, "领取奖励")
            if mx is not None:
                click_at(controller, mx, my)
                time.sleep(1)

            press_key(controller, 70, "F")
            time.sleep(2)

        logger.task("Auto Make Coffee 完成")
        return CustomAction.RunResult(success=True)
