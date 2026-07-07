import re
import yaml
from pathlib import Path
from typing import Union, Optional


# 自定义Loader：仅true/false识别为布尔，on/off/yes/no保持字符串
class NoBoolLoader(yaml.SafeLoader):
    @classmethod
    def set_bool_resolver(cls):
        # 清除原有布尔自动匹配规则
        bool_tag = "tag:yaml.org,2002:bool"
        new_resolvers = {}
        for char, rules in yaml.resolver.Resolver.yaml_implicit_resolvers.items():
            new_rules = []
            for tag, regex in rules:
                if tag == bool_tag:
                    # 只匹配纯 true/false，屏蔽 on/off/yes/no
                    new_re = re.compile(r"^(true|True|TRUE|false|False|FALSE)$")
                    new_rules.append((bool_tag, new_re))
                else:
                    new_rules.append((tag, regex))
            new_resolvers[char] = new_rules
        yaml.resolver.Resolver.yaml_implicit_resolvers = new_resolvers

# 初始化覆盖布尔规则
NoBoolLoader.set_bool_resolver()


class AppConfig:
    """YAML 配置加载类，自动屏蔽ON/OFF转布尔"""
    def __init__(self, yaml_path: Optional[Union[str, Path]] = None, raw_data: Optional[dict] = None):
        if yaml_path is not None:
            assert isinstance(yaml_path, (str, Path)), "路径必须为str或Path类"
            assert raw_data is None, "不能同时提供路径和数据，会产生歧义"
            self.yaml_path = Path(yaml_path).resolve()
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                raw_data = yaml.load(f, Loader=NoBoolLoader) or {}

        if raw_data is not None:
            assert isinstance(raw_data, dict), "raw_data 必须是字典"
            self._load_data(raw_data=raw_data)
        else:
            raise ValueError("必须传入 yaml_path 或 raw_data 其中一项")

    def _load_data(self, raw_data: dict):
        for k, v in raw_data.items():
            if isinstance(v, dict):
                setattr(self, k, AppConfig(raw_data=v))
            else:
                setattr(self, k, v)



if __name__ == "__main__":
    from logging_utils import setup_logging, get_logger
    import logging

    setup_logging(level=logging.DEBUG)
    logger = get_logger("app_config")
    config = AppConfig("./configs/b2903_5g_kef.yaml")
    logger.info("SPEAKER COMMAND POWER ON: %s", config.SPEAKER.COMMAND.POWER.ON)
    logger.info("SPEAKER COMMAND POWER OFF: %s", config.SPEAKER.COMMAND.POWER.OFF)
    logger.info("SPEAKER COMMAND POWER ON TYPE: %s", type(config.SPEAKER.COMMAND.POWER.ON))
    logger.info("SPEAKER COMMAND VOLUME GET: %s", config.SPEAKER.COMMAND.VOLUME.GET)
    logger.info("SPEAKER PORT: %s", config.SPEAKER.PORT)
    logger.info("SPEAKER COMMAND TIME OUT TOLERANCE: %s", config.SPEAKER.COMMAND.TIME_OUT_TOLERANCE)