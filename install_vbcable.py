import urllib.request
import zipfile
import subprocess
from pathlib import Path

# 配置参数
DOWNLOAD_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
BASE_DIR = Path("others/vbcable")
ZIP_FILE = BASE_DIR / "VBCABLE_Driver_Pack45.zip"
EXTRACT_ROOT = BASE_DIR / "VBCABLE_Driver_Pack45"  # 解压根目录，压缩包自带文件夹
INSTALL_EXE = EXTRACT_ROOT / "VBCABLE_Setup_x64.exe"

def main():
    # 自动创建文件夹，不存在就新建
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 下载驱动压缩包
    if not ZIP_FILE.exists():
        print(f"正在下载驱动包: {DOWNLOAD_URL}")
        try:
            urllib.request.urlretrieve(DOWNLOAD_URL, ZIP_FILE)
            print(f"下载完成，保存路径: {ZIP_FILE}")
        except Exception as e:
            print(f"下载失败: {str(e)}")
            return
    else:
        print(f"检测到 {ZIP_FILE.name} 已存在，跳过下载")

    # 2. 解压
    print("正在解压驱动包...")
    try:
        with zipfile.ZipFile(ZIP_FILE, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_ROOT)
        print("解压完成")
    except Exception as e:
        print(f"解压失败: {str(e)}")
        return

    # 3. 校验exe并运行
    if not INSTALL_EXE.exists():
        print(f"错误：找不到安装程序 {INSTALL_EXE}")
        print("压缩包目录结构异常，请手动检查")
        return
    
    print(f"启动安装程序: {INSTALL_EXE}")
    try:
        # shell=True 适配Windows，等待安装程序关闭再往下执行
        subprocess.run(str(INSTALL_EXE), check=True, shell=True)
        print("安装程序已正常退出")
    except subprocess.CalledProcessError as e:
        print(f"安装程序异常，退出码: {e.returncode}")
    except Exception as e:
        print(f"启动程序失败: {str(e)}")

if __name__ == "__main__":
    main()