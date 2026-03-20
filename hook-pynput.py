# 解决 pynput 与 shiboken/six 的冲突
import sys

# 在导入 pynput 之前，禁用 shiboken 的 feature 检查
try:
    import shibokensupport
    # 移除 feature_imported 钩子
    if hasattr(shibokensupport, 'feature'):
        shibokensupport.feature.feature_imported = lambda *args, **kwargs: None
except ImportError:
    pass

# 确保 six 模块正确导入
try:
    import six
except ImportError:
    pass
