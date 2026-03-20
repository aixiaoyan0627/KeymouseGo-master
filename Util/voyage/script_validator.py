# -*- encoding:utf-8 -*-
"""
增强脚本校验器
提供脚本格式验证，确保手写脚本的正确性
"""
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class ScriptValidationError(Exception):
    """脚本校验错误"""
    pass


class EnhancedScriptValidator:
    """增强脚本校验器"""
    
    # 支持的步骤类型
    VALID_STEP_TYPES = {
        'key_press',
        'key_release',
        'mouse_move',
        'mouse_click',
        'mouse_double_click',
        'wait_for_image',
        'wait_for_any_image',
        'wait_for_all_images',
        'find_and_click',
        'find_and_click_any',
        'execute_script',
        'wait',
        'log',
        'if',
        'if_else',
        'set_var',
    }
    
    # 各步骤类型的必填参数
    REQUIRED_PARAMS = {
        'key_press': ['key'],
        'key_release': ['key'],
        'mouse_move': ['x', 'y'],
        'mouse_click': ['x', 'y'],
        'mouse_double_click': ['x', 'y'],
        'wait_for_image': ['image'],
        'wait_for_any_image': [],  # 需要 folder 或 images
        'wait_for_all_images': ['images'],
        'find_and_click': ['image'],
        'find_and_click_any': [],  # 需要 folder 或 images
        'execute_script': ['path'],
        'wait': [],  # 可选
        'log': ['message'],
        'if': ['condition', 'steps'],
        'if_else': ['condition', 'steps', 'else_steps'],
        'set_var': ['name', 'value'],
    }
    
    # 参数类型验证
    PARAM_TYPES = {
        'key': str,
        'x': (int, float),
        'y': (int, float),
        'button': str,
        'image': str,
        'images': list,
        'folder': str,
        'timeout': (int, float),
        'interval': (int, float),
        'threshold': (int, float),
        'click_count': int,
        'click_interval': (int, float),
        'path': str,
        'wait': bool,
        'context': dict,
        'duration': (int, float),
        'message': str,
        'condition': str,
        'steps': list,
        'else_steps': list,
        'name': str,
        'value': (str, int, float, bool),
        'set_var': str,
        'value_on_found': (str, int, float, bool),
        'value_on_timeout': (str, int, float, bool),
        'log_on_timeout': bool,
    }
    
    @classmethod
    def validate_script(cls, script_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证脚本数据
        
        参数:
            script_data: 从 JSON5 加载的脚本数据
        
        返回:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 验证版本（可选，但推荐）
        if 'version' in script_data:
            if not isinstance(script_data['version'], str):
                errors.append('版本号必须是字符串类型')
        
        # 验证步骤
        if 'steps' not in script_data:
            errors.append('缺少 steps 字段')
        else:
            if not isinstance(script_data['steps'], list):
                errors.append('steps 必须是数组类型')
            else:
                for i, step in enumerate(script_data['steps']):
                    step_errors = cls.validate_step(step, i + 1)
                    errors.extend(step_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_step(cls, step: Dict[str, Any], step_num: int) -> List[str]:
        """
        验证单个步骤
        
        参数:
            step: 步骤数据
            step_num: 步骤编号（用于错误信息）
        
        返回:
            错误列表
        """
        errors = []
        
        # 验证 type 字段
        if 'type' not in step:
            errors.append(f'步骤 {step_num}: 缺少 type 字段')
            return errors
        
        step_type = step['type'].lower()
        
        if step_type not in cls.VALID_STEP_TYPES:
            errors.append(f'步骤 {step_num}: 未知的步骤类型 "{step_type}"')
            return errors
        
        # 验证 params 字段
        if 'params' not in step:
            errors.append(f'步骤 {step_num} ({step_type}): 缺少 params 字段')
            return errors
        
        if not isinstance(step['params'], dict):
            errors.append(f'步骤 {step_num} ({step_type}): params 必须是对象类型')
            return errors
        
        params = step['params']
        
        # 验证必填参数
        required = cls.REQUIRED_PARAMS.get(step_type, [])
        for param in required:
            if param not in params:
                errors.append(f'步骤 {step_num} ({step_type}): 缺少必填参数 "{param}"')
        
        # 特殊验证：wait_for_any_image 和 find_and_click_any 需要 folder 或 images
        if step_type in ['wait_for_any_image', 'find_and_click_any']:
            if 'folder' not in params and 'images' not in params:
                errors.append(f'步骤 {step_num} ({step_type}): 需要提供 folder 或 images 参数')
        
        # 验证参数类型
        for param_name, param_value in params.items():
            if param_name in cls.PARAM_TYPES:
                expected_types = cls.PARAM_TYPES[param_name]
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)
                if not isinstance(param_value, expected_types):
                    type_names = [t.__name__ for t in expected_types]
                    errors.append(
                        f'步骤 {step_num} ({step_type}): 参数 "{param_name}" 类型错误，'
                        f'期望 {"/".join(type_names)}，实际是 {type(param_value).__name__}'
                    )
        
        # 递归验证嵌套步骤（if/if_else）
        if step_type == 'if':
            if 'steps' in params and isinstance(params['steps'], list):
                for i, nested_step in enumerate(params['steps']):
                    nested_errors = cls.validate_step(nested_step, f'{step_num}.{i + 1}')
                    errors.extend(nested_errors)
        
        if step_type == 'if_else':
            if 'steps' in params and isinstance(params['steps'], list):
                for i, nested_step in enumerate(params['steps']):
                    nested_errors = cls.validate_step(nested_step, f'{step_num}.{i + 1}')
                    errors.extend(nested_errors)
            if 'else_steps' in params and isinstance(params['else_steps'], list):
                for i, nested_step in enumerate(params['else_steps']):
                    nested_errors = cls.validate_step(nested_step, f'{step_num}.else.{i + 1}')
                    errors.extend(nested_errors)
        
        return errors
    
    @classmethod
    def validate_and_fix(cls, script_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        验证脚本并尝试修复常见问题
        
        参数:
            script_data: 从 JSON5 加载的脚本数据
        
        返回:
            (修复后的脚本数据, 警告列表)
        """
        warnings = []
        
        # 复制原始数据
        fixed_data = script_data.copy()
        
        # 添加默认版本
        if 'version' not in fixed_data:
            fixed_data['version'] = '1.0'
            warnings.append('已添加默认版本号: 1.0')
        
        # 确保 steps 是列表
        if 'steps' not in fixed_data:
            fixed_data['steps'] = []
            warnings.append('已添加空 steps 数组')
        elif not isinstance(fixed_data['steps'], list):
            warnings.append(f'steps 类型错误，已重置为空数组')
            fixed_data['steps'] = []
        
        # 修复每个步骤
        fixed_steps = []
        for i, step in enumerate(fixed_data['steps']):
            if not isinstance(step, dict):
                warnings.append(f'步骤 {i + 1} 不是对象，已跳过')
                continue
            
            fixed_step = step.copy()
            
            # 确保有 type 字段
            if 'type' not in fixed_step:
                warnings.append(f'步骤 {i + 1} 缺少 type，已跳过')
                continue
            
            # 确保有 params 字段
            if 'params' not in fixed_step:
                fixed_step['params'] = {}
                warnings.append(f'步骤 {i + 1} ({fixed_step["type"]}): 已添加空 params')
            elif not isinstance(fixed_step['params'], dict):
                fixed_step['params'] = {}
                warnings.append(f'步骤 {i + 1} ({fixed_step["type"]}): params 类型错误，已重置')
            
            fixed_steps.append(fixed_step)
        
        fixed_data['steps'] = fixed_steps
        
        return fixed_data, warnings
