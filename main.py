import os
import json5
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
class SomeClass:
    def __init__(self):
        # 确保这行代码有正确的缩进（通常是4个空格）
        super().__init__()
        self.setup_ui()
        self.filename = None
        self.default_filename = "0215_1200.json5"  # 修改默认文件名
        self.load_config()
    def on_open(self):
        """打开数据文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "JSON5 Files (*.json5);;All Files (*)")
        if filename:
            self.filename = filename
            self.load_script(filename)
            
    def load_script(self, filename):
        """加载数据文件"""
        if filename:
            try:
                # 添加文件存在性检查
                if not os.path.exists(filename):
                    QMessageBox.warning(self, "错误", f"文件不存在: {filename}")
                    return
                    
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json5.load(f)
                    # ... existing code ...
            except FileNotFoundError:
                QMessageBox.warning(self, "错误", f"文件不存在: {filename}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载文件失败: {str(e)}")
                
    def on_save_as(self):
        """另存为数据文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存数据文件", self.filename or self.default_filename,
            "JSON5 Files (*.json5);;All Files (*)")
        if filename:
            self.filename = filename
            self.save_script(filename)
            
    def on_start_detection(self):
        """开始检测"""
        if not self.filename or not os.path.exists(self.filename):
            QMessageBox.warning(self, "错误", "请先选择有效的脚本文件")
            return
            
        # ... 原有的开始检测逻辑 ...