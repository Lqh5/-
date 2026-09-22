# -*- coding: utf-8 -*-
"""
一箭又一箭 (Arrow Out) - 点击式箭头解谜小游戏

玩法：
- 棋盘上有带方向的箭头（上/下/左/右）
- 点击箭头，若其前进方向到棋盘边界之间没有其他箭头，则飞出并消除
- 若被阻挡，则发生碰撞反馈，并消耗一次失误机会
- 消除本关全部箭头进入下一关；失误次数耗尽则本关失败

运行：python game.py
"""
import sys
import os
import pygame
import random

# ============ 基本配置 ============
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 640
GRID_ROWS = 6
GRID_COLS = 6
CELL_SIZE = 80
GRID_X = (SCREEN_WIDTH - GRID_COLS * CELL_SIZE) // 2  # 棋盘左上角 x
GRID_Y = 110                                          # 棋盘左上角 y

# 方向定义：0=上, 1=右, 2=下, 3=左
# 注意：网格索引 (r, c)，r 是行（向下增），c 是列（向右增）
DIRECTIONS = {
    0: (-1, 0),   # 上：行减 1
    1: (0, 1),    # 右：列加 1
    2: (1, 0),    # 下：行加 1
    3: (0, -1),   # 左：列减 1
}
DIR_ARROWS = {0: "↑", 1: "→", 2: "↓", 3: "←"}
DIR_CHARS = {"^": 0, ">": 1, "v": 2, "<": 3, "V": 2}

# 颜色（深蓝渐变风格）
COLOR_BG_TOP = (22, 25, 42)
COLOR_BG_BOT = (46, 52, 86)
COLOR_PANEL = (40, 46, 70)
COLOR_CELL = (58, 66, 94)
COLOR_CELL_HOVER = (80, 92, 128)
COLOR_ARROW = (245, 248, 255)
COLOR_ARROW_HIT = (255, 95, 95)
COLOR_TEXT = (232, 236, 245)
COLOR_ACCENT = (110, 190, 255)
COLOR_GREEN = (110, 225, 150)
COLOR_RED = (255, 110, 110)
COLOR_YELLOW = (255, 215, 100)
COLOR_ARROW_OUTLINE = (20, 24, 40)

# ============ 关卡配置（3 关，难度递增） ============
# 每关不写死布局，而是在游戏开始时按箭头数量随机生成。
# 生成算法见 random_grid()：保证生成的关卡一定可通关。
# arrows: 本关箭头数量（越多越难）  mistakes: 允许的失误次数
LEVEL_CONFIG = [
    {"arrows": 4, "mistakes": 3},   # 第 1 关：入门
    {"arrows": 6, "mistakes": 3},  # 第 2 关：进阶
    {"arrows": 8, "mistakes": 4},   # 第 3 关：挑战
]


def random_grid(num_arrows):
    """随机生成一个保证可通关、且有解谜性的棋盘。

    反推法：从空棋盘开始逐个放箭头。放新箭头 (r,c,d) 时，要求它沿 d 方向
    的前方路径上没有任何已存在的箭头。这样"按放置顺序倒着消除"一定能通关。
    为了让关卡有难度，新箭头会**优先落在某个旧箭头的前方路径上**
    （即挡住旧箭头），从而制造"必须先消新箭头"的顺序依赖。
    """
    grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    placed = []  # 已放箭头 (r, c, d)
    for _ in range(num_arrows):
        candidates = []       # 合法候选（前方无已放箭头）
        blocking_candidates = []  # 其中能挡住某个旧箭头的候选
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if grid[r][c] is not None:
                    continue
                for d in range(4):
                    dr, dc = DIRECTIONS[d]
                    nr, nc = r + dr, c + dc
                    ok = True
                    while 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                        if grid[nr][nc] is not None:
                            ok = False
                            break
                        nr += dr
                        nc += dc
                    if not ok:
                        continue
                    # 检查这个候选是否挡住某个旧箭头
                    blocks_some = False
                    for (or_, oc, od) in placed:
                        odr, odc = DIRECTIONS[od]
                        nr2, nc2 = or_ + odr, oc + odc
                        while 0 <= nr2 < GRID_ROWS and 0 <= nc2 < GRID_COLS:
                            if (nr2, nc2) == (r, c):
                                blocks_some = True
                                break
                            nr2 += odr
                            nc2 += odc
                        if blocks_some:
                            break
                    if blocks_some:
                        blocking_candidates.append((r, c, d))
                    else:
                        candidates.append((r, c, d))
        # 优先选能挡住旧箭头的位置，制造解谜依赖
        if blocking_candidates and random.random() < 0.7:
            r, c, d = random.choice(blocking_candidates)
        elif candidates:
            r, c, d = random.choice(candidates)
        elif blocking_candidates:
            r, c, d = random.choice(blocking_candidates)
        else:
            break  # 放不下了（棋盘太满）
        grid[r][c] = d
        placed.append((r, c, d))
    return grid


