"""
坦克大战 - Tank Battle (Pygame)
经典 FC 坦克大战复刻，支持无尽闯关、程序化地图、键盘操作
运行: pip install pygame && python tank_battle.py
"""
import pygame
import random
import math
from enum import IntEnum

# ===== Constants =====
CELL = 40
FPS = 60

class Dir(IntEnum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

class Tile(IntEnum):
    EMPTY = 0
    BRICK = 1
    STEEL = 2
    BASE = 3

DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]

# Colors
COLOR_BG = (10, 10, 10)
COLOR_GRID = (26, 26, 26)
COLOR_BRICK = (198, 122, 58)
COLOR_BRICK_DARK = (160, 82, 45)
COLOR_STEEL = (136, 136, 136)
COLOR_STEEL_LIGHT = (170, 170, 170)
COLOR_STEEL_DARK = (102, 102, 102)
COLOR_BASE = (233, 69, 96)
COLOR_BASE_STAR = (245, 197, 24)
COLOR_PLAYER = (74, 222, 128)
COLOR_ENEMY = (239, 68, 68)
COLOR_BULLET_PLAYER = (255, 255, 255)
COLOR_BULLET_ENEMY = (251, 191, 36)
COLOR_EXPLOSION_OUTER = (255, 180, 0)
COLOR_EXPLOSION_INNER = (255, 60, 0)
COLOR_OVERLAY = (0, 0, 0)
COLOR_UI_BG = (22, 33, 62)
COLOR_UI_BORDER = (15, 52, 96)
COLOR_UI_TEXT = (224, 224, 224)
COLOR_ACCENT = (233, 69, 96)
COLOR_GOLD = (245, 197, 24)
COLOR_GREEN = (74, 222, 128)
COLOR_DARK_BG = (26, 26, 46)
COLOR_DPAD = (42, 58, 94)
COLOR_DPAD_BORDER = (74, 106, 158)

