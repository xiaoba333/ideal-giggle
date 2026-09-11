# -*- coding: utf-8 -*-
"""窗口模式全局状态（完整大屏 / 迷你小窗）。"""

# 模式常量
MODE_FULL = "full"
MODE_MINI = "mini"

# 固定尺寸（迷你模式：横屏；约为原迷你窗一半，字号不随窗口缩放）
FULL_WIDTH = 1200
FULL_HEIGHT = 800
MINI_WIDTH = 240
MINI_HEIGHT = 150

# 当前窗口模式（全局变量）
CURRENT_WINDOW_MODE = MODE_FULL


def is_mini_mode():
    """是否处于迷你小窗模式。"""
    return CURRENT_WINDOW_MODE == MODE_MINI


def set_mode(mode):
    """设置全局窗口模式。"""
    global CURRENT_WINDOW_MODE
    CURRENT_WINDOW_MODE = mode