def parse_level(rows):
    """把字符串数组解析成二维网格。
    返回: list[list[int or None]]，值为方向 0-3 或 None(空格)
    """
    grid = []
    for row in rows:
        cells = []
        for ch in row.split():
            if ch == ".":
                cells.append(None)
            else:
                cells.append(DIR_CHARS[ch])
        grid.append(cells)
    return grid


class ArrowGame:
    """游戏核心逻辑（与图形解耦，便于测试）"""

    def __init__(self, level_index=0):
        self.level_index = level_index
        self.mistakes_left = LEVEL_CONFIG[level_index]["mistakes"]
        self.grid = random_grid(LEVEL_CONFIG[level_index]["arrows"])
        self.status = "playing"  # playing / win / lose
        self.last_collision = None  # 最近碰撞的箭头坐标，用于反馈
        self.collision_timer = 0
        self.fly_animations = []  # 正在飞出的箭头动画列表

    def reset(self):
        """重新开始当前关卡（重新随机生成本关布局）"""
        self.mistakes_left = LEVEL_CONFIG[self.level_index]["mistakes"]
        self.grid = random_grid(LEVEL_CONFIG[self.level_index]["arrows"])
        self.status = "playing"
        self.last_collision = None
        self.fly_animations = []

    def next_level(self):
        """进入下一关（若还有），下一关会重新随机生成"""
        if self.level_index + 1 < len(LEVEL_CONFIG):
            self.level_index += 1
            self.reset()
            return True
        return False

    def remaining_arrows(self):
        """当前剩余箭头数量"""
        return sum(1 for row in self.grid for cell in row if cell is not None)

    def path_clear(self, r, c):
        """判断 (r,c) 处的箭头在其前进方向上是否畅通无阻"""
        direction = self.grid[r][c]
        if direction is None:
            return False
        dr, dc = DIRECTIONS[direction]
        nr, nc = r + dr, c + dc
        while 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
            if self.grid[nr][nc] is not None:
                return False  # 被其他箭头阻挡
            nr += dr
            nc += dc
        return True  # 畅通到边界

    def click(self, r, c):
        """点击棋盘上的 (r,c)。
        返回: "fly" 飞出 / "collision" 碰撞 / "empty" 空格子 / "invalid" 无效
        """
        if self.status != "playing":
            return "invalid"
        if self.grid[r][c] is None:
            return "empty"
        if self.path_clear(r, c):
            # 飞出
            direction = self.grid[r][c]
            self.grid[r][c] = None
            self.fly_animations.append({
                "r": r, "c": c, "direction": direction, "progress": 0.0
            })
            # 检查是否通关
            if self.remaining_arrows() == 0:
                self.status = "win"
            return "fly"
        else:
            # 碰撞：失误次数 -1，记录碰撞位置用于反馈
            self.mistakes_left -= 1
            self.last_collision = (r, c)
            self.collision_timer = 30  # 30 帧的碰撞反馈
            if self.mistakes_left <= 0:
                self.status = "lose"
            return "collision"


class ArrowButton:
    """把方向数字转换成可绘制的箭头多边形坐标（顶点从箭头尖开始逆时针）"""

    @staticmethod
    def points(direction, cx, cy, size):
        h = size * 0.32  # 箭头半高
        l = size * 0.42  # 箭头半长
        if direction == 1:    # 右
            return [(cx + l, cy), (cx - l * 0.4, cy - h), (cx - l * 0.4, cy + h)]
        elif direction == 3:  # 左
            return [(cx - l, cy), (cx + l * 0.4, cy - h), (cx + l * 0.4, cy + h)]
        elif direction == 0:  # 上
            return [(cx, cy - l), (cx - h, cy + l * 0.4), (cx + h, cy + l * 0.4)]
        elif direction == 2:  # 下
            return [(cx, cy + l), (cx - h, cy - l * 0.4), (cx + h, cy - l * 0.4)]
        return []


