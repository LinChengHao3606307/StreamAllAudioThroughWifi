import http.server
import socketserver
import threading
import socket
import time
import os
import upnpclient

from logging_utils import setup_logging, get_logger

# ========================== 配置项 ==========================
AUDIO_FILE = "test.mp3"    # 先用MP3测试，兼容性最好
HTTP_PORT = 8000           # 端口可自定义，避开占用
SPEAKER_NAME_KEYWORD = "LSX"
logger = get_logger("static_file_test")
# ===========================================================

def get_local_ip():
    """获取本机局域网IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def start_http_server():
    """启动静态文件HTTP服务，后台运行"""
    handler = http.server.SimpleHTTPRequestHandler
    # 关闭默认日志，需要调试可注释此行
    handler.log_message = lambda *args, **kwargs: None
    
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("0.0.0.0", HTTP_PORT), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd

def main():
    # 前置检查
    if not os.path.exists(AUDIO_FILE):
        logger.error("当前目录找不到文件 %s", AUDIO_FILE)
        logger.info("当前工作目录：%s", os.getcwd())
        return
    
    local_ip = get_local_ip()
    audio_url = f"http://{local_ip}:{HTTP_PORT}/{AUDIO_FILE}"
    
    logger.info("=" * 55)
    logger.info("DLNA 音频播放测试（与QQ音乐同协议）")
    logger.info("音频地址: %s", audio_url)
    logger.info("=" * 55)

    # 1. 启动HTTP服务
    logger.info("[1/4] 启动本地HTTP服务...")
    http_server = start_http_server()
    time.sleep(0.5)
    logger.info("HTTP服务已启动")

    # 2. 搜索局域网DLNA设备
    logger.info("[2/4] 搜索DLNA音频渲染设备...")
    devices = upnpclient.discover()
    logger.info("共发现 %s 个UPnP设备", len(devices))
    
    target_device = None
    for dev in devices:
        logger.info(" - %s", dev.friendly_name)
        # 匹配音箱名称，同时校验是否有播放控制服务
        if SPEAKER_NAME_KEYWORD.lower() in dev.friendly_name.lower():
            if hasattr(dev, 'AVTransport'):
                target_device = dev
                break
    
    if not target_device:
        logger.error("未找到匹配的DLNA播放设备")
        http_server.shutdown()
        return
    
    logger.info("[3/4] 已匹配音箱: %s", target_device.friendly_name)

    # 4. 推送播放地址并启动播放
    logger.info("[4/4] 推送音频到音箱播放...")
    try:
        # 设置播放URI
        target_device.AVTransport.SetAVTransportURI(
            InstanceID=0,
            CurrentURI=audio_url,
            CurrentURIMetaData=''
        )
        # 开始播放
        target_device.AVTransport.Play(
            InstanceID=0,
            Speed='1'
        )
        logger.info("播放指令已发送！音箱应该马上出声了")
    except Exception as e:
        logger.exception("播放失败: %s", e)
        http_server.shutdown()
        return

    logger.info("%s", "\n" + "-" * 40)
    logger.info("播放中... 按 Ctrl+C 停止并退出")
    
    # 保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在停止播放...")
        try:
            target_device.AVTransport.Stop(InstanceID=0)
        except:
            pass
        http_server.shutdown()
        logger.info("程序已退出")

if __name__ == "__main__":
    setup_logging()
    main()