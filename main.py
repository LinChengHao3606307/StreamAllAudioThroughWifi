
import time
import upnpclient
from threading import Thread
import re
import sys

from speaker_request_handler import SpeakerRequestHandler
from app_config import AppConfig
from vpn_utils import VpnUtil
from speaker_controller import SpeakerController
from function_utils import register_listener, get_ip_in_url, get_windows_master_volume
from logging_utils import setup_logging, get_logger, get_colored



class StreamAllAudioThroughWifiApp:

    def __init__(self, config_path):

        try:
            self.config = AppConfig(yaml_path=config_path)
            self.vpn_util = VpnUtil(config=self.config)
            self.speaker_controller = SpeakerController(config=self.config)
            self._logger = get_logger(self.config.LOGGING.LOGGER_NAME)
            setup_logging(self.config.LOGGING.LEVEL)
            SpeakerRequestHandler.set_config(config=self.config)
        except Exception as e:
            self._logger.exception(
                get_colored("初始化失败：%s", self.config.LOGGING.COLORS.ERROR),
                e
            )
            sys.exit(1)

        self.on_step = 0
        self.total_steps = 6
        self.vpn_is_turned_off = False

        self._target_device_ip = None
        self._speaker_regex_pat = re.compile(self.config.SPEAKER.NAME_REGEX)
        self._vpn_resume_listener_stop_signal = None
        self._server_thread = None
        self._http_server = None
        self._target_device = None
        self._volume = -1



    @property
    def is_complete(self):
        return self.on_step == self.total_steps

    # ===================== 主程序步骤 =====================
    def log_info(self):
        """第1步：打印启动信息"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 打印启动信息...", self.config.LOGGING.COLORS.KEY_STEP), 
            self.on_step, self.total_steps
        )
        self._logger.info("HiRes WiFi 播放系统 | %sHz / %sbit", self.config.SAMPLING.RATE, self.config.SAMPLING.WIDTH * 8)
        self._logger.info("协议: DLNA/UPnP")

        source_display = getattr(self.config.SAMPLING, "REQUIRED_SYSTEM_OUTPUT", None)
        self._logger.info(
            "系统播放设备请选择: %s", 
            get_colored(source_display, self.config.LOGGING.COLORS.OUTPUT_DEVICE_HIGHLIGHT)
        )
        self._logger.info("串流地址: %s", SpeakerRequestHandler.get_stream_url())
        if self.config.VPN.TOGGLE_IF_FAILED:
            self._logger.info("VPN临时关闭: 已启用（任意环节失败时临时关闭，之后恢复）")
        self._logger.info("启动信息打印完毕\n")

    def start_http_server(self):
        """第2步：启动HTTP串流服务"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 启动%sHz/%sbit音频串流服务...", self.config.LOGGING.COLORS.KEY_STEP), 
            self.on_step, self.total_steps, self.config.SAMPLING.RATE, self.config.SAMPLING.WIDTH * 8
        )
        if self._http_server:
            self._http_server.shutdown()
            self._http_server = None
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2)
            self._server_thread = None
        
        self._http_server = SpeakerRequestHandler.get_stream_server()
        self._http_server.allow_reuse_address = True
        self._server_thread = Thread(target=self._http_server.serve_forever, daemon=True)
        self._server_thread.start()
        time.sleep(self.config.PROGRAM_CONSTANT.HTTP_SERVER_BOOTING_TIME)
        self._logger.info("音频串流服务就绪\n")
        

    def find_speaker(self):
        """第3步：搜索局域网DLNA音箱"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 搜索局域网DLNA音频设备...", self.config.LOGGING.COLORS.KEY_STEP), 
            self.on_step, self.total_steps
        )
        devices = upnpclient.discover()
        self._logger.info("共发现 %s 个UPnP设备", len(devices))

        self._target_device = None

        for dev in devices:
            if self._speaker_regex_pat.search(dev.friendly_name):
                if hasattr(dev, 'AVTransport'):
                    self._target_device = dev
                    break
        
        if not self._target_device:
            
            self._logger.warning(
                get_colored("未找到匹配音箱", self.config.LOGGING.COLORS.WARNING), 
            )
            self._logger.info("已发现设备列表：")
            for dev in devices:
                self._logger.info(" - %s", dev.friendly_name)
            if self.config.VPN.TOGGLE_IF_FAILED and not self.vpn_is_turned_off:
                self.restart_with_vpn_off()
            else: #二次重启仍失败
                self.cleanup_and_exit()
        
        self._target_device_ip = get_ip_in_url(self._target_device.location)
    
        self._logger.info("匹配音箱: %s\n", self._target_device.friendly_name)

    def bind_controller(self):
        """第4步：把windows的音量调整绑定到音响的api"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 接入音响控制...", self.config.LOGGING.COLORS.KEY_STEP), 
            self.on_step, self.total_steps
        )
        self.speaker_controller.set_ip(self._target_device_ip)
        self.speaker_controller.power_on()
        self._logger.info("音响已启动，ip: %s\n", self._target_device_ip)
    
    def start_stream(self):
        """第5步：推送流到音箱并启动播放"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 推送HiRes实时流...", self.config.LOGGING.COLORS.KEY_STEP),
            self.on_step, self.total_steps
        )
        try:
            self._target_device.AVTransport.SetAVTransportURI(
                InstanceID=0,
                CurrentURI=SpeakerRequestHandler.get_stream_url(),
                CurrentURIMetaData=''
            )
            self._target_device.AVTransport.Play(InstanceID=0, Speed='1')
        except Exception as e:
            self._logger.exception(
                get_colored("推送失败: %s", self.config.LOGGING.COLORS.ERROR),
                e
            )
            if self.config.VPN.TOGGLE_IF_FAILED and not self.vpn_is_turned_off:
                self.restart_with_vpn_off()
            else: #二次重启仍失败
                self.cleanup_and_exit()

        source_display = getattr(self.config.SAMPLING, "REQUIRED_SYSTEM_OUTPUT", None)
        self._logger.info(
            "播放已启动！系统输出切到 %s 即可出声\n", 
            get_colored(source_display, self.config.LOGGING.COLORS.OUTPUT_DEVICE_HIGHLIGHT)
        )

    def block_until_quit(self):
        """第6步：阻塞主进程直到用户退出"""
        self.on_step += 1
        self._logger.info(
            get_colored("[%s/%s] 启动成功！用Ctrl+C 停止服务（5G WiFi 可大幅减少卡顿）", self.config.LOGGING.COLORS.KEY_STEP),
            self.on_step, self.total_steps
        )
        try:
            while True:
                volume, is_mute = get_windows_master_volume()
                prev_volume = self._volume
                self._volume = volume * (1-int(is_mute))
                if self._volume != prev_volume:
                    self.speaker_controller.delete_interval(1)
                    self.speaker_controller.set_volume(
                        self._volume
                    )
                time.sleep(self.config.PROGRAM_CONSTANT.MAIN_LOOP_INTERVAL / 1000)

        except KeyboardInterrupt:
            self._logger.info("正在停止服务...\n")
        finally:
            self.cleanup_and_exit()
    
    # ===================== 辅助进程 =====================
    def restart_with_vpn_off(self):
        """关闭VPN然后重启"""
        self._logger.warning(
            get_colored("[RST] 由于第%s步失败，即将关闭VPN，然后重新运行...", self.config.LOGGING.COLORS.RESTART), 
            self.on_step
        )
        # 1.关闭vpn
        self.vpn_util.run_vpn_command(self.config.VPN.COMMAND.DOWN, "关闭VPN")
        self.vpn_is_turned_off = True
        # 2.重置步骤计数
        self.on_step = 0
        # 3.设置vpn恢复触发
        if self._vpn_resume_listener_stop_signal:
            self._vpn_resume_listener_stop_signal.set()
            self._vpn_resume_listener_stop_signal = None
        
        def trigger_resume():
            return self.is_complete and self.vpn_is_turned_off
        def resume_vpn_action():
            self.vpn_util.run_vpn_command(self.config.VPN.COMMAND.UP, "恢复VPN")
            self.vpn_is_turned_off = False
            self._vpn_resume_listener_stop_signal.set() #恢复后立即销毁

        self._vpn_resume_listener_stop_signal = register_listener(
            trigger_resume,
            resume_vpn_action
        )
        # 4.重启
        self.run()

    def cleanup_and_exit(self):
        """优雅关闭所有资源"""
        if self.is_complete:
            self._logger.info("\n程序执行成功，准备退出...")
        else:
            self._logger.error(
                "\n由于第%s步失败，即将退出...", 
                self.on_step
            )
        SpeakerRequestHandler.is_running = False
        if self._http_server:
            self._http_server.shutdown()
        if self._vpn_resume_listener_stop_signal:
            self._vpn_resume_listener_stop_signal.set()
        if self.vpn_is_turned_off:
            self.vpn_util.run_vpn_command(self.config.VPN.COMMAND.UP, "恢复VPN")
        if self._target_device:
            try:
                self._target_device.AVTransport.Stop(InstanceID=0)
            except:
                pass
        self._logger.info("服务全部关闭\n")
        sys.exit()
        



    def run(self):

        # 第1步：打印启动信息
        self.log_info()

        # 第2步：启动HTTP串流服务
        self.start_http_server()

        # 第3步：搜索局域网DLNA音箱
        self.find_speaker()

        # 第4步：把windows的音量调整绑定到音响的api
        self.bind_controller()

        # 第5步：推送流到音箱并启动播放
        self.start_stream()

        # 第6步：阻塞主进程直到用户退出
        self.block_until_quit()
        

if __name__ == "__main__":
    wifi_music_handler = StreamAllAudioThroughWifiApp("./configs/remote_desktop kef.yaml")
    wifi_music_handler.run()