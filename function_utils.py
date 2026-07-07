import sys
# 必须在导入 comtypes 前设置，统一使用 MTA 多线程 COM 模式
sys.coinit_flags = 0

from logging_utils import get_logger

import threading
import time
import re
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --------------------------
# 全局缓存 + 线程锁
# --------------------------
_volume_api = None
_volume_lock = threading.Lock()
logger = get_logger("function_utils")


def _init_volume_api():
    """内部初始化音量COM接口，仅首次调用执行"""
    global _volume_api
    if _volume_api is not None:
        return
    dev_wrapper = AudioUtilities.GetSpeakers()
    raw_device = dev_wrapper._dev
    interface = raw_device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    _volume_api = cast(interface, POINTER(IAudioEndpointVolume))


def get_windows_master_volume() -> tuple[float, bool]:
    """线程安全的系统音量读取，复用缓存COM接口"""
    global _volume_api
    with _volume_lock:
        try:
            # 首次调用或接口失效时自动重初始化
            if _volume_api is None:
                _init_volume_api()

            vol_scalar = _volume_api.GetMasterVolumeLevelScalar()
            vol_percent = int(round(vol_scalar * 100, 2))
            is_mute = bool(_volume_api.GetMute())
            return vol_percent, is_mute
        except Exception:
            # 设备插拔等异常时重置缓存，下次自动重建
            _volume_api = None
            raise



def register_listener(
    trigger_func,         # 条件判断函数，返回 True/False
    action_func,          # 触发后执行的函数
    interval=0.1,         # 轮询间隔，单位秒
    stop_event=None       # 停止信号，用于优雅退出
):
    """注册一个变量监听器，后台线程轮询检查（边沿触发：仅条件从False变True时触发一次）"""
    if stop_event is None:
        stop_event = threading.Event()

    def _polling():
        last_state = False  # 记录上一轮的条件状态
        while not stop_event.is_set():
            try:
                current_state = bool(trigger_func())
                # 仅在 上一轮假、这一轮真 的上升沿触发
                if current_state and not last_state:
                    action_func()
                last_state = current_state
            except Exception as e:
                logger.exception("监听器异常: %s", e)
            finally:
                time.sleep(interval)

    t = threading.Thread(target=_polling, daemon=True)
    t.start()
    return stop_event

def get_ip_in_url(url:str):
    pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    result = re.search(pattern, url)
    if result:
        return result.group()
    return 
        

if __name__ == "__main__":

    vol, mute = get_windows_master_volume()
    logger.info("系统音量：%s %%，静音状态：%s", vol, mute)

    # 被监控的变量（用可变容器包装，保证线程能读到最新值）
    class Status:
        count = 0

    # 触发动作
    def do_action():
        logger.info("[触发] 变量变成目标值了！当前值：%s", Status.count)

    # 注册监听器：当 count 等于 5 时触发
    stop_signal = register_listener(
        trigger_func=lambda: Status.count == 5,
        action_func=do_action,
        interval=0.1
    )

    # 模拟变量变化
    for i in range(10):
        Status.count = i
        time.sleep(0.2)
    stop_signal.set()  # 停止监听