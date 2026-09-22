# -*- coding: utf-8 -*-
"""一箭又一箭 - 核心逻辑测试（不依赖图形界面）
运行: python test_logic.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import random
from game import ArrowGame, LEVEL_CONFIG, solve_level, random_grid, GRID_ROWS, GRID_COLS

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {detail}")

print("=" * 50)
print("T00 随机关卡生成器：随机生成的棋盘一定可解")
print("=" * 50)
random.seed(42)
for i, cfg in enumerate(LEVEL_CONFIG):
    ok_all = True
    for _ in range(20):
        g = random_grid(cfg["arrows"])
        ok, order = solve_level(g)
        if not ok:
            ok_all = False
            break
    check(f"第 {i+1} 关（{cfg['arrows']}箭头）20 次随机生成均可解", ok_all)

print("=" * 50)
print("T01 点击前方无阻挡的箭头 -> 飞出并消失")
print("=" * 50)
g = ArrowGame(0)
fly_target = None
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        if g.grid[r][c] is not None and g.path_clear(r, c):
            fly_target = (r, c)
            break
    if fly_target:
        break
check("存在可飞箭头", fly_target is not None)
if fly_target:
    r, c = fly_target
    res = g.click(r, c)
    check("返回 fly", res == "fly", res)
    check("箭头被消除", g.grid[r][c] is None)
    check("失误次数不变", g.mistakes_left == LEVEL_CONFIG[0]["mistakes"])

print("=" * 50)
print("T02 点击前方有阻挡的箭头 -> 不消失，失误-1")
print("=" * 50)
g = ArrowGame(1)
blocked_target = None
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        if g.grid[r][c] is not None and not g.path_clear(r, c):
            blocked_target = (r, c)
            break
    if blocked_target:
        break
check("存在被阻挡的箭头", blocked_target is not None)
if blocked_target:
    r, c = blocked_target
    res = g.click(r, c)
    check("返回 collision", res == "collision", res)
    check("箭头未被消除", g.grid[r][c] is not None)
    check("失误次数减1", g.mistakes_left == LEVEL_CONFIG[1]["mistakes"] - 1, g.mistakes_left)

print("=" * 50)
print("T03 边缘朝外的箭头 -> 正常消失，无越界")
print("=" * 50)
g = ArrowGame(0)
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        try:
            g.path_clear(r, c)
        except IndexError:
            check(f"path_clear({r},{c}) 无越界", False, "IndexError")
check("path_clear 全棋盘遍历无越界", True)
edge_fly = None
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        if g.grid[r][c] is not None and g.path_clear(r, c):
            edge_fly = (r, c)
            break
    if edge_fly:
        break
if edge_fly:
    check("边缘箭头正常飞出", g.click(*edge_fly) == "fly")

print("=" * 50)
print("T04 消除全部箭头 -> 通关并进入下一关")
print("=" * 50)
g = ArrowGame(0)
_, order = solve_level(g.grid)
for r, c in order:
    g.click(r, c)
check("状态为 win", g.status == "win", g.status)
check("棋盘清空", g.remaining_arrows() == 0)
ok = g.next_level()
check("进入下一关", ok)
check("新关卡索引为1", g.level_index == 1)
check("下一关箭头数正确", g.remaining_arrows() == LEVEL_CONFIG[1]["arrows"])

print("=" * 50)
print("T05 失误次数耗尽 -> 失败")
print("=" * 50)
g = ArrowGame(1)
limit = LEVEL_CONFIG[1]["mistakes"]
hits = 0
while g.status != "lose" and hits < 80:
    hits += 1
    target = None
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if g.grid[r][c] is not None and not g.path_clear(r, c):
                target = (r, c)
                break
        if target:
            break
    if not target:
        break
    g.click(*target)
check("状态为 lose", g.status == "lose", g.status)
check("点击失败后无效", g.click(0, 0) == "invalid")
g.reset()
check("重新开始后状态恢复", g.status == "playing" and g.mistakes_left == limit)

print("=" * 50)
print("T06 游戏进行中重新开始 -> 布局和失误次数恢复")
print("=" * 50)
g = ArrowGame(0)
start_count = g.remaining_arrows()
for r in range(GRID_ROWS):
    for c in range(GRID_COLS):
        if g.grid[r][c] is not None and g.path_clear(r, c):
            g.click(r, c)
            break
    else:
        continue
    break
g.reset()
check("箭头数量恢复到初始", g.remaining_arrows() == start_count, f"{g.remaining_arrows()} vs {start_count}")
check("失误次数恢复", g.mistakes_left == LEVEL_CONFIG[0]["mistakes"], g.mistakes_left)
check("状态为 playing", g.status == "playing")

print("=" * 50)
print(f"结果: {passed} 通过, {failed} 失败")
print("=" * 50)
sys.exit(1 if failed else 0)
