import time
import subprocess

from app_config import AppConfig
from logging_utils import get_logger, get_colored

logger = get_logger("vpn_utils")


class VpnUtil:
    def __init__(self, config: AppConfig):
        self.config = config
        self._VPN_COMMAND_WAITING_TIME = config.VPN.COMMAND.WAITING_TIME
        self._VPN_COMMAND_DELAY = config.VPN.COMMAND.DELAY
    
    def run_vpn_command(self, command: str, action_name: str):
        """
        执行VPN开关命令，失败只打印警告，不中断主流程
        """
        try:
            time.sleep(self._VPN_COMMAND_DELAY)
            logger.info(
                get_colored("[VPN] 正在%s...", self.config.LOGGING.COLORS.VPN_OPERATION), 
                action_name
            )
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    get_colored("[VPN] %s成功\n", self.config.LOGGING.COLORS.VPN_OPERATION), 
                    action_name
                )
            else:
                logger.error(
                    get_colored("[VPN] %s失败，错误信息：%s\n", self.config.LOGGING.COLORS.ERROR), 
                    action_name, result.stderr.strip()
                )
            time.sleep(self._VPN_COMMAND_WAITING_TIME)
        except Exception as e:
            logger.exception(
                get_colored("[VPN] %s异常\n", self.config.LOGGING.COLORS.ERROR), 
                action_name
            )