# -*- coding: utf-8 -*-
"""
泡泡堂家族比赛积分竞猜系统 - 程序入口

单机本地运行，数据库随 exe 同目录自动生成。

@author hyq
@version 2026-07-14
"""

import os
import sys

# 【防闪退黄金配置】解决部分精简版 Win10 / 老旧电脑因 OpenGL 显卡硬件加速初始化失败导致秒退的经典缺陷
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_OPENGL"] = "software"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from src.database.db_manager import DBManager
from src.database.repository import Repository
from src.ui.main_window import MainWindow


def get_db_path() -> str:
    """
    获取数据库文件路径：与可执行文件（或脚本）同目录

    @author hyq
    @version 2026-07-13
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发模式下的路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "bnb_guessing.db")


def main() -> None:
    """
    程序主入口

    @author hyq
    @version 2026-07-13
    """
    # 初始化数据库
    db_path = get_db_path()
    db_manager = DBManager(db_path)
    repository = Repository(db_manager)
    repository.initialize_db()

    # 启动 Qt 应用
    app = QApplication(sys.argv)

    # 设置全局默认字体
    app.setFont(QFont("Microsoft YaHei UI", 10))

    # 创建并显示主窗口
    window = MainWindow(repository)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
