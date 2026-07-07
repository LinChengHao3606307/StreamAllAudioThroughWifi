import soundcard as sc
from logging_utils import setup_logging, get_logger

setup_logging()
logger = get_logger("view_soundcards")
logger.info("所有录音设备：")
for mic in sc.all_microphones():
    logger.info(" - %s", mic.name)