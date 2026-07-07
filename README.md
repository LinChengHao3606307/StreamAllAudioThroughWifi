# Win11WifiStreamAllAudio

Win11WifiStreamAllAudio 是一个面向 Windows 11 的本地音频转发工具。它会从系统输出中捕获音频（默认通过 VB-Audio Virtual Cable），将其封装为流媒体并推送给局域网内的 DLNA/UPnP 音箱，实现“把电脑上的所有声音同步到音箱”的效果。

## 项目目标

- 捕获 Windows 系统音频
- 将音频流通过 HTTP 实时推送给音箱
- 通过 DLNA/UPnP 控制音箱播放
- 同步调整 Windows 主音量到音箱音量
- 在异常时自动切换 VPN，提升连接可靠性

## 适用场景

- 将电脑上的系统音频实时送到 KEF、Sonos 等支持 DLNA/UPnP 的音箱
- 适合家庭影音、音乐播放、会议音频转发等场景
- 当前配置示例以 KEF LSX II 为目标，使用 Postman 集合驱动控制命令

## 项目结构

- main.py：主程序入口，负责启动整个流程
- audio_request_handler.py：采集系统音频并提供 HTTP 流接口
- audio_sampler.py：将浮点音频转为 PCM 二进制流
- speaker_controller.py：通过 Postman 请求控制音箱开关、音量等
- vpn_utils.py：执行 VPN 开关命令
- app_config.py：加载 YAML 配置
- configs/kef-lsx ii.yaml：当前示例配置文件
- speaker_api/KEF-LSX II.postman_collection.json：KEF 音箱控制请求集合
- others/：辅助脚本，如查看声卡、测试静态文件流等
- tests/：自动化回归测试

## 依赖要求

- Windows 11
- Python 3.10+（建议 3.11）
- VB-Audio Virtual Cable（用于把系统音频转成可捕获输入）
  - 官方下载地址：https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip
- 可用的 DLNA/UPnP 音箱
- 可选：Tailscale 或其他 VPN 工具（配置中已支持自动切换）

## 安装步骤

1. 创建虚拟环境

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. 安装依赖

```powershell
pip install -r requirements.txt
```

3. 配置音频源和音箱

编辑配置文件：

```text
configs/kef-lsx ii.yaml
```

你需要重点确认以下配置：

- SAMPLING.SOURCE_REGEX：匹配你实际安装的虚拟音频输入设备名称
- SPEAKER.NAME_REGEX：匹配局域网中的音箱名称
- SPEAKER.COMMAND.POSTMAN_COLLECTION：对应音箱控制请求集合文件
- VPN.COMMAND：根据你本机的 VPN 工具路径进行配置

## 运行方式

### 方式一：使用批处理脚本

```powershell
runWifiMusic.bat
```

### 方式二：直接运行 Python

```powershell
python main.py
```

## 使用流程

程序启动后会依次执行：

1. 读取配置文件
2. 启动 HTTP 音频流服务
3. 搜索局域网中的 DLNA/UPnP 音箱
4. 连接音箱控制接口
5. 推送实时音频流并开始播放
6. 持续同步系统音量到音箱

## 关键配置说明

### 音频采集

```yaml
SAMPLING:
  RATE: 96000
  WIDTH: 3
  CHANNELS: 2
  FRAMES_PER_BUFFER: 2048
  SOURCE_REGEX: ^CABLE Output \(VB-Audio Virtual Cable\)$
```

这里的 `SOURCE_REGEX` 会根据当前系统中存在的录音设备自动匹配目标输入源。只要你的系统中有对应的虚拟音频设备名称，程序就会使用它进行采集。

### 音箱控制

```yaml
SPEAKER:
  NAME_REGEX: LSX
  COMMAND:
    POSTMAN_COLLECTION: "./speaker_api/KEF-LSX II.postman_collection.json"
```

当前示例配置面向 KEF LSX II 的控制接口，使用 Postman 集合中的请求来完成开机、待机、音量获取和设置。

## 常见问题

### 1. 没有找到音箱

检查以下内容：

- `SPEAKER.NAME_REGEX` 是否匹配到你的音箱名称
- 音箱是否和电脑处于同一局域网
- 音箱是否支持 UPnP/DLNA 控制

### 2. 没有声音

检查以下内容：

- `SAMPLING.SOURCE_REGEX` 是否正确匹配到 VB-Audio Virtual Cable
- 系统输出是否已经切到对应虚拟音频设备
- 是否已经安装并启用了 VB-Audio Virtual Cable

### 3. Postman 请求失败

检查：

- `speaker_api/KEF-LSX II.postman_collection.json` 是否存在
- 请求名称是否与当前配置中的 `NAME` 字段一致
- 网络环境是否允许访问音箱控制接口

## 辅助脚本

- others/view_soundcards.py：查看当前系统中的录音设备
- others/static_file_test.py：用于测试静态文件流和 DLNA 播放逻辑

## 备注

此项目当前以 Windows 11 本机环境为主，依赖系统级音频设备和音箱控制能力。若你要适配其他音箱或不同音频设备，需要修改配置文件和相应的控制集合。
