import numpy as np
from app_config import AppConfig

class AudioSampler:

    def __init__(self, config: AppConfig):
        self._SAMPLE_WIDTH = config.SAMPLING.WIDTH

    def _get_np_int_type(self, n_bit: int):
        """根据位宽返回承载整型，24bit用int32存放"""
        if n_bit <= 16:
            return np.int16
        if n_bit <= 32:
            return np.int32
        if n_bit <= 64:
            return np.int64
        raise NotImplementedError(f"不支持的位宽 {n_bit}bit")

    def float_to_n_bit_pcm(self, data: np.ndarray) -> bytes:
        """浮点音频 [-1,1] 转 N bit 小端PCM二进制流"""
        n_bit = self._SAMPLE_WIDTH * 8
        np_int_type = self._get_np_int_type(n_bit)
        max_int = 2 ** (n_bit - 1) - 1

        # 限幅防止溢出
        scaled = np.clip(data, -1.0, 1.0) * max_int
        int_sample = scaled.astype(np_int_type)

        byte_list = []
        # 小端序：先低字节，依次移位提取每一字节
        for i in range(self._SAMPLE_WIDTH):
            shift_val = 8 * i
            byte_arr = ((int_sample >> shift_val) & 0xFF).astype(np.uint8)
            byte_list.append(byte_arr)

        # 堆叠字节维度，转为连续二进制
        return np.stack(byte_list, axis=-1).tobytes()