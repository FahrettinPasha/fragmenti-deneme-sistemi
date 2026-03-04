"""
FRAGMENTIA - Infinite Side-Scroller PROTOTYPE
=============================================
AGENT.MD Uyumlu:
  - Rule of Time: frame_mul = dt * 60.0
  - GC: disable() oyun baslarken, collect() load'da
  - Z-Layer sirasi korundu (0..UI)
  - Kamera: LERP X tracking (cap=0.22)
  - Nesne havuzu: Ground chunks pool ile yonetilir
  - DEBUG: F12 ile toggle edilebilir log
"""

import pygame
import sys
import math
import gc

# ─────────────────────────────────────────
# SETTINGS  (settings.py karşılığı)
# ─────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
FPS               = 60
CAPTION           = "FRAGMENTIA – Runner Prototype"

# Karakter
PLAYER_W, PLAYER_H = 32, 52
PLAYER_SPEED       = 280.0          # px/s
JUMP_FORCE         = -620.0         # px/s  (negatif = yukarı)
GRAVITY            = 1400.0         # px/s²

# Zemin
GROUND_Y           = SCREEN_H - 80  # zemin üst kenarı (world space)
GROUND_H           = 80
CHUNK_W            = 400            # her chunk genişliği

# Kamera
CAM_LERP           = 0.12           # 0..1  (düşük = daha yumuşak)
CAM_TARGET_X_RATIO = 0.35           # ekranın %35'inde tut

# Renkler  (settings.py -> COLOR_*  eşdeğeri)
C_BG          = (10,  10,  22)
C_STARS       = (200, 200, 230)
C_GROUND_TOP  = (40,  200, 120)
C_GROUND_BODY = (25,  90,  55)
C_PLAYER      = (80,  180, 255)
C_PLAYER_EYE  = (255, 255, 255)
C_UI_TEXT     = (220, 220, 220)
C_DEBUG       = (255, 200,  50)

# ─────────────────────────────────────────
# GC YÖNETİMİ  (AGENT.MD Kural 2)
# ─────────────────────────────────────────
gc.collect()   # loading aşaması: temizle
gc.disable()   # oyun döngüsünde GC yok

# ─────────────────────────────────────────
# PYGAME BAŞLATMA
# ─────────────────────────────────────────
pygame.init()
screen       = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption(CAPTION)
clock        = pygame.time.Clock()
font_sm      = pygame.font.SysFont("consolas", 16)
font_md      = pygame.font.SysFont("consolas", 22, bold=True)

# ─────────────────────────────────────────
# STAR POOL  (Z-2 için 120 adet, sabit list)
# ─────────────────────────────────────────
import random
random.seed(42)
STAR_POOL = [(random.randint(0, SCREEN_W * 4),
              random.randint(0, SCREEN_H - 120),
              random.choice([1, 1, 2])) for _ in range(120)]

# ─────────────────────────────────────────
# GROUND CHUNK SİSTEMİ
# (Oyun içinde list[] tahsisi yok — chunk pool döngüsel)
# ─────────────────────────────────────────
POOL_SIZE = 8   # ekranda max görünecek chunk sayısı

class GroundChunk:
    """Tek zemin parçası. Pool'dan geri dönüştürülür."""
    __slots__ = ("world_x", "active")

    def __init__(self, world_x: float):
        self.world_x = world_x
        self.active  = True

    def recycle(self, new_x: float):
        self.world_x = new_x
        self.active  = True

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.world_x), GROUND_Y, CHUNK_W + 1, GROUND_H)


class GroundSystem:
    """
    Pool tabanlı sonsuz zemin yöneticisi.
    Oyun döngüsünde yeni nesne yaratılmaz.
    """
    def __init__(self):
        # Başlangıç: ekranı dolduracak kadar chunk  (pool sabit, hiç büyümez)
        self.chunks: list[GroundChunk] = []
        start = -(CHUNK_W)
        for i in range(POOL_SIZE):
            self.chunks.append(GroundChunk(start + i * CHUNK_W))
        self._rightmost_x = start + (POOL_SIZE - 1) * CHUNK_W

    def update(self, camera_x: float):
        """Kameranın sağına geçen chunk'ları soldan geri dönüştür."""
        cam_right = camera_x + SCREEN_W + CHUNK_W

        for ch in self.chunks:
            if ch.world_x + CHUNK_W < camera_x - CHUNK_W:
                # Chunk ekran solunun gerisinde kaldı → recycle
                self._rightmost_x += CHUNK_W
                ch.recycle(self._rightmost_x)

    def get_ground_top_y(self) -> int:
        return GROUND_Y

    def draw(self, surface: pygame.Surface, camera_x: float):
        for ch in self.chunks:
            sx = int(ch.world_x - camera_x)
            if sx > SCREEN_W + CHUNK_W or sx < -CHUNK_W:
                continue
            r = pygame.Rect(sx, GROUND_Y, CHUNK_W + 1, GROUND_H)
            # Zemin gövde
            pygame.draw.rect(surface, C_GROUND_BODY, r)
            # Üst çizgi (toprak kenarı)
            pygame.draw.rect(surface, C_GROUND_TOP,
                             pygame.Rect(sx, GROUND_Y, CHUNK_W + 1, 6))
            # Chunk sınır çizgisi (görsel referans)
            pygame.draw.line(surface, (30, 70, 45),
                             (sx, GROUND_Y), (sx, SCREEN_H), 1)

