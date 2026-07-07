import re
import struct
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
import socket

from logging_utils import get_logger

try:
    import soundcard as sc
except ImportError:  # pragma: no cover - executed when optional dependency is absent
    sc = None

from audio_sampler import AudioSampler
from app_config import AppConfig

logger = get_logger("audio_request_handler")


class AudioRequestHandler(BaseHTTPRequestHandler):
    # 类级别的默认配置（所有实例共享）
    _VIRTUAL_AUDIO_DEVICE = None
    _SAMPLE_RATE = None
    _SAMPLE_WIDTH = None
    _CHANNELS = None
    _FRAMES_PER_BUFFER = None
    _STREAM_PORT = None
    _SAMPLER = None

    # 全局运行控制标志
    is_running = True

    @classmethod
    def get_local_ip(cls):
        """获取本机局域网IP，避免返回127.0.0.1"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    @classmethod
    def get_stream_url(cls):
        local_ip = cls.get_local_ip()
        stream_url = f"http://{local_ip}:{cls._STREAM_PORT}/stream"
        return stream_url
    
    @classmethod
    def get_stream_server(cls):
        return HTTPServer(("0.0.0.0", cls._STREAM_PORT), AudioRequestHandler)
    
    @classmethod
    def resolve_virtual_audio_device(cls, config: AppConfig):
        """根据配置中的正则表达式解析当前可用的虚拟音频输入设备。"""
        sampling_cfg = getattr(config, "SAMPLING", None)
        if sampling_cfg is None:
            return None

        source_regex = getattr(sampling_cfg, "SOURCE_REGEX", None)
        if source_regex:
            try:
                if sc is None:
                    return getattr(sampling_cfg, "SOURCE", None)

                try:
                    microphones = sc.all_microphones(include_loopback=True)
                except TypeError:
                    microphones = sc.all_microphones()

                for mic in microphones:
                    mic_name = getattr(mic, "name", None) or str(mic)
                    if re.search(source_regex, mic_name):
                        return mic_name
            except Exception as exc:
                logger.warning("解析音频输入设备失败: %s", exc)

        return getattr(sampling_cfg, "SOURCE", None)

    @classmethod
    def set_config(cls, config: AppConfig):
        """类方法：全局设置配置，所有新连接的实例都会生效"""
        cls._VIRTUAL_AUDIO_DEVICE = cls.resolve_virtual_audio_device(config)
        cls._SAMPLE_RATE = config.SAMPLING.RATE
        cls._SAMPLE_WIDTH = config.SAMPLING.WIDTH
        cls._CHANNELS = config.SAMPLING.CHANNELS
        cls._FRAMES_PER_BUFFER = config.SAMPLING.FRAMES_PER_BUFFER
        cls._STREAM_PORT = config.STREAM.PORT
        cls._SAMPLER = AudioSampler(config=config)


    def build_wav_header(self, stream_mode: bool = True):
        """
        生成标准PCM WAV文件头
        :param stream_mode: 流式模式，长度填0，支持无限播放；关闭则填最大长度
        """
        if stream_mode:
            chunk_size = 0
            subchunk2_size = 0
        else:
            chunk_size = 0xFFFFFFFF
            subchunk2_size = 0xFFFFFFFF

        header = b'RIFF' + struct.pack('<I', chunk_size) + b'WAVE'
        header += b'fmt ' + struct.pack('<IHHIIHH',
            16,                         # fmt块大小，标准PCM固定16字节
            1,                          # 音频格式：1 = 线性PCM
            self._CHANNELS,             # 声道数
            self._SAMPLE_RATE,          # 采样率
            self._SAMPLE_RATE * self._CHANNELS * self._SAMPLE_WIDTH,  # 每秒字节数
            self._CHANNELS * self._SAMPLE_WIDTH,   # 块对齐
            self._SAMPLE_WIDTH * 8                # 位深
        )
        header += b'data' + struct.pack('<I', subchunk2_size)
        return header



    def do_GET(self):
        if self.path != '/stream':
            self.send_error(404, explain="Only /stream endpoint available")
            return

        # HTTP响应头：流式传输核心优化
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Accept-Ranges', 'none')  # 明确不支持断点续传，防止播放器乱发Range请求
        self.send_header('Connection', 'close')
        # 不发送Content-Length，让播放器以流的方式持续接收
        self.end_headers()

        try:
            # 获取虚拟录音设备
            mic = sc.get_microphone(self._VIRTUAL_AUDIO_DEVICE, include_loopback=True)
            frames_per_buffer = self._FRAMES_PER_BUFFER

            # 写入流式WAV头（长度为0，标识无限流）
            self.wfile.write(self.build_wav_header(stream_mode=True))

            # 循环采集音频并持续推送
            with mic.recorder(
                samplerate=self._SAMPLE_RATE,
                channels=self._CHANNELS
            ) as recorder:
                while self.is_running:
                    data = recorder.record(frames_per_buffer)
                    pcm_bytes = self._SAMPLER.float_to_n_bit_pcm(data)
                    try:
                        self.wfile.write(pcm_bytes)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        # 客户端断开直接退出循环
                        break

        # 客户端主动断开、管道错误直接忽略，不打印异常
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            logger.exception("音频流异常: %s", e)

    def log_message(self, format, *args):
        # 屏蔽默认HTTP访问日志，控制台只打印自定义异常
        return