# -*- encoding:utf-8 -*-
"""
增强脚本执行器

负责执行包含图像识别、条件等待等高级功能的脚本
"""
import os
import time
import random
import json5
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum, auto
from loguru import logger

from .detector import ImageDetector


class StepType(Enum):
    """增强脚本步骤类型"""
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    MOUSE_MOVE = auto()
    MOUSE_CLICK = auto()
    MOUSE_DOUBLE_CLICK = auto()
    MOUSE_DRAG = auto()  # 鼠标拖拽/滑动
    MOUSE_SCROLL = auto()  # 鼠标滚轮滚动
    WAIT_FOR_IMAGE = auto()
    WAIT_FOR_ANY_IMAGE = auto()
    WAIT_FOR_ALL_IMAGES = auto()
    FIND_AND_CLICK = auto()
    FIND_AND_CLICK_ANY = auto()
    FIND_AND_CLICK_DYNAMIC = auto()  # 动态构建图片路径并点击
    EXECUTE_SCRIPT = auto()
    WAIT = auto()
    LOG = auto()
    IF = auto()
    IF_ELSE = auto()
    SET_VAR = auto()


@dataclass
class EnhancedStep:
    """增强脚本的单个步骤"""
    type: StepType
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedScript:
    """增强脚本"""
    version: str = '1.0'
    name: str = ''
    steps: List[EnhancedStep] = field(default_factory=list)
    description: str = ''
    meta: Dict[str, Any] = field(default_factory=dict)


