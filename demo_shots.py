# -*- coding: utf-8 -*-
"""生成游戏各界面截图（离屏渲染，不弹出窗口）
运行: python demo_shots.py
输出: screens/ 目录下的 png 文件
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import random
import pygame
from game import App, ArrowGame, solve_level, LEVEL_CONFIG

os.makedirs("screens", exist_ok=True)
random.seed(2026)  # 固定种子，保证每次截图棋盘一致


def shot(app, name):
    path = os.path.join("screens", name)
    pygame.image.save(app.screen, path)
    print("saved:", path)


app = App()

# 1. 开始界面
app.scene = "start"
app.draw_start()
shot(app, "01_start.png")

# 2-4. 三个关卡的游戏界面（随机生成，固定种子）
for i in range(len(LEVEL_CONFIG)):
    app.scene = "game"
    app.game = ArrowGame(i)
    app.draw_game()
    shot(app, f"02_level{i+1}.png")

# 5. 碰撞反馈（第2关找一个被阻挡的箭头点）
app.game = ArrowGame(1)
blocked = None
for r in range(6):
    for c in range(6):
        if app.game.grid[r][c] is not None and not app.game.path_clear(r, c):
            blocked = (r, c)
            break
    if blocked:
        break
if blocked:
    app.game.click(*blocked)
app.game.collision_timer = 30
app.draw_game()
shot(app, "05_collision.png")

# 6. 通关界面（第1关按解自动消除）
app.game = ArrowGame(0)
_, order = solve_level(app.game.grid)
for r, c in order:
    app.game.click(r, c)
app.win_next_available = True
app.scene = "win"
app.draw_game()
app.draw_result(win=True)
shot(app, "06_win.png")

# 7. 失败界面（第2关连续点被阻挡箭头直到失误耗尽）
app.game = ArrowGame(1)
while app.game.status != "lose":
    target = None
    for r in range(6):
        for c in range(6):
            if app.game.grid[r][c] is not None and not app.game.path_clear(r, c):
                target = (r, c)
                break
        if target:
            break
    if not target:
        break
    app.game.click(*target)
app.scene = "lose"
app.draw_game()
app.draw_result(win=False)
shot(app, "07_lose.png")

pygame.quit()
print("done")
