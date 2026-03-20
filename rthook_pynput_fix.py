# PyInstaller 运行时钩子 - 修复 pynput 与 shiboken/six 的冲突
import sys
import os

print("正在修复导入冲突...")

# 方法1: 禁用 shiboken 的 feature 检查
try:
    import shibokensupport
    if hasattr(shibokensupport, 'feature'):
        print("禁用 shiboken feature 检查...")
        # 保存原始函数
        original_feature_imported = shibokensupport.feature.feature_imported
        
        # 替换为不做任何事的函数
        def dummy_feature_imported(*args, **kwargs):
            pass
        
        shibokensupport.feature.feature_imported = dummy_feature_imported
except ImportError:
    print("shibokensupport 未找到")
except Exception as e:
    print(f"处理 shibokensupport 时出错: {e}")

# 方法2: 确保 six 模块正确加载
try:
    import six
    print(f"six 模块已加载: {six.__file__}")
except ImportError:
    print("six 模块未找到")
except Exception as e:
    print(f"加载 six 时出错: {e}")

# 方法3: 修复 _SixMetaPathImporter 的问题
try:
    # 查找并修复 six 的导入器
    for importer in sys.meta_path:
        if importer.__class__.__name__ == '_SixMetaPathImporter':
            print(f"找到 _SixMetaPathImporter: {importer}")
            # 确保它有 _path 属性
            if not hasattr(importer, '_path'):
                print("添加 _path 属性...")
                importer._path = []
except Exception as e:
    print(f"修复 _SixMetaPathImporter 时出错: {e}")

print("导入冲突修复完成")