class EnhancedScriptExecutor:
    """
    增强脚本执行器
    
    负责执行包含图像识别、条件等待等高级功能的脚本
    """
    
    def __init__(
        self,
        detector: ImageDetector,
        action_executor,
        script_executor,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        初始化增强脚本执行器
        
        :param detector: 图像检测器
        :param action_executor: 动作执行器
        :param script_executor: 脚本执行器
        :param log_callback: 日志回调函数
        """
        self.detector = detector
        self.action_executor = action_executor
        self.script_executor = script_executor
        self.log_callback = log_callback
        
        self._context: Dict[str, str] = {}
        self._running = False
        self._stopped = False
    
    def log(self, message: str):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            logger.info(message)
    
    def set_context(self, context: Dict[str, str]):
        """
        设置上下文变量（用于变量替换）
        
        :param context: 变量字典，例如 {'buy_city': '圣多明各', 'sell_sea': '加勒比'}
        """
        self._context = context.copy()
        self.log(f'[增强脚本] 上下文已设置: {self._context}')
    
    def _replace_variables(self, text: str) -> str:
        """
        替换字符串中的变量
        
        :param text: 包含变量的字符串，例如 "imgsE/${buy_city}.png"
        :return: 替换后的字符串
        """
        if not text or not isinstance(text, str):
            return text
        
        result = text
        for key, value in self._context.items():
            var_pattern = f'${{{key}}}'
            if var_pattern in result:
                result = result.replace(var_pattern, value)
                self.log(f'[增强脚本] 变量替换: {var_pattern} -> {value}')
        
        return result
    
    def _replace_params_variables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归替换参数字典中的变量
        
        :param params: 参数字典
        :return: 替换后的参数字典
        """
        if not params:
            return params
        
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                result[key] = self._replace_variables(value)
            elif isinstance(value, dict):
                result[key] = self._replace_params_variables(value)
            elif isinstance(value, list):
                # 处理列表中的每一项
                replaced_list = []
                for item in value:
                    if isinstance(item, str):
                        replaced_list.append(self._replace_variables(item))
                    elif isinstance(item, dict):
                        # 如果是字典，递归处理（可能是嵌套步骤的 params）
                        replaced_list.append(self._replace_params_variables(item))
                    elif isinstance(item, EnhancedStep):
                        # 如果是步骤对象，创建新的步骤对象并替换参数
                        replaced_params = self._replace_params_variables(item.params)
                        replaced_list.append(EnhancedStep(type=item.type, params=replaced_params))
                    else:
                        replaced_list.append(item)
                result[key] = replaced_list
            else:
                result[key] = value
        
        return result
    
    def stop(self):
        """停止执行"""
        self._stopped = True
        self._running = False
    
    def is_running(self) -> bool:
        """是否正在执行"""
        return self._running
    
    def load_from_file(self, file_path: str) -> Optional[EnhancedScript]:
        """
        从文件加载增强脚本
        
        :param file_path: 脚本文件路径
        :return: 增强脚本对象或 None
        """
        if not os.path.isfile(file_path):
            self.log(f'[增强脚本] 文件不存在: {file_path}')
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json5.load(f)
        except Exception as e:
            self.log(f'[增强脚本] 解析文件失败: {e}')
            return None
        
        try:
            # 检查是否是旧格式（scripts 数组）
            if 'scripts' in data and 'steps' not in data:
                data = self._convert_old_format(data)
            
            # 验证脚本格式
            if 'steps' not in data:
                self.log('[增强脚本] 脚本格式验证失败:')
                self.log('  - 缺少 steps 字段')
                
                # 尝试自动修复
                if 'name' not in data:
                    self.log('  [修复] 已添加默认名称')
                    data['name'] = os.path.splitext(os.path.basename(file_path))[0]
                if 'version' not in data:
                    self.log('  [修复] 已添加默认版本号: 1.0')
                    data['version'] = '1.0'
                if 'steps' not in data:
                    self.log('  [修复] 已添加空 steps 数组')
                    data['steps'] = []
                
                # 如果 steps 为空，尝试自动修复
                if not data['steps']:
                    self.log('[增强脚本] 尝试自动修复...')
                    data = self._auto_fix_script(data)
            
            self.log('[增强脚本] 加载成功: {} (v{}), 共 {} 步'.format(
                data.get('name', ''),
                data.get('version', '1.0'),
                len(data.get('steps', []))
            ))
            
            return EnhancedScript(
                version=data.get('version', '1.0'),
                name=data.get('name', ''),
                steps=[self._parse_step(step_data) for step_data in data.get('steps', [])],
                description=data.get('description', ''),
                meta=data.get('meta', {}),
            )
        except Exception as e:
            self.log(f'[增强脚本] 加载失败: {e}')
            return None
    
    def _convert_old_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将旧格式脚本转换为新格式
        
        旧格式示例:
        {
            "scripts": [
                {"type": "mouse_click", "x": 100, "y": 200}
            ]
        }
        
        新格式示例:
        {
            "steps": [
                {"type": "mouse_click", "params": {"x": 100, "y": 200}}
            ]
        }
        """
        if 'scripts' not in data:
            return data
        
        scripts = data.pop('scripts')
        steps = []
        
        for event in scripts:
            step = self._convert_event_to_step(event)
            if step:
                steps.append(step)
        
        data['steps'] = steps
        return data
    
    def _convert_event_to_step(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        将旧格式事件转换为新格式步骤
        """
        event_type = event.get('type', '')
        params = {}
        
        if event_type == 'EM':
            params['x'] = event.get('x', 0)
            params['y'] = event.get('y', 0)
            return {'type': 'mouse_move', 'params': params}
        elif event_type == 'EC':
            params['x'] = event.get('x', 0)
            params['y'] = event.get('y', 0)
            return {'type': 'mouse_click', 'params': params}
        elif event_type == 'ED':
            params['x'] = event.get('x', 0)
            params['y'] = event.get('y', 0)
            return {'type': 'mouse_double_click', 'params': params}
        elif event_type == 'EK':
            params['key'] = event.get('key', '')
            return {'type': 'key_press', 'params': params}
        elif event_type == 'WAIT':
            params['duration'] = event.get('delay', 1.0)
            return {'type': 'wait', 'params': params}
        
        return None
    
    def _auto_fix_script(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动修复脚本格式
        """
        # 如果有 scripts 字段但没有 steps 字段，尝试转换
        if 'scripts' in data and 'steps' not in data:
            data = self._convert_old_format(data)
        
        # 如果还是没有 steps，尝试从其他字段推断
        if 'steps' not in data or not data['steps']:
            steps = []
            
            # 尝试从 script 字段推断
            if 'script' in data:
                script_data = data['script']
                if isinstance(script_data, list):
                    for event in script_data:
                        step = self._convert_event_to_step(event)
                        if step:
                            steps.append(step)
                data['steps'] = steps
            
            # 尝试从 events 字段推断
            elif 'events' in data:
                events_data = data['events']
                if isinstance(events_data, list):
                    for event in events_data:
                        step = self._convert_event_to_step(event)
                        if step:
                            steps.append(step)
                data['steps'] = steps
        
        return data
    
    def _parse_step(self, step_data: Dict[str, Any]) -> EnhancedStep:
        """
        解析单个步骤
        
        :param step_data: 步骤数据
        :return: 步骤对象
        """
        step_type_str = step_data.get('type', '').upper()
        
        type_map = {
            'KEY_PRESS': StepType.KEY_PRESS,
            'KEY_RELEASE': StepType.KEY_RELEASE,
            'MOUSE_MOVE': StepType.MOUSE_MOVE,
            'MOUSE_CLICK': StepType.MOUSE_CLICK,
            'MOUSE_DOUBLE_CLICK': StepType.MOUSE_DOUBLE_CLICK,
            'MOUSE_DRAG': StepType.MOUSE_DRAG,
            'MOUSE_SCROLL': StepType.MOUSE_SCROLL,
            'WAIT_FOR_IMAGE': StepType.WAIT_FOR_IMAGE,
            'WAIT_FOR_ANY_IMAGE': StepType.WAIT_FOR_ANY_IMAGE,
            'WAIT_FOR_ALL_IMAGES': StepType.WAIT_FOR_ALL_IMAGES,
            'FIND_AND_CLICK': StepType.FIND_AND_CLICK,
            'FIND_AND_CLICK_ANY': StepType.FIND_AND_CLICK_ANY,
            'FIND_AND_CLICK_DYNAMIC': StepType.FIND_AND_CLICK_DYNAMIC,
            'EXECUTE_SCRIPT': StepType.EXECUTE_SCRIPT,
            'WAIT': StepType.WAIT,
            'LOG': StepType.LOG,
            'IF': StepType.IF,
            'IF_ELSE': StepType.IF_ELSE,
            'SET_VAR': StepType.SET_VAR,
        }
        
        step_type = type_map.get(step_type_str)
        if step_type is None:
            self.log(f'[增强脚本] 未知的步骤类型: {step_type_str}')
            step_type = StepType.WAIT
        
        params = step_data.get('params', {})
        
        return EnhancedStep(type=step_type, params=params)
    
    def execute(self, script: EnhancedScript) -> bool:
        """
        执行增强脚本
        
        :param script: 增强脚本对象
        :return: 是否执行成功
        """
        if not script or not script.steps:
            self.log('[增强脚本] 脚本为空')
            return False
        
        self._running = True
        self._stopped = False
        
        self.log(f'[增强脚本] 开始执行: {script.name}')
        if self._context:
            self.log(f'[增强脚本] 上下文变量: {self._context}')
        
        for i, step in enumerate(script.steps):
            if self._stopped:
                self.log('[增强脚本] 执行被中断')
                self._running = False
                return False
            
            step_num = i + 1
            self.log(f'[增强脚本] 执行第 {step_num}/{len(script.steps)} 步: {step.type.name}')
            
            try:
                # 替换步骤参数中的变量
                replaced_params = self._replace_params_variables(step.params)
                # 创建替换后的步骤
                replaced_step = EnhancedStep(type=step.type, params=replaced_params)
                
                success = self._execute_step(replaced_step)
                # 记录上一步的执行结果到上下文
                self._context['last_step_success'] = success
                
                if not success:
                    self.log(f'[增强脚本] 第 {step_num} 步执行失败')
                    self._running = False
                    return False
            except Exception as e:
                self.log(f'[增强脚本] 第 {step_num} 步执行出错: {e}')
                logger.exception(f'Error executing step {step_num}')
                self._context['last_step_success'] = False
                self._running = False
                return False
        
        self.log(f'[增强脚本] 执行完成: {script.name}')
        self._running = False
        return True
    
    def _execute_steps(self, steps: List) -> bool:
        """
        执行一系列步骤
        
        :param steps: 步骤列表（可以是 EnhancedStep 对象或字典）
        :return: 是否全部执行成功
        """
        for i, step in enumerate(steps):
            if self._stopped:
                return False
            
            try:
                # 支持字典和 EnhancedStep 两种格式
                if isinstance(step, dict):
                    # 将字典转换为 EnhancedStep
                    step_obj = self._parse_step(step)
                else:
                    step_obj = step
                
                success = self._execute_step(step_obj)
                if not success:
                    self.log(f'[增强脚本] 嵌套步骤第 {i+1} 步执行失败')
                    return False
            except Exception as e:
                self.log(f'[增强脚本] 嵌套步骤第 {i+1} 步执行出错: {e}')
                logger.exception(f'Error executing nested step {i+1}')
                return False
        
        return True
    
    def _evaluate_condition(self, condition: str) -> bool:
        """
        评估条件表达式
        
        :param condition: 条件表达式，例如 "city_selection_mode == 'specified'"
        :return: 条件是否成立
        """
        try:
            # 简单的变量比较支持
            # 格式: "变量名 == 值" 或 "变量名 != 值"
            condition = condition.strip()
            
            # 处理等于
            if '==' in condition:
                parts = condition.split('==', 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    expected_value_str = parts[1].strip().strip('\'"')
                    actual_value = self._context.get(var_name, '')
                    
                    # 智能类型转换比较
                    if isinstance(actual_value, bool):
                        # 布尔值比较
                        expected_value_lower = expected_value_str.lower()
                        expected_bool = expected_value_lower in ('true', '1', 'yes')
                        result = actual_value == expected_bool
                        self.log(f'[增强脚本] 条件: {var_name} == "{expected_value_str}" -> {actual_value} (bool) == {expected_bool} = {result}')
                        return result
                    else:
                        # 普通字符串比较
                        result = str(actual_value) == expected_value_str
                        self.log(f'[增强脚本] 条件: {var_name} == "{expected_value_str}" -> {actual_value} == "{expected_value_str}" = {result}')
                        return result
            
            # 处理不等于
            elif '!=' in condition:
                parts = condition.split('!=', 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    expected_value_str = parts[1].strip().strip('\'"')
                    actual_value = self._context.get(var_name, '')
                    
                    # 智能类型转换比较
                    if isinstance(actual_value, bool):
                        # 布尔值比较
                        expected_value_lower = expected_value_str.lower()
                        expected_bool = expected_value_lower in ('true', '1', 'yes')
                        result = actual_value != expected_bool
                        self.log(f'[增强脚本] 条件: {var_name} != "{expected_value_str}" -> {actual_value} (bool) != {expected_bool} = {result}')
                        return result
                    else:
                        # 普通字符串比较
                        result = str(actual_value) != expected_value_str
                        self.log(f'[增强脚本] 条件: {var_name} != "{expected_value_str}" -> {actual_value} != "{expected_value_str}" = {result}')
                        return result
            
            self.log(f'[增强脚本] 无法解析条件: {condition}')
            return False
            
        except Exception as e:
            self.log(f'[增强脚本] 条件评估出错: {e}')
            logger.exception('Error evaluating condition')
            return False
    
    def _execute_step(self, step: EnhancedStep) -> bool:
        """
        执行单个步骤
        
        :param step: 步骤对象
        :return: 是否执行成功
        """
        params = step.params
        
        if step.type == StepType.KEY_PRESS:
            key = params.get('key', '')
            return self.action_executor.press_key(key)
        
        elif step.type == StepType.KEY_RELEASE:
            key = params.get('key', '')
            return self.action_executor.release_key(key)
        
        elif step.type == StepType.MOUSE_MOVE:
            x = params.get('x', 0)
            y = params.get('y', 0)
            coordinate_type = params.get('coordinate_type', 'relative_to_window')
            return self.action_executor.move_mouse_to(x, y, coordinate_type)
        
        elif step.type == StepType.MOUSE_CLICK:
            x = params.get('x', 0)
            y = params.get('y', 0)
            button = params.get('button', 'left')
            coordinate_type = params.get('coordinate_type', 'relative_to_window')
            return self.action_executor.click_at(x, y, button, coordinate_type)
        
        elif step.type == StepType.MOUSE_DOUBLE_CLICK:
            x = params.get('x', 0)
            y = params.get('y', 0)
            return self.action_executor.double_click_at(x, y)
        
        elif step.type == StepType.MOUSE_DRAG:
            return self._mouse_drag(params)
        
        elif step.type == StepType.MOUSE_SCROLL:
            return self._mouse_scroll(params)
        
        elif step.type == StepType.WAIT_FOR_IMAGE:
            return self._wait_for_image(params)
        
        elif step.type == StepType.WAIT_FOR_ANY_IMAGE:
            return self._wait_for_any_image(params)
        
        elif step.type == StepType.WAIT_FOR_ALL_IMAGES:
            return self._wait_for_all_images(params)
        
        elif step.type == StepType.FIND_AND_CLICK:
            return self._find_and_click(params)
        
        elif step.type == StepType.FIND_AND_CLICK_ANY:
            return self._find_and_click_any(params)
        
        elif step.type == StepType.FIND_AND_CLICK_DYNAMIC:
            return self._find_and_click_dynamic(params)
        
        elif step.type == StepType.EXECUTE_SCRIPT:
            return self._execute_external_script(params)
        
        elif step.type == StepType.WAIT:
            # 支持固定等待或随机等待
            duration = params.get('duration', None)
            duration_min = params.get('duration_min', None)
            duration_max = params.get('duration_max', None)
            
            if duration is not None:
                # 固定等待时间
                wait_time = duration
            elif duration_min is not None and duration_max is not None:
                # 随机等待时间
                wait_time = random.uniform(duration_min, duration_max)
                self.log(f'[增强脚本] 随机等待: {wait_time:.2f}秒 (范围: {duration_min}-{duration_max}秒)')
            else:
                # 默认等待1秒
                wait_time = 1.0
            
            # 可中断的等待
            start_time = time.time()
            while time.time() - start_time < wait_time:
                if self._stopped:
                    return False
                time.sleep(0.1)  # 每100ms检查一次停止标志
            return True
        
        elif step.type == StepType.LOG:
            message = params.get('message', '')
            message = self._replace_variables(message)
            self.log(f'[增强脚本] {message}')
            return True
        
        elif step.type == StepType.IF:
            condition = params.get('condition', '')
            steps = params.get('steps', [])
            if self._evaluate_condition(condition):
                self.log(f'[增强脚本] 条件成立， 执行IF分支')
                return self._execute_steps(steps)
            else:
                self.log(f'[增强脚本] 条件不成立, 跳过IF分支')
                return True
        
        elif step.type == StepType.IF_ELSE:
            condition = params.get('condition', '')
            steps = params.get('steps', [])
            else_steps = params.get('else_steps', [])
            if self._evaluate_condition(condition):
                self.log(f'[增强脚本] 条件成立，执行IF分支')
                return self._execute_steps(steps)
            else:
                self.log(f'[增强脚本] 条件不成立，执行ELSE分支')
                return self._execute_steps(else_steps)
        
        elif step.type == StepType.SET_VAR:
            var_name = params.get('name', '')
            var_value = params.get('value', '')
            if var_name:
                self._context[var_name] = var_value
                self.log(f'[增强脚本] 设置变量: {var_name} = "{var_value}"')
            return True
        
        return False
    
    def _wait_for_image(self, params: Dict[str, Any]) -> bool:
        """
        等待图像出现
        
        参数:
        - image: 图像路径
        - timeout: 超时时间（秒），默认10秒
        - interval: 检测间隔（秒），默认0.5秒
        - set_var: 可选，检测结果存入变量名
        - value_on_found: 检测到图片时的变量值，默认"true"
        - value_on_timeout: 超时时的变量值，默认"false"
        - log_on_timeout: 超时时是否输出日志，默认true
        """
        image_path = params.get('image', '')
        timeout = params.get('timeout', 10.0)
        interval = params.get('interval', 0.5)
        set_var = params.get('set_var', '')
        value_on_found = params.get('value_on_found', 'true')
        value_on_timeout = params.get('value_on_timeout', 'false')
        log_on_timeout = params.get('log_on_timeout', True)
        
        if not image_path:
            self.log('[增强脚本] wait_for_image: 缺少图像路径')
            if set_var:
                self._context[set_var] = value_on_timeout
            return False
        
        # 解析路径（相对路径转为绝对路径）
        image_path = self._resolve_image_path(image_path)
        
        if not os.path.isfile(image_path):
            self.log(f'[增强脚本] wait_for_image: 图像文件不存在: {_convert_pinyin_to_chinese(image_path)}')
            if set_var:
                self._context[set_var] = value_on_timeout
            return False
        
        self.log(f'[增强脚本] 等待图像出现: {os.path.basename(_convert_pinyin_to_chinese(image_path))} (超时: {timeout}秒)')
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stopped:
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(interval)
                continue
            
            try:
                pos = self.detector.detect_single(
                    image_path,
                    screenshot,
                    capture_offset,
                )
                if pos is not None:
                    self.log(f'[增强脚本] 图像出现: {os.path.basename(_convert_pinyin_to_chinese(image_path))}')
                    if set_var:
                        self._context[set_var] = value_on_found
                        self.log(f'[增强脚本] 设置变量: {set_var} = "{value_on_found}"')
                    return True
            except Exception as e:
                self.log(f'[增强脚本] 检测图像出错: {e}')
            
            time.sleep(interval)
        
        if log_on_timeout:
            self.log(f'[增强脚本] 等待图像超时: {os.path.basename(_convert_pinyin_to_chinese(image_path))}')
        if set_var:
            self._context[set_var] = value_on_timeout
            self.log(f'[增强脚本] 设置变量: {set_var} = "{value_on_timeout}"')
        return False
    
    def _resolve_image_path(self, image_path: str) -> str:
        """
        解析图像路径，将相对路径转换为绝对路径
        
        :param image_path: 图像路径（相对或绝对）
        :return: 绝对路径
        """
        if not image_path:
            return image_path
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(image_path):
            return image_path
        
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 尝试在项目根目录下查找
        abs_path = os.path.join(root_dir, image_path)
        self.log(f'[增强脚本] 路径解析: {image_path} -> {abs_path}')
        if os.path.isfile(abs_path):
            self.log(f'[增强脚本] 路径解析成功: {abs_path}')
            return abs_path
        
        # 如果找不到，返回原路径（让后续处理报错）
        self.log(f'[增强脚本] 路径解析失败，文件不存在: {abs_path}')
        return image_path

    def _find_and_click(self, params: Dict[str, Any]) -> bool:
        """
        找到图像并点击
        
        参数:
        - image: 图像路径
        - timeout: 超时时间（秒），默认10秒
        - interval: 检测间隔（秒），默认0.5秒
        - click_count: 点击次数，默认1次
        - click_interval: 多次点击之间的间隔（秒），默认0.2秒
        - region: 可选，检测区域 (left, top, width, height)
        - retry_count: 重试次数，默认0次（失败后重试几次）
        - retry_scroll: 重试前是否滚动，默认False
        - scroll_params: 滚动参数，默认None
        - use_hash_verify: 是否使用哈希验证，默认True
        """
        image_path = params.get('image', '')
        timeout = params.get('timeout', 10.0)
        interval = params.get('interval', 0.5)
        click_count = params.get('click_count', 1)
        click_interval = params.get('click_interval', 0.2)
        region = params.get('region', None)
        retry_count = params.get('retry_count', 0)
        retry_scroll = params.get('retry_scroll', False)
        scroll_params = params.get('scroll_params', None)
        use_hash_verify = params.get('use_hash_verify', True)
        
        if not image_path:
            self.log('[增强脚本] find_and_click: 缺少图像路径')
            return False
        
        # 解析路径（相对路径转为绝对路径）
        image_path = self._resolve_image_path(image_path)
        
        if not os.path.isfile(image_path):
            self.log(f'[增强脚本] find_and_click: 图像文件不存在: {_convert_pinyin_to_chinese(image_path)}')
            return False
        
        self.log(f'[增强脚本] 查找并点击: {os.path.basename(_convert_pinyin_to_chinese(image_path))}')
        self.log(f'[增强脚本] 参数: timeout={timeout}, interval={interval}, retry_count={retry_count}, retry_scroll={retry_scroll}')
        if region:
            self.log(f'[增强脚本] 检测区域: {region}')
        if scroll_params:
            self.log(f'[增强脚本] 滚动参数: {scroll_params}')
        
        # 内部辅助函数：执行一次查找尝试
        def try_find_and_click(do_scroll: bool = False) -> Optional[bool]:
            """
            执行一次查找尝试
            
            :param do_scroll: 是否先滚动再查找
            :return: True=成功找到并点击，False=失败，None=超时需要重试
            """
            if do_scroll:
                self.log('[增强脚本] 执行鼠标滚轮下滚脚本...')
                # 使用录制好的鼠标滚轮下滚脚本
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                scroll_script_path = os.path.join(base_dir, 'system_scripts', '鼠标滚轮下滚.json5')
                if os.path.isfile(scroll_script_path) and self.script_executor:
                    self.log(f'[增强脚本] 执行滚轮脚本: {os.path.basename(scroll_script_path)}')
                    self.script_executor.execute(scroll_script_path, wait=True)
                    self.log('[增强脚本] 滚轮脚本执行完成')
                    time.sleep(0.5)
                else:
                    self.log(f'[增强脚本] 滚轮脚本不存在或脚本执行器未初始化: {scroll_script_path}')
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self._stopped:
                    return False
                
                screenshot, capture_offset = self.detector.take_screenshot()
                if screenshot is None:
                    time.sleep(interval)
                    continue
                
                try:
                    pos = self.detector.detect_single(
                        image_path,
                        screenshot,
                        capture_offset,
                        region=region,
                        use_hash_verify=use_hash_verify,
                    )
                    
                    if pos is not None:
                        # 找到图像，执行点击
                        if len(pos) == 3:
                            x, y, confidence = pos
                        else:
                            x, y = pos
                        self.log(f'[增强脚本] 找到图像，点击位置: ({x}, {y})')
                        
                        for i in range(click_count):
                            if i > 0:
                                time.sleep(click_interval)
                            self.action_executor.click_at(x, y)
                        
                        return True
                        
                except Exception as e:
                    self.log(f'[增强脚本] 检测图像时出错: {e}')
                
                time.sleep(interval)
            
            return None  # 超时
        
        # 第一次尝试（不滚动）
        result = try_find_and_click(do_scroll=False)
        if result is not None:
            return result
        
        self.log(f'[增强脚本] 第一次查找超时，执行滚动后再次查找...')
        
        # 第二次尝试（滚动后查找）
        result = try_find_and_click(do_scroll=True)
        if result is not None:
            return result
        
        self.log(f'[增强脚本] 查找图像超时: {os.path.basename(_convert_pinyin_to_chinese(image_path))}')
        return False
    
    def _get_all_images_in_folder(self, folder_path: str) -> List[str]:
        """
        获取文件夹下所有图片路径
        
        :param folder_path: 文件夹路径（支持相对路径）
        :return: 图片路径列表
        """
        result = []
        if not folder_path:
            return result
        
        # 处理相对路径，假设相对于项目根目录
        if not os.path.isabs(folder_path):
            # 获取项目根目录
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            folder_path = os.path.join(root_dir, folder_path)
        
        if not os.path.isdir(folder_path):
            self.log(f'[增强脚本] 文件夹不存在: {folder_path}')
            return result
        
        for f in os.listdir(folder_path):
            f_path = os.path.join(folder_path, f)
            if os.path.isfile(f_path) and f.lower().endswith(('.png', '.jpg', '.jpeg')):
                result.append(f_path)
        
        return sorted(result)
    
    def _wait_for_any_image(self, params: Dict[str, Any]) -> bool:
        """
        等待任意一张图片出现
        
        参数:
        - folder: 文件夹路径
        - images: 图片路径列表（二选一）
        - timeout: 超时时间（秒），默认10秒
        - interval: 检测间隔（秒），默认0.5秒
        """
        folder = params.get('folder', '')
        images = params.get('images', [])
        timeout = params.get('timeout', 10.0)
        interval = params.get('interval', 0.5)
        
        image_paths = []
        if folder:
            image_paths = self._get_all_images_in_folder(folder)
        elif images:
            image_paths = images
        
        if not image_paths:
            self.log('[增强脚本] wait_for_any_image: 没有指定图片')
            return False
        
        self.log(f'[增强脚本] 等待任意图片出现，共 {len(image_paths)} 张 (超时: {timeout}秒)')
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stopped:
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(interval)
                continue
            
            try:
                for img_path in image_paths:
                    try:
                        pos = self.detector.detect_single(
                            img_path,
                            screenshot,
                            capture_offset,
                        )
                        if pos is not None:
                            self.log(f'[增强脚本] 图片出现: {os.path.basename(_convert_pinyin_to_chinese(img_path))}')
                            return True
                    except Exception:
                        pass
            except Exception as e:
                self.log(f'[增强脚本] 检测图片出错: {e}')
            
            time.sleep(interval)
        
        self.log('[增强脚本] 等待任意图片超时')
        return False
    
    def _wait_for_all_images(self, params: Dict[str, Any]) -> bool:
        """
        等待所有指定图片同时出现
        
        参数:
        - images: 图片路径列表
        - timeout: 超时时间（秒），默认10秒
        - interval: 检测间隔（秒），默认0.5秒
        """
        images = params.get('images', [])
        timeout = params.get('timeout', 10.0)
        interval = params.get('interval', 0.5)
        
        if not images:
            self.log('[增强脚本] wait_for_all_images: 没有指定图片')
            return False
        
        # 检查所有图片是否存在（解析相对路径）
        valid_images = []
        for img_path in images:
            # 解析路径（相对路径转为绝对路径）
            resolved_path = self._resolve_image_path(img_path)
            if os.path.isfile(resolved_path):
                valid_images.append(resolved_path)
            else:
                self.log(f'[增强脚本] wait_for_all_images: 图像文件不存在: {_convert_pinyin_to_chinese(img_path)}')
        
        if not valid_images:
            self.log('[增强脚本] wait_for_all_images: 没有有效的图片')
            return False
        
        self.log(f'[增强脚本] 等待所有图片同时出现，共 {len(valid_images)} 张 (超时: {timeout}秒)')
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stopped:
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(interval)
                continue
            
            found_all = True
            found_images = []
            
            try:
                for img_path in valid_images:
                    pos = self.detector.detect_single(
                        img_path,
                        screenshot,
                        capture_offset,
                    )
                    if pos is None:
                        found_all = False
                        break
                    found_images.append((img_path, pos))
            except Exception as e:
                self.log(f'[增强脚本] 检测图片出错: {e}')
                found_all = False
            
            if found_all:
                self.log(f'[增强脚本] 所有图片同时出现，共 {len(found_images)} 张')
                return True
            
            time.sleep(interval)
        
        self.log('[增强脚本] 等待所有图片同时出现超时')
        return False
    
    def _find_and_click_any(self, params: Dict[str, Any]) -> bool:
        """
        找到任意一张图片并点击
        
        参数:
        - folder: 文件夹路径
        - images: 图片路径列表（二选一）
        - timeout: 超时时间（秒），默认10秒
        - interval: 检测间隔（秒），默认0.5秒
        - click_count: 点击次数，默认1次
        - click_interval: 多次点击之间的间隔（秒），默认0.2秒
        """
        folder = params.get('folder', '')
        images = params.get('images', [])
        timeout = params.get('timeout', 10.0)
        interval = params.get('interval', 0.5)
        click_count = params.get('click_count', 1)
        click_interval = params.get('click_interval', 0.2)
        
        image_paths = []
        if folder:
            image_paths = self._get_all_images_in_folder(folder)
        elif images:
            image_paths = images
        
        if not image_paths:
            self.log('[增强脚本] find_and_click_any: 没有指定图片')
            return False
        
        self.log(f'[增强脚本] 查找并点击任意图片，共 {len(image_paths)} 张')
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self._stopped:
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(interval)
                continue
            
            try:
                for img_path in image_paths:
                    try:
                        pos = self.detector.detect_single(
                            img_path,
                            screenshot,
                            capture_offset,
                        )
                        if pos is not None:
                            self.log(f'[增强脚本] 找到图片，点击 {click_count} 次: {os.path.basename(_convert_pinyin_to_chinese(img_path))}')
                            
                            for i in range(click_count):
                                if self._stopped:
                                    return False
                                
                                self.action_executor.click_at(pos[0], pos[1])
                                
                                if i < click_count - 1:
                                    time.sleep(click_interval)
                            
                            return True
                    except Exception:
                        pass
            except Exception as e:
                self.log(f'[增强脚本] 检测图片出错: {e}')
            
            time.sleep(interval)
        
        self.log('[增强脚本] 查找任意图片超时')
        return False
    
    def _execute_external_script(self, params: Dict[str, Any]) -> bool:
        """
        执行外部脚本
        
        参数:
        - path: 脚本路径
        - wait: 是否等待执行完成，默认True
        - context: 可选，向脚本传递的上下文变量字典
        """
        script_path = params.get('path', '')
        wait = params.get('wait', True)
        context = params.get('context', {})
        
        if not script_path:
            self.log('[增强脚本] execute_script: 缺少脚本路径')
            return False
        
        if not os.path.isfile(script_path):
            self.log(f'[增强脚本] execute_script: 脚本文件不存在: {script_path}')
            return False
        
        self.log(f'[增强脚本] 执行外部脚本: {os.path.basename(script_path)}')
        
        # 如果是增强脚本（.json5），先加载并设置context
        if script_path.lower().endswith('.json5'):
            script = self.load_from_file(script_path)
            if not script:
                return False
            
            # 如果有传入context，先保存当前context，执行完后恢复
            old_context = self._context.copy()
            
            # 合并新的context（新context优先级更高）
            if context:
                merged_context = old_context.copy()
                for k, v in context.items():
                    # 对context里的变量也进行变量替换
                    if isinstance(v, str):
                        v = self._replace_variables(v)
                    merged_context[k] = v
                self._context = merged_context
                self.log(f'[增强脚本] 合并上下文: {self._context}')
            
            try:
                result = self.execute(script)
                return result
            finally:
                # 恢复原context
                self._context = old_context
                self.log(f'[增强脚本] 上下文已恢复')
        
        # 否则使用默认的脚本执行器
        return self.script_executor.execute(script_path, wait=wait)

    def _mouse_drag(self, params: Dict[str, Any]) -> bool:
        """
        鼠标拖拽/滑动操作
        
        参数:
        - start_x: 起始X坐标
        - start_y: 起始Y坐标
        - end_x: 结束X坐标
        - end_y: 结束Y坐标
        - duration: 滑动持续时间（秒），默认0.5秒
        - button: 鼠标按钮，默认'left'
        - steps: 滑动步数，默认20步（步数越多轨迹越平滑）
        """
        start_x = params.get('start_x', 0)
        start_y = params.get('start_y', 0)
        end_x = params.get('end_x', 0)
        end_y = params.get('end_y', 0)
        duration = params.get('duration', 0.5)
        button = params.get('button', 'left')
        steps = params.get('steps', 20)
        
        self.log(f'[增强脚本] 鼠标拖拽: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 持续{duration}秒')
        
        try:
            # 使用 action_executor 的 drag 方法
            return self.action_executor.drag(
                start_x, start_y,
                end_x, end_y,
                duration=duration,
                button=button,
                steps=steps
            )
        except Exception as e:
            self.log(f'[增强脚本] 鼠标拖拽失败: {e}')
            return False

    def _mouse_scroll(self, params: Dict[str, Any]) -> bool:
        """
        鼠标滚轮滚动操作
        
        参数:
        - x: 鼠标X坐标（滚动前移动到的位置）
        - y: 鼠标Y坐标（滚动前移动到的位置）
        - scroll_amount: 滚动量，正数向上滚动，负数向下滚动
        - scroll_times: 滚动次数，默认1次
        """
        x = params.get('x', 0)
        y = params.get('y', 0)
        scroll_amount = params.get('scroll_amount', -3)  # 默认向下滚动3个单位
        scroll_times = params.get('scroll_times', 1)
        
        self.log(f'[增强脚本] 鼠标滚轮滚动: 位置({x}, {y}), 滚动量{scroll_amount}, 次数{scroll_times}')
        
        try:
            # 使用 action_executor 的 scroll 方法
            success = self.action_executor.scroll(
                x, y,
                scroll_amount=scroll_amount,
                scroll_times=scroll_times
            )
            # 检查是否已停止
            if self._stopped:
                self.log('[增强脚本] 鼠标滚轮滚动时检测到停止信号')
                return False
            return success
        except Exception as e:
            self.log(f'[增强脚本] 鼠标滚轮滚动失败: {e}')
            return False

    def _find_and_click_dynamic(self, params: Dict[str, Any]) -> bool:
        """
        动态构建图片路径并点击
        
        参数:
        - base_path: 基础路径（如 'imgsE' 或 'imgsF'）
        - folder_var: 文件夹名变量（从上下文中获取）
        - image_var: 图片名变量（从上下文中获取，可选）
        - timeout: 超时时间（秒），默认5秒
        - interval: 检测间隔（秒），默认0.5秒
        """
        base_path = params.get('base_path', '')
        folder_var = params.get('folder_var', '')
        image_var = params.get('image_var', '')
        timeout = params.get('timeout', 5.0)
        interval = params.get('interval', 0.5)
        
        # 从上下文中获取变量值
        folder_name = self._context.get(folder_var, '')
        image_name = self._context.get(image_var, '') if image_var else folder_name
        
        if not folder_name:
            self.log(f'[增强脚本] FIND_AND_CLICK_DYNAMIC: 文件夹变量 {folder_var} 未设置')
            return False
        
        # 构建图片路径
        if base_path == 'imgsE':
            # imgsE 中的图片直接在根目录
            image_path = f'{base_path}/{folder_name}.png'
        elif base_path == 'imgsF':
            # imgsF 中的图片直接在根目录（不再有海域子文件夹）
            image_path = f'{base_path}/{image_name}.png'
        else:
            self.log(f'[增强脚本] FIND_AND_CLICK_DYNAMIC: 不支持的基础路径 {base_path}')
            return False
        
        self.log(f'[增强脚本] 动态路径: {image_path} (文件夹: {folder_name}, 图片: {image_name})')
        
        # 调用普通的 find_and_click，禁用哈希验证（文字类图片不适合哈希验证）
        return self._find_and_click({
            'image': image_path,
            'timeout': timeout,
            'interval': interval,
            'use_hash_verify': False,
        })


def _convert_pinyin_to_chinese(text: str) -> str:
    """
    将拼音转换为中文（用于日志显示）
    
    :param text: 包含拼音的文本
    :return: 转换后的文本
    """
    try:
        from .pinyin_converter import pinyin_to_chinese
        return pinyin_to_chinese(text)
    except Exception:
        return text
