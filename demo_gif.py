# -*- coding: utf-8 -*-
"""自动生成演示 GIF：开始界面 -> AI 自动通关第 1 关 -> 通关界面
运行: python demo_gif.py
输出: screens/demo.gif
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import random
import pygame
from PIL import Image
from game import App, ArrowGame, solve_level, SCREEN_WIDTH, SCREEN_HEIGHT

random.seed(2026)

app = App()
frames = []

def grab():
    """把当前 surface 抓成 PIL Image"""
    raw = pygame.image.tostring(app.screen, "RGB")
    frames.append(Image.frombytes("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), raw))

def tick_anim():
    """推进一帧动画（对应主循环里的 tick）"""
    if app.game.collision_timer > 0:
        app.game.collision_timer -= 1

# 1. 开始界面停留
app.scene = "start"
app.draw_start()
for _ in range(18):
    grab()

# 2. 进入第 1 关
app.scene = "game"
app.game = ArrowGame(0)
_, order = solve_level(app.game.grid)
print("自动通关顺序:", order)

next_step = 0
gap = 18  # 每隔多少帧点一次
frame = 0
while app.game.status != "win":
    tick_anim()
    app.draw_game()
    grab()
    frame += 1
    # 当前没有在飞的动画时，按间隔点下一个箭头
    if not app.game.fly_animations and next_step < len(order) and frame % gap == 0:
        r, c = order[next_step]
        app.game.click(r, c)
        next_step += 1

# 3. 通关界面
app.win_next_available = True
app.scene = "win"
app.draw_game()
app.draw_result(win=True)
for _ in range(28):
    grab()

# 合成 GIF
out = os.path.join("screens", "demo.gif")
frames[0].save(out, save_all=True, append_images=frames[1:],
               duration=70, loop=0, optimize=True)
print("saved:", out, f"({len(frames)} frames)")
pygame.quit()
