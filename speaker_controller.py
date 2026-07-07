import re
import json
from typing import Union, List, Any, Dict
from python_postman import PythonPostman
from python_postman.execution import ExecutionContext
import time
import threading

from app_config import AppConfig


class SpeakerController:
    def __init__(self, config: AppConfig):
        self.ip_pat = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        self.spk_ip: str | None = None
        self.spk_cfg = config.SPEAKER
        self.cmd_cfg = self.spk_cfg.COMMAND

        # 配置完整性预校验
        self._validate_config()

        # 加载 Postman 集合文件
        try:
            self.collection = PythonPostman.from_file(self.cmd_cfg.POSTMAN_COLLECTION)
        except Exception as e:
            raise RuntimeError(f"加载Postman集合失败: {str(e)}") from e
        self.context = ExecutionContext()

        self.interval_update_lock = threading.Lock()
        self.passed_interval = 0

    def _validate_config(self) -> None:
        """提前校验必填配置字段，避免运行时报错定位困难"""
        required_spk = ["NAME_REGEX", "COMMAND"]
        for attr in required_spk:
            if not hasattr(self.spk_cfg, attr):
                raise ValueError(f"配置缺失: SPEAKER.{attr}")

        required_cmd = ["POSTMAN_COLLECTION", "POWER", "VOLUME"]
        for attr in required_cmd:
            if not hasattr(self.cmd_cfg, attr):
                raise ValueError(f"配置缺失: SPEAKER.COMMAND.{attr}")

    def is_IPv4(self, ip: str) -> bool:
        """校验IPv4地址格式与数值合法性（修复原字符串比较的类型错误）"""
        if not self.ip_pat.fullmatch(ip):
            return False
        octets = ip.split(".")
        for octet_str in octets:
            try:
                octet = int(octet_str)
            except ValueError:
                return False
            if octet < 0 or octet > 255:
                return False
        return True

    def set_ip(self, ip: str) -> None:
        """设置音箱IP，同步注入Postman上下文的 baseUrl 变量"""
        if not self.is_IPv4(ip):
            raise ValueError(f"无效IP地址格式: {ip}")
        self.spk_ip = ip
        # Postman集合中用 {{speakerIp}} 占位基础地址
        self.context.set_variable("speakerIp", self.spk_ip)

    @staticmethod
    def _extract_by_path(data: Any, path: str) -> Any:
        """
        按点分隔路径从JSON中提取值
        规则：
        - 字符串键必须用单引号包裹，如 'value' → 取 data["value"]
        - 数组索引必须是无引号的纯数字，如 0 → 取 data[0]
        - 不符合上述规则的格式会直接报错
        示例：
        "'value'.'i32_'" → data["value"]["i32_"]
        "0.'value'.'name'" → data[0]["value"]["name"]
        "value.'i32_'" → 报错（字符串键未加单引号）
        """
        keys = path.split(".")
        current = data
        for key in keys:
            try:
                # 情况1：首尾都是单引号 → 字符串键
                if key.startswith("'") and key.endswith("'"):
                    _key = key[1:-1]
                # 情况2：无引号的纯数字 → 数组索引
                elif key.isdigit():
                    _key = int(key)
                # 其他情况：格式错误，直接抛出
                else:
                    raise ValueError(
                        f"路径格式非法: 键 '{key}' 既不是单引号包裹的字符串键，也不是纯数字索引"
                    )
                
                current = current[_key]
            
            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(f"响应提取失败，路径: {path}，错误: {str(e)}") from e
        
        return current

    def _get_cmd_steps(self, cmd_node: Any) -> List[Any]:
        """自动收集 CMD1/CMD2... 并按数字升序排列，保证执行顺序"""
        steps = []
        for attr in dir(cmd_node):
            if attr.startswith("CMD") and attr[3:].isdigit():
                step_num = int(attr[3:])
                steps.append((step_num, getattr(cmd_node, attr)))
        steps.sort(key=lambda x: x[0])
        return [step[1] for step in steps]

    def _run_command(
            self, 
            cmd_node: Any, 
            params_val: List[Any] | None = None
        ) -> List[List[Any]]:
        """
        通用命令执行引擎
        :param cmd_node: 命令配置节点，如 self.cmd_cfg.POWER.ON
        :param params: 动态参数字典，键为变量名
        :return: 二维列表，外层对应CMD步骤，内层对应该步骤的响应提取结果
        """
        params_val = params_val or []
        all_results = []
        for step in self._get_cmd_steps(cmd_node):
            sleep_interval = self.cmd_cfg.EXECUTION_INTERVAL
            self.interval_update_lock.acquire()
            if self.passed_interval > 0:
                sleep_interval = 0
                self.passed_interval -= 1
            self.interval_update_lock.release()
            time.sleep(sleep_interval)
            req_name = step.NAME
            step_params = step.PARAMS if hasattr(step, "PARAMS") else []
            step_resp_paths = step.RESPONSE if hasattr(step, "RESPONSE") else []

            # 1. 注入当前步骤的变量到上下文
            for i, param_name in enumerate(step_params):
                if i >= len(params_val):
                    raise ValueError(f"请求 [{req_name}] 缺失必填参数: {param_name}")
                self.context.set_variable(param_name, str(params_val[i]))

            # 2. 从集合中取请求并执行
            try:
                request = self.collection.get_request_by_name(req_name)
            except Exception as e:
                raise RuntimeError(f"Postman集合未找到请求: {req_name}") from e

            try:
                response = request.execute_sync(context=self.context)
            except Exception as e:
                raise RuntimeError(f"执行请求 [{req_name}] 失败: {str(e)}") from e

            # 3. 按路径提取响应值
            step_results = []
            if step_resp_paths:
                try:
                    resp_data = response.response.json
                except json.JSONDecodeError as e:
                    raise ValueError(f"请求 [{req_name}] 响应非JSON格式: {str(e)}") from e

                for path in step_resp_paths:
                    step_results.append(self._extract_by_path(resp_data, path))

            all_results.append(step_results)

        return all_results

    # ------------------------------ 对外控制接口 ------------------------------
    def delete_interval(self, num_intervals:int):
        assert isinstance(num_intervals, int), "只能删除整数个执行间隔"
        assert num_intervals >=0, "不能删除负数个执行间隔"
        self.interval_update_lock.acquire()
        self.passed_interval += num_intervals
        self.interval_update_lock.release()

    def power_on(self) -> None:
        """音箱开机（切换到WiFi源唤醒）"""
        self._run_command(self.cmd_cfg.POWER.ON)

    def power_off(self) -> None:
        """音箱待机（进入低功耗模式）"""
        self._run_command(self.cmd_cfg.POWER.OFF)

    def get_volume(self) -> int:
        """读取当前音量 0~100"""
        results = self._run_command(self.cmd_cfg.VOLUME.GET)
        if not results or not results[0]:
            raise RuntimeError("获取音量失败，响应未提取到有效值")
        return int(results[0][0])

    def set_volume(self, vol: Union[int, float]) -> None:
        """设置音量，自动限幅 0~100"""
        vol = max(0, min(100, int(vol)))
        self._run_command(
            self.cmd_cfg.VOLUME.SET,
            params_val=[vol]
        )