class App:
    """Pygame 主应用"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("一箭又一箭 - Arrow Out")
        self.clock = pygame.time.Clock()
        # 加载系统中文字体（避免 SysFont 在离屏模式下枚举 bug，同时保证中文显示）
        font_path = None
        for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
                  r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
            if os.path.exists(p):
                font_path = p
                break
        self.font = pygame.font.Font(font_path, 24)
        self.font_small = pygame.font.Font(font_path, 18)
        self.font_big = pygame.font.Font(font_path, 44)
        self.game = ArrowGame(0)
        self.scene = "start"  # start / game / win / lose
        self.win_next_available = False  # 是否还有下一关
        self.hover_cell = None
        self.mouse_pos = (0, 0)
        # 预渲染垂直渐变背景（只做一次，每帧直接贴）
        self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(COLOR_BG_TOP[0] + (COLOR_BG_BOT[0] - COLOR_BG_TOP[0]) * t)
            g = int(COLOR_BG_TOP[1] + (COLOR_BG_BOT[1] - COLOR_BG_TOP[1]) * t)
            b = int(COLOR_BG_TOP[2] + (COLOR_BG_BOT[2] - COLOR_BG_TOP[2]) * t)
            pygame.draw.line(self.bg, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    # ---------- 绘制辅助 ----------
    def draw_text(self, text, size, color, x, y, center=True):
        f = self.font_big if size == 44 else (self.font if size == 24 else self.font_small)
        surf = f.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)

    def cell_rect(self, r, c):
        return pygame.Rect(GRID_X + c * CELL_SIZE, GRID_Y + r * CELL_SIZE,
                           CELL_SIZE, CELL_SIZE)

    def draw_grid(self):
        """绘制棋盘和箭头"""
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                rect = self.cell_rect(r, c)
                # 格子背景
                if self.hover_cell == (r, c) and self.game.grid[r][c] is not None:
                    pygame.draw.rect(self.screen, COLOR_CELL_HOVER, rect, border_radius=12)
                else:
                    pygame.draw.rect(self.screen, COLOR_CELL, rect, border_radius=12)
                pygame.draw.rect(self.screen, (30, 34, 54), rect, width=2, border_radius=12)

                direction = self.game.grid[r][c]
                if direction is None:
                    continue
                cx, cy = rect.center
                # 碰撞反馈：红色高亮 + 抖动
                if self.game.last_collision == (r, c) and self.game.collision_timer > 0:
                    offset = random.randint(-5, 5)
                    pts = ArrowButton.points(direction, cx + offset, cy, CELL_SIZE * 0.62)
                    # 红色箭头先画深色描边再填色
                    outline = [(int(x * 1.15 + (cx + offset) * -0.15),
                                 int(y * 1.15 + cy * -0.15)) for x, y in pts]
                    pygame.draw.polygon(self.screen, (140, 30, 30), outline)
                    pygame.draw.polygon(self.screen, COLOR_ARROW_HIT, pts)
                else:
                    pts = ArrowButton.points(direction, cx, cy, CELL_SIZE * 0.62)
                    outline = [(int(x * 1.12 + cx * -0.12),
                                 int(y * 1.12 + cy * -0.12)) for x, y in pts]
                    pygame.draw.polygon(self.screen, COLOR_ARROW_OUTLINE, outline)
                    pygame.draw.polygon(self.screen, COLOR_ARROW, pts)

        # 飞出动画：沿方向移动并淡出
        for anim in self.game.fly_animations:
            dr, dc = DIRECTIONS[anim["direction"]]
            anim["progress"] += 0.08
            if anim["progress"] >= 1.0:
                continue
            rect = self.cell_rect(anim["r"], anim["c"])
            cx = rect.centerx + dc * CELL_SIZE * anim["progress"] * 2.5
            cy = rect.centery + dr * CELL_SIZE * anim["progress"] * 2.5
            alpha = max(0, 1 - anim["progress"])
            color = (int(245 * alpha), int(248 * alpha), int(255 * alpha))
            if alpha > 0:
                pts = ArrowButton.points(anim["direction"], int(cx), int(cy), CELL_SIZE * 0.62 * alpha)
                pygame.draw.polygon(self.screen, color, pts)
        # 清理完成的动画
        self.game.fly_animations = [a for a in self.game.fly_animations if a["progress"] < 1.0]

    def draw_hud(self):
        """顶部状态栏：关卡、剩余箭头、失误次数、重新开始"""
        pygame.draw.rect(self.screen, (*COLOR_PANEL, ), (0, 0, SCREEN_WIDTH, 92))
        # 底部一条高亮分隔线
        pygame.draw.line(self.screen, COLOR_ACCENT, (0, 92), (SCREEN_WIDTH, 92), 2)
        self.draw_text(f"关卡 {self.game.level_index + 1} / {len(LEVEL_CONFIG)}", 24,
                       COLOR_ACCENT, 90, 46)
        self.draw_text(f"剩余箭头: {self.game.remaining_arrows()}", 24,
                       COLOR_TEXT, 290, 46)
        self.draw_text(f"失误: {self.game.mistakes_left}/{LEVEL_CONFIG[self.game.level_index]['mistakes']}",
                       24, COLOR_RED, 520, 46)
        # 重新开始按钮（hover 变亮）
        self.restart_rect = pygame.Rect(655, 22, 125, 48)
        hovered = self.restart_rect.collidepoint(self.mouse_pos)
        btn_color = (140, 205, 255) if hovered else COLOR_ACCENT
        pygame.draw.rect(self.screen, btn_color, self.restart_rect, border_radius=12)
        self.draw_text("重开", 20, (20, 30, 40),
                       self.restart_rect.centerx, self.restart_rect.centery)

    def draw_start(self):
        self.screen.blit(self.bg, (0, 0))
        cx = SCREEN_WIDTH // 2
        # 标题下加装饰线
        pygame.draw.line(self.screen, COLOR_ACCENT, (cx - 180, 260), (cx + 180, 260), 3)
        self.draw_text("一 箭 又 一 箭", 44, COLOR_ACCENT, cx, 210)
        self.draw_text("点击箭头，让它在不被阻挡的情况下飞出棋盘", 24, COLOR_TEXT, cx, 310)
        self.draw_text("被阻挡的箭头会碰撞并消耗一次失误机会", 20, COLOR_YELLOW, cx, 350)
        self.draw_text(f"消除全部箭头即可过关！共 3 关", 20, COLOR_GREEN, cx, 390)
        self.start_rect = pygame.Rect(cx - 100, 440, 200, 62)
        hovered = self.start_rect.collidepoint(self.mouse_pos)
        btn_color = (140, 240, 175) if hovered else COLOR_GREEN
        pygame.draw.rect(self.screen, btn_color, self.start_rect, border_radius=14)
        self.draw_text("开始游戏", 26, (20, 30, 40),
                       self.start_rect.centerx, self.start_rect.centery)
        self.draw_text("提示：优先点击能直接飞出的箭头", 18, (150, 160, 190), cx, 560)

    def draw_game(self):
        self.screen.blit(self.bg, (0, 0))
        self.draw_hud()
        self.draw_grid()

    def draw_result(self, win):
        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 20, 170))
        self.screen.blit(overlay, (0, 0))
        cx = SCREEN_WIDTH // 2
        # 中央圆角卡片
        card = pygame.Rect(cx - 230, 200, 460, 300)
        pygame.draw.rect(self.screen, (36, 42, 66), card, border_radius=18)
        pygame.draw.rect(self.screen, COLOR_ACCENT if win else COLOR_RED, card,
                         width=2, border_radius=18)
        if win:
            self.draw_text("★ 恭喜通关！", 44, COLOR_GREEN, cx, 270)
            self.draw_text(f"第 {self.game.level_index + 1} 关已清除", 24, COLOR_TEXT,
                           cx, 325)
            btn_label = "进入下一关" if self.win_next_available else "全部通关，返回首页"
            btn_w = 220 if self.win_next_available else 280
        else:
            self.draw_text("挑战失败", 44, COLOR_RED, cx, 270)
            self.draw_text("失误次数用完了，再试一次吧！", 24, COLOR_TEXT,
                           cx, 325)
            btn_label = "重新挑战"
            btn_w = 220
        self.result_rect = pygame.Rect(cx - btn_w // 2, 380, btn_w, 58)
        hovered = self.result_rect.collidepoint(self.mouse_pos)
        btn_color = (140, 240, 175) if hovered else COLOR_GREEN
        if not win:
            btn_color = (255, 140, 140) if hovered else COLOR_RED
        pygame.draw.rect(self.screen, btn_color, self.result_rect, border_radius=14)
        self.draw_text(btn_label, 24, (20, 30, 40),
                       self.result_rect.centerx, self.result_rect.centery)

    # ---------- 事件处理 ----------
    def cell_from_pos(self, pos):
        x, y = pos
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.cell_rect(r, c).collidepoint(x, y):
                    return r, c
        return None

    def handle_click(self, pos):
        x, y = pos
        if self.scene == "start":
            if self.start_rect.collidepoint(x, y):
                self.scene = "game"
                self.game = ArrowGame(0)
            return
        if self.scene == "game":
            # 重新开始按钮
            if hasattr(self, "restart_rect") and self.restart_rect.collidepoint(x, y):
                self.game.reset()
                return
            cell = self.cell_from_pos(pos)
            if cell:
                r, c = cell
                result = self.game.click(r, c)
                if result == "fly":
                    pass  # 动画在主循环里
                elif result == "collision":
                    pass  # 反馈已在逻辑里记录
                # 检查是否通关/失败，切换场景
                if self.game.status == "win":
                    self.win_next_available = (self.game.level_index + 1 < len(LEVEL_CONFIG))
                    self.scene = "win"
                elif self.game.status == "lose":
                    self.scene = "lose"
            return
        if self.scene in ("win", "lose"):
            if hasattr(self, "result_rect") and self.result_rect.collidepoint(x, y):
                if self.scene == "win" and self.win_next_available:
                    self.game.next_level()
                    self.scene = "game"
                elif self.scene == "lose":
                    self.game.reset()
                    self.scene = "game"
                else:
                    # 最后一关通关 -> 回到开始界面（或展示全部通关）
                    self.scene = "start"
            return

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                    if self.scene == "game":
                        self.hover_cell = self.cell_from_pos(event.pos)

            # 碰撞计时器递减
            if self.game.collision_timer > 0:
                self.game.collision_timer -= 1
                if self.game.collision_timer == 0:
                    self.game.last_collision = None

            # 绘制
            if self.scene == "start":
                self.draw_start()
            elif self.scene == "game":
                self.draw_game()
            elif self.scene == "win":
                self.draw_game()
                self.draw_result(win=True)
            elif self.scene == "lose":
                self.draw_game()
                self.draw_result(win=False)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit(0)


def _can_fly(g, r, c):
    """在给定网格 g 上，判断 (r,c) 的箭头是否可飞出（不修改网格）"""
    direction = g[r][c]
    if direction is None:
        return False
    dr, dc = DIRECTIONS[direction]
    nr, nc = r + dr, c + dc
    while 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
        if g[nr][nc] is not None:
            return False
        nr += dr
        nc += dc
    return True


def solve_level(grid, max_depth=20):
    """DFS 回溯求解器：枚举所有当前可飞的箭头，逐个尝试消除。
    返回: (是否可解, 消除顺序列表[(r,c)])
    比"有可飞就消"的贪心更严格，能发现需要特殊顺序的死局。
    """
    g = [row[:] for row in grid]

    def dfs(current, order):
        if all(cell is None for row in current for cell in row):
            return True, order
        if len(order) > max_depth:
            return False, order
        # 收集当前所有可飞的箭头
        candidates = [(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)
                      if current[r][c] is not None and _can_fly(current, r, c)]
        for r, c in candidates:
            saved = current[r][c]
            current[r][c] = None
            ok, result = dfs(current, order + [(r, c)])
            if ok:
                return True, result
            current[r][c] = saved  # 回溯
        return False, order

    return dfs(g, [])


if __name__ == "__main__":
    # 启动前抽查：对每个关卡配置多次随机生成，用 DFS 验证生成器确实产出可解棋盘
    print("正在验证随机关卡生成器...")
    all_ok = True
    for i, cfg in enumerate(LEVEL_CONFIG):
        ok_count = 0
        for trial in range(20):
            g = random_grid(cfg["arrows"])
            ok, order = solve_level(g)
            if ok:
                ok_count += 1
        print(f"  第 {i+1} 关（{cfg['arrows']} 箭头）: 20 次随机生成全部可解"
              if ok_count == 20 else f"  第 {i+1} 关: {ok_count}/20 可解 ⚠")
        all_ok = all_ok and ok_count == 20
    print("验证通过，开始游戏..." if all_ok else "存在不可解情况，请检查生成器！")
    App().run()
