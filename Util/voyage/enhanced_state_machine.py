# -*- encoding:utf-8 -*-
"""
增强版状态机基础类

核心特点：
1. 每个状态独立的超时配置
2. 状态回滚机制
3. 通用异常事件处理
4. 状态机与执行器解耦
"""
import time
from enum import Enum, auto
from typing import Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from loguru import logger


class StateMachineEvent(Enum):
    """状态机事件类型"""
    # 正常事件
    SUCCESS = auto()
    FAILURE = auto()
    TIMEOUT = auto()
    
    # 异常事件
    ERROR = auto()
    RECOVERY = auto()
    ROLLBACK = auto()


@dataclass
class StateConfig:
    """单个状态的配置"""
    name: str
    timeout: float = 30.0  # 状态超时时间（秒）
    max_retries: int = 3   # 最大重试次数
    rollback_to: Optional[str] = None  # 超时/失败时回滚到的状态
    on_enter: Optional[Callable] = None  # 进入状态时的回调
    on_exit: Optional[Callable] = None  # 离开状态时的回调
    on_timeout: Optional[Callable] = None  # 超时时的回调
    on_failure: Optional[Callable] = None  # 失败时的回调


class EnhancedStateMachine:
    """
    增强版状态机
    
    核心特性：
    - 每个状态独立的超时配置
    - 状态回滚机制
    - 重试机制
    - 事件驱动的状态转换
    """
    
    def __init__(self, name: str = "StateMachine", log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化状态机
        
        参数:
            name: 状态机名称
            log_callback: 日志回调函数
        """
        self.name = name
        self.log = log_callback or print
        
        # 状态配置
        self._states: Dict[str, StateConfig] = {}
        
        # 当前状态
        self._current_state: Optional[str] = None
        self._previous_state: Optional[str] = None
        
        # 状态计时
        self._state_start_time: float = 0.0
        self._state_retry_count: int = 0
        
        # 状态转换表
        self._transitions: Dict[str, Dict[StateMachineEvent, str]] = {}
        
        # 状态执行器
        self._state_executors: Dict[str, Callable] = {}
        
        # 运行状态
        self._running: bool = False
        self._paused: bool = False
        
        # 上下文数据
        self._context: Dict[str, Any] = {}
    
    def register_state(self, config: StateConfig) -> 'EnhancedStateMachine':
        """
        注册一个状态
        
        参数:
            config: 状态配置
        
        返回:
            self（支持链式调用）
        """
        self._states[config.name] = config
        self.log(f'[{self.name}] 注册状态: {config.name} (超时: {config.timeout}s, 重试: {config.max_retries})')
        return self
    
    def register_transition(
        self, 
        from_state: str, 
        event: StateMachineEvent, 
        to_state: str
    ) -> 'EnhancedStateMachine':
        """
        注册状态转换
        
        参数:
            from_state: 源状态
            event: 触发事件
            to_state: 目标状态
        
        返回:
            self（支持链式调用）
        """
        if from_state not in self._transitions:
            self._transitions[from_state] = {}
        self._transitions[from_state][event] = to_state
        self.log(f'[{self.name}] 注册转换: {from_state} --[{event.name}]--> {to_state}')
        return self
    
    def register_executor(self, state: str, executor: Callable) -> 'EnhancedStateMachine':
        """
        注册状态执行器
        
        参数:
            state: 状态名称
            executor: 执行器函数，返回 StateMachineEvent
        
        返回:
            self（支持链式调用）
        """
        self._state_executors[state] = executor
        return self
    
    def set_context(self, key: str, value: Any):
        """设置上下文数据"""
        self._context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self._context.get(key, default)
    
    @property
    def current_state(self) -> Optional[str]:
        """当前状态"""
        return self._current_state
    
    @property
    def previous_state(self) -> Optional[str]:
        """上一个状态"""
        return self._previous_state
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def start(self, initial_state: str) -> bool:
        """
        启动状态机
        
        参数:
            initial_state: 初始状态
        
        返回:
            是否启动成功
        """
        if initial_state not in self._states:
            self.log(f'[{self.name}] 初始状态不存在: {initial_state}')
            return False
        
        self._running = True
        self._paused = False
        self._transition_to(initial_state)
        self.log(f'[{self.name}] 已启动，初始状态: {initial_state}')
        return True
    
    def stop(self):
        """停止状态机"""
        self._running = False
        self._paused = False
        self.log(f'[{self.name}] 已停止')
    
    def pause(self):
        """暂停状态机"""
        if self._running:
            self._paused = True
            self.log(f'[{self.name}] 已暂停')
    
    def resume(self):
        """恢复状态机"""
        if self._running and self._paused:
            self._paused = False
            self.log(f'[{self.name}] 已恢复')
    
    def _transition_to(self, state: str):
        """
        转换到指定状态
        
        参数:
            state: 目标状态
        """
        # 离开当前状态
        if self._current_state and self._current_state in self._states:
            old_config = self._states[self._current_state]
            if old_config.on_exit:
                try:
                    old_config.on_exit(self._context)
                except Exception as e:
                    logger.warning(f'[{self.name}] 离开状态 {self._current_state} 时出错: {e}')
        
        # 更新状态
        self._previous_state = self._current_state
        self._current_state = state
        self._state_start_time = time.time()
        self._state_retry_count = 0
        
        # 进入新状态
        if state in self._states:
            new_config = self._states[state]
            if new_config.on_enter:
                try:
                    new_config.on_enter(self._context)
                except Exception as e:
                    logger.warning(f'[{self.name}] 进入状态 {state} 时出错: {e}')
        
        self.log(f'[{self.name}] 状态转换: {self._previous_state or "NONE"} --> {state}')
    
    def _check_timeout(self) -> bool:
        """
        检查当前状态是否超时
        
        返回:
            是否超时
        """
        if not self._current_state or self._current_state not in self._states:
            return False
        
        config = self._states[self._current_state]
        elapsed = time.time() - self._state_start_time
        
        if elapsed >= config.timeout:
            self.log(f'[{self.name}] 状态超时: {self._current_state} ({elapsed:.1f}s >= {config.timeout}s)')
            
            if config.on_timeout:
                try:
                    config.on_timeout(self._context)
                except Exception as e:
                    logger.warning(f'[{self.name}] 超时回调出错: {e}')
            
            return True
        
        return False
    
    def _handle_event(self, event: StateMachineEvent):
        """
        处理事件并执行状态转换
        
        参数:
            event: 触发的事件
        """
        if not self._current_state:
            return
        
        # 查找转换规则
        if self._current_state in self._transitions:
            transitions = self._transitions[self._current_state]
            if event in transitions:
                next_state = transitions[event]
                self._transition_to(next_state)
                return
        
        # 如果没有定义转换，尝试使用状态配置的回滚
        if event in [StateMachineEvent.TIMEOUT, StateMachineEvent.FAILURE]:
            if self._current_state in self._states:
                config = self._states[self._current_state]
                if config.rollback_to:
                    self.log(f'[{self.name}] 事件 {event.name}，回滚到: {config.rollback_to}')
                    self._transition_to(config.rollback_to)
                    return
        
        self.log(f'[{self.name}] 未定义转换: {self._current_state} --[{event.name}]--> ?')
    
    def run_step(self) -> bool:
        """
        执行一步状态机
        
        返回:
            是否继续运行
        """
        if not self._running:
            return False
        
        if self._paused:
            time.sleep(0.1)
            return True
        
        if not self._current_state:
            self.log(f'[{self.name}] 未设置当前状态')
            return False
        
        # 检查超时
        if self._check_timeout():
            self._handle_event(StateMachineEvent.TIMEOUT)
            return True
        
        # 执行当前状态
        if self._current_state in self._state_executors:
            try:
                executor = self._state_executors[self._current_state]
                event = executor(self._context)
                
                if event != StateMachineEvent.SUCCESS:
                    self._state_retry_count += 1
                    
                    # 检查是否超过最大重试次数
                    config = self._states[self._current_state]
                    if self._state_retry_count >= config.max_retries:
                        self.log(f'[{self.name}] 状态 {self._current_state} 重试次数已达上限 ({config.max_retries})')
                        if config.on_failure:
                            try:
                                config.on_failure(self._context)
                            except Exception as e:
                                logger.warning(f'[{self.name}] 失败回调出错: {e}')
                        self._handle_event(StateMachineEvent.FAILURE)
                    else:
                        self.log(f'[{self.name}] 状态 {self._current_state} 重试 {self._state_retry_count}/{config.max_retries}')
                else:
                    # 成功，重置重试计数
                    self._state_retry_count = 0
                    self._handle_event(event)
                    
            except Exception as e:
                logger.exception(f'[{self.name}] 执行状态 {self._current_state} 出错: {e}')
                self._handle_event(StateMachineEvent.ERROR)
        
        return True
    
    def run(self):
        """运行状态机主循环"""
        while self._running:
            if not self.run_step():
                break
            time.sleep(0.1)
