import logging

def get_colored(original_str: str, hex_color: str) -> str:
    """
    为字符串添加指定十六进制颜色的终端前景色
    
    Args:
        original_str: 原始字符串
        hex_color: 十六进制颜色码，支持 #RRGGBB 或 RRGGBB 格式
        
    Returns:
        带 ANSI 颜色转义序列的字符串，输出到终端会显示对应颜色
        
    Raises:
        ValueError: 颜色码格式非法时抛出
    """
    # 去除前缀 #
    hex_color = hex_color.lstrip('#')
    
    # 校验长度必须为 6 位
    if len(hex_color) != 6:
        raise ValueError(
            f"无效的十六进制颜色格式: {hex_color}，需为 6 位格式（如 #FF0000）"
        )
    
    # 解析 RGB 分量（0-255）
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        raise ValueError(
            f"无效的十六进制字符: {hex_color}，仅支持 0-9、a-f、A-F"
        )
    
    # ANSI 24位真彩色前景色序列 + 文本 + 重置属性序列
    # 38;2 表示前景色、24位RGB模式；\033[0m 重置所有终端属性
    return f"\033[38;2;{r};{g};{b}m{original_str}\033[0m"

def setup_logging(level=logging.INFO) -> None:
    """Initialize a consistent console logging format for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger instance."""
    return logging.getLogger(name)