# ─────────────────────────────────────────
# PLAYER
# ─────────────────────────────────────────
class Player:
    """
    Kamera takibi için world-space koordinatlarla yaşar.
    Framerate-independent: tüm fizik frame_mul ile ölçeklenir.
    """
    __slots__ = (
        "world_x", "world_y", "vx", "vy",
        "on_ground", "facing", "anim_tick",
        "squash", "stretch"
    )

    def __init__(self):
        self.world_x   = 200.0
        self.world_y   = float(GROUND_Y - PLAYER_H)
        self.vx        = 0.0
        self.vy        = 0.0
        self.on_ground = False
        self.facing    = 1       # +1 sağ, -1 sol
        self.anim_tick = 0.0
        self.squash    = 1.0    #착지 ezilme (squash & stretch)
        self.stretch   = 1.0

    def update(self, dt: float, ground_y: int, keys):
        frame_mul = dt * 60.0   # AGENT.MD Kural 1

        # ── Yatay hareket
        self.vx = 0.0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vx   = -PLAYER_SPEED
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx   =  PLAYER_SPEED
            self.facing = 1

        # ── Zıplama
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) \
                and self.on_ground:
            self.vy        = JUMP_FORCE
            self.on_ground = False
            self.stretch   = 1.35   # zıplarken uzama

        # ── Yerçekimi  (frame_mul ile)
        self.vy += GRAVITY * dt

        # ── Pozisyon güncelle
        self.world_x += self.vx * dt
        self.world_y += self.vy * dt

        # ── Zemin çarpışması (basit AABB)
        foot_y = self.world_y + PLAYER_H
        if foot_y >= ground_y:
            self.world_y   = float(ground_y - PLAYER_H)
            if self.vy > 200:
                self.squash  = 0.72   # iniş ezilmesi
                self.stretch = 1.0
            self.vy        = 0.0
            self.on_ground = True
        else:
            self.on_ground = False

        # ── Sol sınır (dünya başlangıcı)
        if self.world_x < 0:
            self.world_x = 0.0

        # ── Squash/Stretch toparlanma
        self.squash  += (1.0 - self.squash)  * min(1.0, dt * 12)
        self.stretch += (1.0 - self.stretch) * min(1.0, dt * 12)

        # ── Yürüme animasyon tik
        if self.on_ground and self.vx != 0:
            self.anim_tick += dt * 8
        else:
            self.anim_tick = 0.0

    def draw(self, surface: pygame.Surface, camera_x: float):
        """Z-7: Oyuncu çizimi — squash/stretch + yüz yönü"""
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)

        # Squash/stretch deformasyonu
        draw_w = int(PLAYER_W  * self.squash)
        draw_h = int(PLAYER_H  * self.stretch)
        draw_x = sx + (PLAYER_W - draw_w) // 2
        draw_y = sy + (PLAYER_H - draw_h)

        body = pygame.Rect(draw_x, draw_y, draw_w, draw_h)

        # Gövde
        pygame.draw.rect(surface, C_PLAYER, body, border_radius=6)

        # Yürüme: hafif tik-tak eğim (bacak taklidi)
        leg_offset = int(math.sin(self.anim_tick) * 4)
        pygame.draw.line(surface, (60, 140, 210),
                         (sx + 8,  sy + PLAYER_H - 10),
                         (sx + 8,  sy + PLAYER_H + 8 + leg_offset), 3)
        pygame.draw.line(surface, (60, 140, 210),
                         (sx + PLAYER_W - 8, sy + PLAYER_H - 10),
                         (sx + PLAYER_W - 8, sy + PLAYER_H + 8 - leg_offset), 3)

        # Göz (yüz yönüne göre)
        eye_x = sx + (PLAYER_W // 2) + self.facing * 7
        pygame.draw.circle(surface, C_PLAYER_EYE,
                           (eye_x, draw_y + 14), 5)
        pygame.draw.circle(surface, (30, 30, 80),
                           (eye_x + self.facing * 2, draw_y + 14), 2)

# ─────────────────────────────────────────
# KAMERA
# (AGENT.MD Bölüm 4 – LERP X tracking)
# ─────────────────────────────────────────
class Camera:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 0.0

    def update(self, target_world_x: float, dt: float):
        """
        Oyuncu ekranın CAM_TARGET_X_RATIO noktasında tutulur.
        LERP: yumuşak kayma, drift engeli.
        """
        desired_x = target_world_x - SCREEN_W * CAM_TARGET_X_RATIO
        desired_x = max(0.0, desired_x)
        self.x   += (desired_x - self.x) * min(1.0, CAM_LERP * dt * 60)

# ─────────────────────────────────────────
# PARALLAX ARKAPLAN (Z-1)
# ─────────────────────────────────────────
def draw_parallax_bg(surface: pygame.Surface, camera_x: float):
    """
    İki kopya yan yana → infinite loop.
    Uzak şehir silueti (placeholder polygon).
    """
    BUILDING_DATA = [
        (0,   160, 60,  260),
        (80,  200, 45,  220),
        (150, 120, 80,  280),
        (260, 180, 55,  240),
        (340, 100, 70,  300),
        (440, 210, 50,  210),
        (520, 140, 90,  260),
        (640, 170, 65,  230),
        (730, 90,  75,  310),
        (840, 200, 55,  220),
        (920, 130, 80,  270),
    ]
    TILE_W = 1000   # tekrarlama periyodu

    speed_mult = 0.25   # parallax katsayısı
    offset = (camera_x * speed_mult) % TILE_W

    for tile in range(2):
        base_x = tile * TILE_W - offset
        for (bx, by, bw, bh) in BUILDING_DATA:
            sx = int(base_x + bx)
            pygame.draw.rect(surface, (20, 20, 45),
                             pygame.Rect(sx, SCREEN_H - bh, bw, bh))
            # pencereler
            for wy in range(SCREEN_H - bh + 10, SCREEN_H - 20, 22):
                for wx in range(sx + 6, sx + bw - 6, 14):
                    c = (50, 50, 100) if (wx + wy) % 3 == 0 else (90, 180, 90)
                    pygame.draw.rect(surface, c, pygame.Rect(wx, wy, 6, 8))

# ─────────────────────────────────────────
# YILDIZLAR (Z-2, parallax yok — uzak)
# ─────────────────────────────────────────
def draw_stars(surface: pygame.Surface, camera_x: float):
    star_parallax = 0.05
    for (sx, sy, sr) in STAR_POOL:
        draw_x = int((sx - camera_x * star_parallax) % (SCREEN_W + 100))
        pygame.draw.circle(surface, C_STARS, (draw_x, sy), sr)

# ─────────────────────────────────────────
# UI (Z-UI)
# ─────────────────────────────────────────
_ui_cache: pygame.Surface | None = None
_ui_frame_counter = 0

def render_ui(surface: pygame.Surface, player_world_x: float,
              fps: float, debug: bool):
    global _ui_cache, _ui_frame_counter
    _ui_frame_counter += 1

    # Her 10 frame'de bir yeniden render (AGENT.MD cached_ui_surface)
    if _ui_cache is None or _ui_frame_counter % 10 == 0:
        _ui_cache = pygame.Surface((SCREEN_W, 60), pygame.SRCALPHA)
        dist_text = f"MESAFE: {int(player_world_x / 100):,} m"
        fps_text  = f"FPS: {fps:.0f}"
        s1 = font_md.render(dist_text, True, C_UI_TEXT)
        s2 = font_sm.render(fps_text,  True, C_UI_TEXT)
        _ui_cache.blit(s1, (20, 10))
        _ui_cache.blit(s2, (20, 38))

    surface.blit(_ui_cache, (0, 0))

    if debug:
        lines = [
            f"[DEBUG F12]",
            f"  player.world_x : {player_world_x:.1f}",
            f"  cam.x          : camX",
        ]
        for i, ln in enumerate(lines):
            s = font_sm.render(ln, True, C_DEBUG)
            surface.blit(s, (SCREEN_W - 280, 10 + i * 20))

# ─────────────────────────────────────────
# ANA DÖNGÜ
# ─────────────────────────────────────────
def main():
    player  = Player()
    camera  = Camera()
    ground  = GroundSystem()
    debug   = False

    # Kamera başlangıç pozisyonu
    camera.x = 0.0

    print("[PROTOTYPE] Başladı. F12 = debug | ESC = çıkış")
    print("[PROTOTYPE] Kontroller: A/D veya Sol/Sağ ok | W/Space/Yukarı = zıpla")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)   # spike önlemi

        # ── EVENTS ──────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_F12:
                    debug = not debug
                    print(f"[DEBUG] {'AÇIK' if debug else 'KAPALI'}")

        keys = pygame.key.get_pressed()

        # ── UPDATE ──────────────────────────────
        ground.update(camera.x)
        player.update(dt, ground.get_ground_top_y(), keys)
        camera.update(player.world_x, dt)

        # ── RENDER ──────────────────────────────
        # Z-0: Arka plan temizle
        screen.fill(C_BG)

        # Z-1: Parallax şehir silueti
        draw_parallax_bg(screen, camera.x)

        # Z-2: Yıldızlar
        draw_stars(screen, camera.x)

        # Z-4: Zemin / platform
        ground.draw(screen, camera.x)

        # Z-7: Oyuncu
        player.draw(screen, camera.x)

        # Z-UI: HUD
        render_ui(screen, player.world_x,
                  clock.get_fps(), debug)

        pygame.display.flip()

    # ── KAPAT ────────────────────────────────
    gc.enable()
    gc.collect()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()