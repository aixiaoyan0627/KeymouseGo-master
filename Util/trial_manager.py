import os
import json
import time
from datetime import datetime, timedelta

LICENSE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.license_data')
TRIAL_DAYS = 7

class TrialManager:
    """试用期管理"""
    
    def __init__(self):
        self.license_file = LICENSE_FILE
        self.trial_days = TRIAL_DAYS
        self._load()
    
    def _load(self):
        """加载许可证数据"""
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.first_use_time = data.get('first_use_time', 0)
                    self.last_use_time = data.get('last_use_time', 0)
                    self.used_days = data.get('used_days', 0)
            except:
                self._reset()
        else:
            self._reset()
    
    def _reset(self):
        """重置许可证数据"""
        self.first_use_time = 0
        self.last_use_time = 0
        self.used_days = 0
    
    def _save(self):
        """保存许可证数据"""
        try:
            data = {
                'first_use_time': self.first_use_time,
                'last_use_time': self.last_use_time,
                'used_days': self.used_days
            }
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'保存许可证数据失败: {e}')
    
    def check_trial(self):
        """
        检查试用期状态
        返回: (是否通过检查, 剩余天数, 错误消息)
        """
        current_time = time.time()
        
        # 首次使用
        if self.first_use_time == 0:
            self.first_use_time = current_time
            self.last_use_time = current_time
            self.used_days = 1
            self._save()
            remaining = self.trial_days - 1
            return True, remaining, None
        
        # 检查是否相隔超过24小时（视为新的一天使用）
        day_seconds = 24 * 60 * 60
        days_since_last = (current_time - self.last_use_time) / day_seconds
        
        if days_since_last >= 1:
            # 更新使用天数
            self.used_days += int(days_since_last)
            self.last_use_time = current_time
            self._save()
        
        # 计算剩余天数
        remaining = self.trial_days - self.used_days
        
        if remaining <= 0:
            return False, 0, f'试用期已结束，软件已锁死'
        
        return True, remaining, None
    
    def get_remaining_days(self):
        """获取剩余天数"""
        if self.first_use_time == 0:
            return self.trial_days
        return max(0, self.trial_days - self.used_days)
    
    def get_used_days(self):
        """获取已使用天数"""
        return self.used_days


def check_trial():
    """检查试用期的便捷函数"""
    manager = TrialManager()
    passed, remaining, error_msg = manager.check_trial()
    return passed, remaining, error_msg
