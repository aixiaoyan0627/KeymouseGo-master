# -*- encoding:utf-8 -*-
"""
增强版日志系统

核心特点：
1. 分级日志（DEBUG/INFO/WARNING/ERROR）
2. 上下文日志（坐标、置信度、截图）
3. 按天分割日志文件
4. 识别失败自动保存截图
5. 脚本执行错误自动记录详细信息
"""
import os
import sys
import time
import datetime
from typing import Optional, Tuple, Any, Dict
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from loguru import logger


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class RecognitionContext:
    """识别上下文"""
    template_name: str
    success: bool
    position: Optional[Tuple[int, int]] = None
    confidence: float = 0.0
    region: Optional[Tuple[int, int, int, int]] = None
    screenshot_path: Optional[str] = None


@dataclass
class ScriptStepContext:
    """脚本步骤上下文"""
    step_index: int
    step_type: str
    params: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0


class EnhancedLogger:
    """
    增强版日志器
    
    提供：
    - 识别日志（带上下文和截图）
    - 脚本执行日志
    - 按天分割日志文件
    """
    
    def __init__(
        self,
        log_dir: str = "logs",
        log_level: str = "INFO",
        save_failure_screenshots: bool = True,
        max_screenshot_age_days: int = 7,
    ):
        """
        初始化增强日志器
        
        参数:
            log_dir: 日志目录
            log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
            save_failure_screenshots: 是否保存失败截图
            max_screenshot_age_days: 截图保留天数
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.save_failure_screenshots = save_failure_screenshots
        self.max_screenshot_age_days = max_screenshot_age_days
        
        self.screenshot_dir = self.log_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
        self._setup_logger(log_level)
        self._cleanup_old_screenshots()
    
    def _setup_logger(self, log_level: str):
        """配置 loguru 日志器"""
        logger.remove()
        
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stdout,
            format=log_format,
            level=log_level,
            colorize=True,
        )
        
        logger.add(
            self.log_dir / "keymousego_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="DEBUG",
            rotation="00:00",
            retention="30 days",
            encoding="utf-8",
        )
        
        logger.add(
            self.log_dir / "error_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="ERROR",
            rotation="00:00",
            retention="30 days",
            encoding="utf-8",
        )
    
    def _cleanup_old_screenshots(self):
        """清理旧的截图文件"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.max_screenshot_age_days)
            
            for screenshot_file in self.screenshot_dir.glob("*.png"):
                if screenshot_file.stat().st_mtime < cutoff_date.timestamp():
                    screenshot_file.unlink()
                    logger.debug(f"删除旧截图: {screenshot_file}")
        except Exception as e:
            logger.warning(f"清理旧截图失败: {e}")
    
    def _save_screenshot(self, frame: np.ndarray, prefix: str = "recognition") -> Optional[str]:
        """
        保存截图
        
        参数:
            frame: OpenCV 图像帧
            prefix: 文件名前缀
        
        返回:
            保存的文件路径
        """
        if not self.save_failure_screenshots:
            return None
        
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            
            cv2.imwrite(str(filepath), frame)
            return str(filepath)
        except Exception as e:
            logger.warning(f"保存截图失败: {e}")
            return None
    
    def log_recognition(
        self,
        template_name: str,
        success: bool,
        position: Optional[Tuple[int, int]] = None,
        confidence: float = 0.0,
        region: Optional[Tuple[int, int, int, int]] = None,
        frame: Optional[np.ndarray] = None,
    ) -> RecognitionContext:
        """
        记录识别结果
        
        参数:
            template_name: 模板名称
            success: 是否识别成功
            position: 识别到的坐标
            confidence: 置信度
            region: 检测区域
            frame: 图像帧（用于保存截图
        
        返回:
            识别上下文
        """
        screenshot_path = None
        if not success and frame is not None:
            screenshot_path = self._save_screenshot(frame, "fail")
        
        context = RecognitionContext(
            template_name=template_name,
            success=success,
            position=position,
            confidence=confidence,
            region=region,
            screenshot_path=screenshot_path,
        )
        
        if success:
            logger.info(
                f"识别成功 | 模板: {template_name} | "
                f"坐标: {position} | "
                f"置信度: {confidence:.2f}"
            )
        else:
            logger.error(
                f"识别失败 | 模板: {template_name} | "
                f"置信度: {confidence:.2f}",
            )
            if screenshot_path:
                logger.error(f"失败截图已保存: {screenshot_path}")
            if region:
                logger.error(f"检测区域: {region}")
        
        return context
    
    def log_script_step(
        self,
        step_index: int,
        step_type: str,
        params: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None,
        execution_time: float = 0.0,
        frame: Optional[np.ndarray] = None,
    ) -> ScriptStepContext:
        """
        记录脚本执行步骤
        
        参数:
            step_index: 步骤索引
            step_type: 步骤类型
            params: 步骤参数
            success: 是否成功
            error_message: 错误信息
            execution_time: 执行时间（秒）
            frame: 图像帧（用于保存截图）
        
        返回:
            脚本步骤上下文
        """
        screenshot_path = None
        if not success and frame is not None:
            screenshot_path = self._save_screenshot(frame, "script_fail")
        
        context = ScriptStepContext(
            step_index=step_index,
            step_type=step_type,
            params=params,
            success=success,
            error_message=error_message,
            execution_time=execution_time,
        )
        
        if success:
            logger.info(
                f"脚本步骤 {step_index} | "
                f"类型: {step_type} | "
                f"执行时间: {execution_time:.2f}s"
            )
        else:
            logger.error(
                f"脚本步骤 {step_index} 失败 | "
                f"类型: {step_type} | "
                f"错误: {error_message}"
            )
            if screenshot_path:
                logger.error(f"失败截图已保存: {screenshot_path}")
            if params:
                logger.error(f"步骤参数: {params}")
        
        return context
    
    def log_state_transition(
        self,
        from_state: str,
        to_state: str,
        event: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ):
        """
        记录状态机状态转换
        
        参数:
            from_state: 源状态
            to_state: 目标状态
            event: 触发事件
            context_data: 上下文数据
        """
        message = f"状态转换: {from_state} --> {to_state}"
        if event:
            message += f" | 事件: {event}"
        
        logger.info(message)
        
        if context_data:
            logger.debug(f"状态转换上下文: {context_data}")
    
    def log_input_action(
        self,
        action_type: str,
        position: Optional[Tuple[int, int]] = None,
        key: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """
        记录输入操作
        
        参数:
            action_type: 操作类型 (click/move/keypress等)
            position: 坐标
            key: 按键
            success: 是否成功
            error_message: 错误信息
        """
        if success:
            if action_type in ["click", "move"] and position:
                logger.info(f"输入操作: {action_type} | 坐标: {position}")
            elif action_type in ["keypress", "keyrelease"] and key:
                logger.info(f"输入操作: {action_type} | 按键: {key}")
            else:
                logger.info(f"输入操作: {action_type}")
        else:
            logger.error(f"输入操作失败: {action_type} | 错误: {error_message}")


# 全局增强日志器实例
_enhanced_logger: Optional[EnhancedLogger] = None


def init_enhanced_logger(
    log_dir: str = "logs",
    log_level: str = "INFO",
    save_failure_screenshots: bool = True,
) -> EnhancedLogger:
    """
    初始化全局增强日志器
    
    参数:
        log_dir: 日志目录
        log_level: 日志级别
        save_failure_screenshots: 是否保存失败截图
    
    返回:
        增强日志器实例
    """
    global _enhanced_logger
    _enhanced_logger = EnhancedLogger(
        log_dir=log_dir,
        log_level=log_level,
        save_failure_screenshots=save_failure_screenshots,
    )
    return _enhanced_logger


def get_enhanced_logger() -> EnhancedLogger:
    """
    获取全局增强日志器实例
    
    返回:
        增强日志器实例
    """
    global _enhanced_logger
    if _enhanced_logger is None:
        _enhanced_logger = EnhancedLogger()
    return _enhanced_logger