# ===== Helper Functions =====
def get_map_size(wave):
    cols = min(13 + (wave - 1) // 3 * 2, 21)
    return cols, cols

def generate_map(wave, cols, rows):
    data = [Tile.EMPTY] * (cols * rows)
    reserved = set()
    cx, cy = cols // 2, rows - 1

    # Reserve spawn zones
    for sx, sy in [(0, 0), (cx, 0), (cols - 1, 0), (0, rows - 1), (cols - 1, rows - 1)]:
        for dy in range(2):
            for dx in range(-1, 2):
                ry, rx = sy + dy, sx + dx
                if 0 <= ry < rows and 0 <= rx < cols:
                    reserved.add(ry * cols + rx)

    # Reserve player spawn area
    for dy in range(-3, 1):
        for dx in range(-1, 2):
            ry, rx = cy + dy, cx + dx
            if 0 <= ry < rows and 0 <= rx < cols:
                reserved.add(ry * cols + rx)

    # Base every 3 waves
    if wave % 3 == 0:
        data[cy * cols + cx] = Tile.BASE
        reserved.add(cy * cols + cx)
        for gx, gy in [(cx - 1, cy), (cx, cy - 1), (cx + 1, cy)]:
            if 0 <= gx < cols and 0 <= gy < rows:
                data[gy * cols + gx] = Tile.BRICK
                reserved.add(gy * cols + gx)

    # Brick placement
    brick_prob = min(0.15 + wave * 0.03, 0.4)
    for y in range(1, rows - 1):
        for x in range(1, cols - 1):
            if (y * cols + x) in reserved:
                continue
            if random.random() < brick_prob:
                data[y * cols + x] = Tile.BRICK

    # Steel placement (wave 6+)
    if wave >= 6:
        steel_prob = min((wave - 5) * 0.02, 0.12)
        for y in range(2, rows - 2):
            for x in range(2, cols - 2):
                if (y * cols + x) in reserved:
                    continue
                if data[y * cols + x] == Tile.EMPTY and random.random() < steel_prob:
                    data[y * cols + x] = Tile.STEEL

    return data

# ===== Classes =====
class Tank:
    def __init__(self, x, y, direction=Dir.UP, color=COLOR_PLAYER):
        self.x = float(x)
        self.y = float(y)
        self.dir = direction
        self.color = color
        self.bullet_speed = 3
        self.active = True

    def draw(self, screen, cell):
        cx = self.x * cell + cell // 2
        cy = self.y * cell + cell // 2
        # Rotate based on direction
        angle = -self.dir * 90
        tank_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(tank_surf, self.color, (2, 4, 36, 32))
        # Treads
        pygame.draw.rect(tank_surf, (51, 51, 51), (0, 2, 6, 36))
        pygame.draw.rect(tank_surf, (51, 51, 51), (34, 2, 6, 36))
        # Track marks
        for i in range(4, 36, 8):
            pygame.draw.line(tank_surf, (85, 85, 85), (2, i), (6, i), 2)
            pygame.draw.line(tank_surf, (85, 85, 85), (34, i), (38, i), 2)
        # Barrel
        pygame.draw.rect(tank_surf, (221, 221, 221), (17, -2, 6, 14))
        rotated = pygame.transform.rotate(tank_surf, angle)
        screen.blit(rotated, (cx - rotated.get_width() // 2, cy - rotated.get_height() // 2))

    def can_move(self, nx, ny, game_map, cols, rows, tanks, exclude):
        if nx < 0 or ny < 0 or nx >= cols or ny >= rows:
            return False
        return game_map[ny][nx] == Tile.EMPTY and not tank_at(nx, ny, tanks, exclude)

    def try_move(self, game_map, cols, rows, tanks):
        nx = self.x + DX[self.dir]
        ny = self.y + DY[self.dir]
        if self.can_move(int(nx), int(ny), game_map, cols, rows, tanks, self):
            self.x = nx
            self.y = ny
            return True
        return False

    def shoot(self, bullets, is_player):
        bx = self.x + DX[self.dir] * 0.6
        by = self.y + DY[self.dir] * 0.6
        bullets.append(Bullet(bx, by, self.dir, self.bullet_speed, is_player))


class Enemy(Tank):
    def __init__(self, x, y):
        super().__init__(x, y, Dir.DOWN, COLOR_ENEMY)
        self.move_timer = 0
        self.shoot_timer = 0
        self.dir_change_timer = random.randint(50, 130)

    def update(self, player, game_map, cols, rows, bullets, tanks, enemies):
        if not self.active:
            return
        self.dir_change_timer -= 1
        self.move_timer -= 1

        if self.dir_change_timer <= 0:
            r = random.random()
            if r < 0.3:
                self.dir = random.choice(list(Dir))
            elif r < 0.6 and random.random() > 0.5:
                dx = player.x - self.x
                dy = player.y - self.y
                self.dir = Dir.RIGHT if abs(dx) > abs(dy) and dx > 0 else \
                            Dir.LEFT if abs(dx) > abs(dy) else \
                            Dir.DOWN if dy > 0 else Dir.UP
            self.dir_change_timer = random.randint(40, 100)

        if self.move_timer <= 0:
            if not self.try_move(game_map, cols, rows, tanks):
                self.dir = random.choice(list(Dir))
            self.move_timer = random.randint(25, 50)

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            dx = player.x - self.x
            dy = player.y - self.y
            aligned = (
                (self.dir == Dir.UP and dy < 0 and abs(dx) < 1.5) or
                (self.dir == Dir.DOWN and dy > 0 and abs(dx) < 1.5) or
                (self.dir == Dir.LEFT and dx < 0 and abs(dy) < 1.5) or
                (self.dir == Dir.RIGHT and dx > 0 and abs(dy) < 1.5)
            )
            if aligned or random.random() < 0.02:
                self.shoot(bullets, False)
            self.shoot_timer = random.randint(80, 220)


class Bullet:
    def __init__(self, x, y, direction, speed, from_player):
        self.x = x
        self.y = y
        self.dir = direction
        self.speed = speed
        self.from_player = from_player
        self.active = True

    def update(self, game_map, cols, rows, player, enemies, explosions):
        self.x += DX[self.dir] * self.speed * 0.06
        self.y += DY[self.dir] * self.speed * 0.06
        cx, cy = round(self.x), round(self.y)

        if cx < 0 or cy < 0 or cx >= cols or cy >= rows:
            self.active = False
            return

        tile = game_map[cy][cx]

        if tile == Tile.STEEL:
            self.active = False
            explosions.append(Explosion(cx, cy))
        elif tile == Tile.BRICK:
            self.active = False
            game_map[cy][cx] = Tile.EMPTY
            explosions.append(Explosion(cx, cy))
        elif tile == Tile.BASE:
            self.active = False
            game_map[cy][cx] = Tile.EMPTY
            explosions.append(Explosion(cx, cy))
        elif not self.from_player and player.active:
            if abs(self.x - player.x) < 0.7 and abs(self.y - player.y) < 0.7:
                self.active = False
                return 'player_hit'
        elif self.from_player:
            for e in enemies:
                if e.active and abs(self.x - e.x) < 0.7 and abs(self.y - e.y) < 0.7:
                    self.active = False
                    e.active = False
                    explosions.append(Explosion(e.x, e.y))
                    return 'enemy_kill'

    def draw(self, screen, cell):
        color = COLOR_BULLET_PLAYER if self.from_player else COLOR_BULLET_ENEMY
        cx = self.x * cell + cell // 2
        cy = self.y * cell + cell // 2
        pygame.draw.circle(screen, color, (int(cx), int(cy)), 3)


class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.life = 15

    def draw(self, screen, cell):
        cx = self.x * cell + cell // 2
        cy = self.y * cell + cell // 2
        alpha_outer = int(self.life / 15 * 255)
        alpha_inner = int(self.life / 15 * 255)
        r = (15 - self.life) * 2 + 10

        outer = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(outer, (*COLOR_EXPLOSION_OUTER, alpha_outer), (r, r), r)
        screen.blit(outer, (cx - r, cy - r))

        inner = pygame.Surface((int(r * 1.2), int(r * 1.2)), pygame.SRCALPHA)
        pygame.draw.circle(inner, (*COLOR_EXPLOSION_INNER, alpha_inner), (int(r * 0.6), int(r * 0.6)), int(r * 0.6))
        screen.blit(inner, (cx - r * 0.6, cy - r * 0.6))

    def update(self):
        self.life -= 1
        return self.life > 0


def tank_at(x, y, tanks, exclude=None):
    for t in tanks:
        if t.active and t is not exclude and int(t.x) == int(x) and int(t.y) == int(y):
            return t
    return None


# ===== Game Class =====
class Game:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 40)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.screen = None
        self.running = True
        self.reset()

    def reset(self):
        self.wave = 1
        self.score = 0
        self.lives = 3
        self.kills = 0
        self.game_over = False
        self.game_won = False
        self.paused = False
        self.spawning = False
        self.game_started = False
        self.invincible_timer = 0
        self.shoot_cooldown = 0
        self.move_cooldown = 0
        self.enemies = []
        self.bullets = []
        self.explosions = []
        self.keys = set()
        self.pending_timers = []
        self.set_map_size(1)
        self.screen = pygame.display.set_mode((self.cols * CELL, self.rows * CELL))
        pygame.display.set_caption("坦克大战 - Tank Battle")
        self.game_map = self.load_map(generate_map(1, self.cols, self.rows))
        self.player = Tank(self.cols // 2, self.get_spawn_y(), Dir.UP, COLOR_PLAYER)

    def set_map_size(self, wave):
        self.cols, self.rows = get_map_size(wave)

    def get_spawn_y(self):
        cx = self.cols // 2
        y = self.rows - 1
        while y > 0 and self.game_map and len(self.game_map) > y and self.game_map[y][cx] != Tile.EMPTY:
            y -= 1
        return y

    def load_map(self, data):
        game_map = []
        for y in range(self.rows):
            row = []
            for x in range(self.cols):
                row.append(data[y * self.cols + x])
            game_map.append(row)
        return game_map

    def spawn_enemies(self):
        cx = self.cols // 2
        spawns = [(0, 0), (cx, 0), (self.cols - 1, 0), (0, self.rows - 1), (self.cols - 1, self.rows - 1)]
        count = min(3 + self.wave, 6)
        all_tanks = [self.player] + self.enemies
        for i in range(count):
            sp = spawns[i % len(spawns)]
            e = Enemy(sp[0], sp[1])
            if tank_at(e.x, e.y, all_tanks) or self.game_map[int(e.y)][int(e.x)] != Tile.EMPTY:
                placed = False
                for y in range(min(3, self.rows)):
                    for x in range(self.cols):
                        if self.game_map[y][x] == Tile.EMPTY and not tank_at(x, y, all_tanks):
                            e.x, e.y = float(x), float(y)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    continue
            self.enemies.append(e)

    def next_wave(self):
        if self.spawning:
            return
        self.spawning = True
        self.wave += 1
        self.score += 200
        self.lives += 3
        self.set_map_size(self.wave)
        self.game_map = self.load_map(generate_map(self.wave, self.cols, self.rows))
        sp_x, sp_y = self.cols // 2, self.get_spawn_y()
        self.player.x, self.player.y = float(sp_x), float(sp_y)
        self.bullets.clear()
        self.invincible_timer = 180
        self.screen = pygame.display.set_mode((self.cols * CELL, self.rows * CELL))
        pygame.time.set_timer(pygame.USEREVENT, 1000, True)

    def player_hit(self):
        if not self.player.active:
            return
        self.player.active = False
        self.explosions.append(Explosion(self.player.x, self.player.y))
        self.lives -= 1
        if self.lives <= 0:
            pygame.time.set_timer(pygame.USEREVENT + 1, 500, True)
        else:
            pygame.time.set_timer(pygame.USEREVENT + 2, 800, True)

    def respawn_player(self):
        self.player.x = float(self.cols // 2)
        self.player.y = float(self.get_spawn_y())
        self.player.dir = Dir.UP
        self.player.active = True
        self.invincible_timer = 180

    def end_game(self, won):
        self.game_over = True
        self.game_won = won
        self.game_started = False
        self.player.active = False
        for e in self.enemies:
            e.active = False

    def start_game(self):
        # Clear pending timers
        for _ in range(10):
            pygame.time.set_timer(pygame.USEREVENT, 0)
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
        self.reset()
        self.game_started = True
        self.invincible_timer = 180
        self.spawn_enemies()

    def update(self):
        if not self.game_started or self.game_over or self.paused:
            return

        # Player movement
        if self.player.active:
            if self.invincible_timer > 0:
                self.invincible_timer -= 1
            self.move_cooldown -= 1
            if self.move_cooldown <= 0:
                all_tanks = [self.player] + self.enemies
                moved = False
                if pygame.K_w in self.keys or pygame.K_UP in self.keys:
                    self.player.dir = Dir.UP
                    moved = self.player.try_move(self.game_map, self.cols, self.rows, all_tanks)
                elif pygame.K_s in self.keys or pygame.K_DOWN in self.keys:
                    self.player.dir = Dir.DOWN
                    moved = self.player.try_move(self.game_map, self.cols, self.rows, all_tanks)
                elif pygame.K_a in self.keys or pygame.K_LEFT in self.keys:
                    self.player.dir = Dir.LEFT
                    moved = self.player.try_move(self.game_map, self.cols, self.rows, all_tanks)
                elif pygame.K_d in self.keys or pygame.K_RIGHT in self.keys:
                    self.player.dir = Dir.RIGHT
                    moved = self.player.try_move(self.game_map, self.cols, self.rows, all_tanks)
                if moved:
                    self.move_cooldown = 12

            self.shoot_cooldown -= 1
            if (pygame.K_k in self.keys or pygame.K_SPACE in self.keys) and self.shoot_cooldown <= 0:
                self.player.shoot(self.bullets, True)
                self.shoot_cooldown = 30

        # Update enemies
        all_tanks = [self.player] + self.enemies
        for e in self.enemies:
            e.update(self.player, self.game_map, self.cols, self.rows, self.bullets, all_tanks, self.enemies)

        # Update bullets
        for b in self.bullets[:]:
            if not b.active:
                continue
            result = b.update(self.game_map, self.cols, self.rows, self.player, self.enemies, self.explosions)
            if result == 'player_hit':
                if self.invincible_timer <= 0:
                    self.player_hit()
            elif result == 'enemy_kill':
                self.kills += 1
                self.score += 100

        # Cleanup
        self.bullets = [b for b in self.bullets if b.active]
        self.enemies = [e for e in self.enemies if e.active]

        # Wave clear check
        if len(self.enemies) == 0 and not self.game_over and self.player.active and not self.spawning:
            self.next_wave()

        # Update explosions
        self.explosions = [ex for ex in self.explosions if ex.update()]

    def draw_map(self):
        for y in range(self.rows):
            for x in range(self.cols):
                px, py = x * CELL, y * CELL
                tile = self.game_map[y][x]
                if tile == Tile.BRICK:
                    pygame.draw.rect(self.screen, COLOR_BRICK, (px, py, CELL, CELL))
                    half = CELL // 2 - 2
                    pygame.draw.rect(self.screen, COLOR_BRICK_DARK, (px + 2, py + 2, half, half))
                    pygame.draw.rect(self.screen, COLOR_BRICK_DARK, (px + CELL // 2, py + CELL // 2, half, half))
                    pygame.draw.rect(self.screen, (139, 69, 19), (px, py, CELL, CELL), 1)
                elif tile == Tile.STEEL:
                    pygame.draw.rect(self.screen, COLOR_STEEL, (px, py, CELL, CELL))
                    pygame.draw.rect(self.screen, COLOR_STEEL_LIGHT, (px + 3, py + 3, CELL - 6, CELL - 6))
                    pygame.draw.rect(self.screen, COLOR_STEEL_DARK, (px + 5, py + 5, CELL - 10, CELL - 10))
                elif tile == Tile.BASE:
                    pygame.draw.rect(self.screen, COLOR_BASE, (px, py, CELL, CELL))
                    cx, cy = px + CELL // 2, py + CELL // 2
                    points = []
                    for i in range(5):
                        a = i * 4 * math.pi / 5 - math.pi / 2
                        r = CELL / 3
                        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
                    pygame.draw.polygon(self.screen, COLOR_BASE_STAR, points)

        # Grid lines
        for x in range(self.cols + 1):
            pygame.draw.line(self.screen, COLOR_GRID, (x * CELL, 0), (x * CELL, self.rows * CELL))
        for y in range(self.rows + 1):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y * CELL), (self.cols * CELL, y * CELL))

    def draw_ui(self):
        w, h = self.screen.get_width(), self.screen.get_height()
        # Stats bar
        bar_h = 30
        pygame.draw.rect(self.screen, COLOR_DARK_BG, (0, h - bar_h, w, bar_h))
        texts = [
            f"Score: {self.score}",
            f"Lives: {self.lives}",
            f"Kills: {self.kills}",
            f"Wave: {self.wave}"
        ]
        spacing = w // len(texts)
        for i, txt in enumerate(texts):
            surf = self.font_small.render(txt, True, COLOR_GOLD)
            self.screen.blit(surf, (i * spacing + 10, h - bar_h + 5))

    def draw_overlay(self, title, subtitle, title_color=COLOR_ACCENT):
        w, h = self.screen.get_width(), self.screen.get_height()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        t = self.font_large.render(title, True, title_color)
        self.screen.blit(t, (w // 2 - t.get_width() // 2, h // 2 - 40))
        s = self.font_small.render(subtitle, True, COLOR_UI_TEXT)
        self.screen.blit(s, (w // 2 - s.get_width() // 2, h // 2 + 10))

    def draw(self):
        self.screen.fill(COLOR_BG)
        self.draw_map()

        # Base flag
        bcx = self.cols // 2
        if self.game_map[self.rows - 1][bcx] != Tile.BASE:
            flag_surf = self.font_medium.render("★", True, COLOR_BASE_STAR)
            self.screen.blit(flag_surf, (bcx * CELL + CELL // 2 - flag_surf.get_width() // 2,
                                         (self.rows - 1) * CELL + CELL // 2 - 10))

        # Draw tanks (player blinks when invincible)
        if self.player.active:
            if self.invincible_timer > 0 and (self.invincible_timer // 8) % 2 == 0:
                s = pygame.Surface((40, 40), pygame.SRCALPHA)
                s.set_alpha(76)
                self.player.draw(self.screen, CELL)
            else:
                self.player.draw(self.screen, CELL)

        for e in self.enemies:
            if e.active:
                e.draw(self.screen, CELL)

        for b in self.bullets:
            if b.active:
                b.draw(self.screen, CELL)

        for ex in self.explosions:
            ex.draw(self.screen, CELL)

        # Overlays
        if self.paused and not self.game_over:
            self.draw_overlay("PAUSED", "Press P to continue", COLOR_GOLD)
        elif self.game_over:
            title = "YOU WIN!" if self.game_won else "GAME OVER"
            color = COLOR_GREEN if self.game_won else COLOR_ACCENT
            self.draw_overlay(title, "Press R to restart", color)
        elif not self.game_started:
            w, h = self.screen.get_width(), self.screen.get_height()
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))
            t1 = self.font_large.render("TANK BATTLE", True, COLOR_ACCENT)
            self.screen.blit(t1, (w // 2 - t1.get_width() // 2, h // 2 - 60))
            t2 = self.font_small.render("Classic FC Tank Battle", True, (136, 136, 136))
            self.screen.blit(t2, (w // 2 - t2.get_width() // 2, h // 2 - 15))
            t3 = self.font_medium.render("Press ENTER to Start", True, COLOR_GREEN)
            self.screen.blit(t3, (w // 2 - t3.get_width() // 2, h // 2 + 30))
            t4 = self.font_small.render("WASD Move  |  K Shoot  |  P Pause", True, (136, 136, 136))
            self.screen.blit(t4, (w // 2 - t4.get_width() // 2, h // 2 + 65))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.keys.add(event.key)
                    if event.key == pygame.K_p:
                        if self.game_started and not self.game_over:
                            self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.start_game()
                    elif event.key == pygame.K_RETURN:
                        if not self.game_started:
                            self.start_game()
                elif event.type == pygame.KEYUP:
                    self.keys.discard(event.key)
                elif event.type == pygame.USEREVENT:
                    self.spawning = False
                    self.spawn_enemies()
                elif event.type == pygame.USEREVENT + 1:
                    self.end_game(False)
                elif event.type == pygame.USEREVENT + 2:
                    self.respawn_player()

            self.update()
            self.draw()

        pygame.quit()


if __name__ == '__main__':
    Game().run()
