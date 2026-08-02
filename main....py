"""
================================================================================
 ZOMBIE SURVIVAL - a complete 2D top-down survival shooter built with Pygame
================================================================================

HOW TO RUN
----------
    python main.py

Requires only the "pygame" package (works with Pydroid 3 on Android -
install "pygame" from the Pydroid 3 Pip menu, then open and run this file).
Also compatible with APK builds using Buildozer.

CONTROLS
--------
    Move          : W A S D  or  Arrow Keys
    Aim           : Mouse
    Shoot         : Hold Left Mouse Button
    Reload        : R
    Pause         : ESC or P

ASSET FOLDERS (all optional - the game runs perfectly with built-in
shapes/colors and silence if these files are missing, so you can add your
own art/audio at any time without changing a single line of code)
--------------------------------------------------------------------
Place files next to this main.py script using this exact folder layout:

    your_game_folder/
    │
    ├── main.py                     <- this file
    │
    └── assets/
        ├── gun.wav                 <- fired every time the player shoots
        ├── zombie.wav              <- zombie attack AND zombie death
        ├── footsteps.wav           <- loops while the player is moving
        ├── reload.wav              <- played when reload starts
        ├── explosion.wav           <- played when the boss zombie dies
        ├── gameover.wav            <- played once when the player dies
        ├── victory.wav             <- played once when the player wins
        ├── bg_music.mp3            <- looping background music
        │
        └── images/
            ├── player.png          <- top-down player sprite (facing right)
            ├── zombie_normal.png
            ├── zombie_fast.png
            ├── zombie_tank.png
            ├── zombie_boss.png
            ├── bullet.png
            ├── icon.png            <- window icon
            └── background.png

If a file is missing, the game silently falls back to simple colored
shapes (for images) or silence (for sounds) - nothing will crash.

Your progress (high score) is saved automatically to "highscore.json"
in the same folder as this script.
================================================================================
"""

import os
import sys
import json
import math
import random

import pygame

# --------------------------------------------------------------------------
# CONSTANTS
# --------------------------------------------------------------------------

WIDTH, HEIGHT = 960, 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
RED = (220, 30, 30)
DARK_RED = (150, 0, 0)
GREEN = (80, 200, 80)
BLUE = (70, 130, 220)
YELLOW = (230, 210, 40)
ORANGE = (255, 140, 0)
GRAY = (60, 60, 60)
DARK_GRAY = (35, 35, 40)
PURPLE = (140, 80, 170)

STATE_MENU = "MENU"
STATE_SETTINGS = "SETTINGS"
STATE_PLAYING = "PLAYING"
STATE_PAUSED = "PAUSED"
STATE_GAMEOVER = "GAMEOVER"
STATE_VICTORY = "VICTORY"

# Survive this many waves to trigger the victory state / victory.wav
WIN_WAVE = 10


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


# --------------------------------------------------------------------------
# ASSET MANAGER  (images + full sound system)
# --------------------------------------------------------------------------

class AssetManager:
    """Loads images/sounds if present, otherwise fails gracefully so the
    game can always run using built-in shapes and silence."""

    IMAGE_NAMES = [
        "player.png",
        "zombie_normal.png",
        "zombie_fast.png",
        "zombie_tank.png",
        "zombie_boss.png",
        "bullet.png",
        "icon.png",
        "background.png",
    ]

    # key -> filename directly under the "assets/" folder
    SOUND_FILES = {
        "gun": "gun.wav",
        "zombie": "zombie.wav",
        "footsteps": "footsteps.wav",
        "reload": "reload.wav",
        "explosion": "explosion.wav",
        "gameover": "gameover.wav",
        "victory": "victory.wav",
    }

    MUSIC_FILE = "bg_music.mp3"

    def __init__(self, mixer_ok):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")
        self.img_dir = os.path.join(self.assets_dir, "images")

        self.mixer_ok = mixer_ok

        self.images = {}
        self.sounds = {}
        self.music_path = None

        # volume settings (0.0 - 1.0)
        self.sfx_volume = 0.6

        # dedicated channel for looping footstep audio so it never
        # collides with one-shot sound effects
        self.footsteps_channel = None
        self._footsteps_playing = False

        self._load_images()
        self._load_sounds()
        self._load_music()
        self._setup_footsteps_channel()

    # ---------------------------------------------------------- images ----

    def _load_images(self):
        for name in self.IMAGE_NAMES:
            path = os.path.join(self.img_dir, name)
            try:
                img = pygame.image.load(path).convert_alpha()
                self.images[name] = img
            except Exception:
                self.images[name] = None

    # ---------------------------------------------------------- sounds ----

    def _load_sounds(self):
        for key, filename in self.SOUND_FILES.items():
            path = os.path.join(self.assets_dir, filename)
            snd = None
            if self.mixer_ok:
                try:
                    snd = pygame.mixer.Sound(path)
                except Exception:
                    snd = None
            self.sounds[key] = snd

    def _load_music(self):
        path = os.path.join(self.assets_dir, self.MUSIC_FILE)
        self.music_path = path if os.path.isfile(path) else None

    def _setup_footsteps_channel(self):
        if not self.mixer_ok:
            return
        try:
            # reserve the last available channel purely for footsteps
            num = pygame.mixer.get_num_channels()
            if num < 8:
                pygame.mixer.set_num_channels(8)
                num = 8
            self.footsteps_channel = pygame.mixer.Channel(num - 1)
        except Exception:
            self.footsteps_channel = None

    def play_sound(self, key, volume=None):
        """Play a one-shot sound effect by its key. Never raises."""
        snd = self.sounds.get(key)
        if snd is None:
            return
        try:
            snd.set_volume(self.sfx_volume if volume is None else volume)
            snd.play()
        except Exception:
            pass

    def update_footsteps(self, should_play):
        """Loop footsteps.wav while should_play is True, stop otherwise."""
        snd = self.sounds.get("footsteps")
        if snd is None or self.footsteps_channel is None:
            return
        try:
            if should_play and not self._footsteps_playing:
                self.footsteps_channel.play(snd, loops=-1)
                self._footsteps_playing = True
            elif not should_play and self._footsteps_playing:
                self.footsteps_channel.stop()
                self._footsteps_playing = False

            if self._footsteps_playing:
                self.footsteps_channel.set_volume(self.sfx_volume)
        except Exception:
            pass

    def set_sfx_volume(self, vol):
        self.sfx_volume = clamp(vol, 0.0, 1.0)
        if self.footsteps_channel is not None and self._footsteps_playing:
            try:
                self.footsteps_channel.set_volume(self.sfx_volume)
            except Exception:
                pass


# --------------------------------------------------------------------------
# PARTICLES
# --------------------------------------------------------------------------

class Particle:
    def __init__(self, pos, vel, life, color, radius):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.life = life
        self.max_life = life
        self.color = color
        self.radius = radius

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= 0.94
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        if self.life <= 0:
            return
        ratio = max(0.0, self.life / self.max_life)
        r = max(1, int(self.radius * ratio))
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), r)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def spawn_explosion(self, pos, color=ORANGE, count=24,
                         speed_range=(50, 220), life_range=(0.3, 0.8), radius=4):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(*speed_range)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            life = random.uniform(*life_range)
            self.particles.append(Particle(pos, vel, life, color, radius))

    def spawn_blood(self, pos, count=10):
        self.spawn_explosion(pos, color=DARK_RED, count=count,
                              speed_range=(30, 140), life_range=(0.2, 0.5), radius=3)

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

    def clear(self):
        self.particles = []


# --------------------------------------------------------------------------
# BULLET
# --------------------------------------------------------------------------

class Bullet:
    RADIUS = 4
    SPEED = 700

    def __init__(self, pos, direction, damage):
        self.pos = pygame.Vector2(pos)
        d = pygame.Vector2(direction)
        self.dir = d.normalize() if d.length_squared() > 0 else pygame.Vector2(1, 0)
        self.damage = damage
        self.alive = True

    def update(self, dt):
        self.pos += self.dir * self.SPEED * dt
        if self.pos.x < -50 or self.pos.x > WIDTH + 50 or \
           self.pos.y < -50 or self.pos.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surf, img=None):
        if img is not None:
            rect = img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(img, rect)
        else:
            pygame.draw.circle(surf, YELLOW, (int(self.pos.x), int(self.pos.y)), self.RADIUS)


# --------------------------------------------------------------------------
# PLAYER
# --------------------------------------------------------------------------

class Player:
    RADIUS = 18

    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.speed = 220.0

        self.max_health = 100
        self.health = 100

        self.mag_size = 30
        self.ammo = self.mag_size
        self.reserve_ammo = 150

        self.reloading = False
        self.reload_time = 1.6
        self.reload_timer = 0.0

        self.fire_cooldown = 0.12
        self.fire_timer = 0.0

        self.angle = 0.0
        self.hurt_cooldown = 0.0
        self.alive = True
        self.kills = 0

        # True while the player is actively moving (drives footsteps.wav)
        self.moving = False

    def handle_input(self, keys, dt):
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1

        self.moving = move.length_squared() > 0

        if self.moving:
            move = move.normalize()

        self.pos += move * self.speed * dt
        self.pos.x = clamp(self.pos.x, self.RADIUS, WIDTH - self.RADIUS)
        self.pos.y = clamp(self.pos.y, self.RADIUS, HEIGHT - self.RADIUS)

    def update(self, dt, mouse_pos):
        direction = pygame.Vector2(mouse_pos) - self.pos
        if direction.length_squared() > 0:
            self.angle = math.atan2(direction.y, direction.x)

        if self.fire_timer > 0:
            self.fire_timer -= dt
        if self.hurt_cooldown > 0:
            self.hurt_cooldown -= dt

        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self._finish_reload()

    def start_reload(self, assets):
        if self.reloading or self.ammo == self.mag_size or self.reserve_ammo <= 0:
            return
        self.reloading = True
        self.reload_timer = self.reload_time
        assets.play_sound("reload")

    def _finish_reload(self):
        needed = self.mag_size - self.ammo
        take = min(needed, self.reserve_ammo)
        self.ammo += take
        self.reserve_ammo -= take
        self.reloading = False

    def can_shoot(self):
        return (not self.reloading) and self.fire_timer <= 0 and self.ammo > 0

    def shoot(self, mouse_pos, assets):
        if self.ammo <= 0 and not self.reloading:
            self.start_reload(assets)
            return None
        if not self.can_shoot():
            return None

        direction = pygame.Vector2(mouse_pos) - self.pos
        self.ammo -= 1
        self.fire_timer = self.fire_cooldown
        assets.play_sound("gun")
        return Bullet(self.pos, direction, damage=25)

    def take_damage(self, amount):
        if self.hurt_cooldown > 0 or not self.alive:
            return
        self.health -= amount
        self.hurt_cooldown = 0.4
        if self.health <= 0:
            self.health = 0
            self.alive = False

    def draw(self, surf, assets):
        img = assets.images.get("player.png")
        if img is not None:
            rotated = pygame.transform.rotate(img, -math.degrees(self.angle))
            rect = rotated.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(rotated, rect)
        else:
            flash = self.hurt_cooldown > 0
            color = WHITE if flash else BLUE
            pygame.draw.circle(surf, color, (int(self.pos.x), int(self.pos.y)), self.RADIUS)
            pygame.draw.circle(surf, BLACK, (int(self.pos.x), int(self.pos.y)), self.RADIUS, 2)
            end = self.pos + pygame.Vector2(math.cos(self.angle), math.sin(self.angle)) * (self.RADIUS + 16)
            pygame.draw.line(surf, BLACK, self.pos, end, 4)


# --------------------------------------------------------------------------
# ZOMBIES
# --------------------------------------------------------------------------

class Zombie:
    TYPE = "normal"
    COLOR = GREEN
    RADIUS = 16

    def __init__(self, pos, health, speed, damage, score_value):
        self.pos = pygame.Vector2(pos)
        self.max_health = health
        self.health = health
        self.speed = speed
        self.damage = damage
        self.score_value = score_value
        self.alive = True
        self.attack_cooldown = 0.0
        self.attack_rate = 0.8

    def update(self, dt, target_pos):
        direction = pygame.Vector2(target_pos) - self.pos
        if direction.length_squared() > 0:
            direction = direction.normalize()
        self.pos += direction * self.speed * dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            return True
        return False

    def can_attack(self):
        return self.attack_cooldown <= 0

    def attack(self):
        self.attack_cooldown = self.attack_rate
        return self.damage

    def draw(self, surf, img=None):
        if img is not None:
            rect = img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(img, rect)
        else:
            pygame.draw.circle(surf, self.COLOR, (int(self.pos.x), int(self.pos.y)), self.RADIUS)
            pygame.draw.circle(surf, BLACK, (int(self.pos.x), int(self.pos.y)), self.RADIUS, 2)

        bar_w = self.RADIUS * 2
        ratio = self.health / self.max_health if self.max_health > 0 else 0
        bx = int(self.pos.x - self.RADIUS)
        by = int(self.pos.y - self.RADIUS - 10)
        pygame.draw.rect(surf, GRAY, (bx, by, bar_w, 5))
        pygame.draw.rect(surf, RED, (bx, by, int(bar_w * ratio), 5))


class NormalZombie(Zombie):
    TYPE = "normal"
    COLOR = GREEN
    RADIUS = 16

    def __init__(self, pos, wave):
        health = 40 + wave * 4
        speed = random.uniform(60, 85)
        super().__init__(pos, health, speed, damage=8, score_value=10)


class FastZombie(Zombie):
    TYPE = "fast"
    COLOR = YELLOW
    RADIUS = 13

    def __init__(self, pos, wave):
        health = 25 + wave * 3
        speed = random.uniform(140, 175)
        super().__init__(pos, health, speed, damage=6, score_value=15)
        self.attack_rate = 0.5


class TankZombie(Zombie):
    TYPE = "tank"
    COLOR = PURPLE
    RADIUS = 24

    def __init__(self, pos, wave):
        health = 140 + wave * 10
        speed = random.uniform(30, 45)
        super().__init__(pos, health, speed, damage=18, score_value=30)
        self.attack_rate = 1.2


class BossZombie(Zombie):
    TYPE = "boss"
    COLOR = (180, 20, 20)
    RADIUS = 42

    def __init__(self, pos, wave):
        health = 800 + wave * 60
        speed = random.uniform(45, 58)
        super().__init__(pos, health, speed, damage=30, score_value=500)
        self.attack_rate = 1.0


# --------------------------------------------------------------------------
# WAVE MANAGER
# --------------------------------------------------------------------------

class WaveManager:
    def __init__(self):
        self.wave = 0
        self.zombies_to_spawn = 0
        self.spawn_timer = 0.0
        self.spawn_interval = 1.0
        self.wave_active = False
        self.boss_wave = False

    def start_next_wave(self):
        self.wave += 1
        self.boss_wave = (self.wave % 5 == 0)
        self.zombies_to_spawn = 5 + self.wave * 2
        self.spawn_timer = 0.0
        self.spawn_interval = max(0.25, 1.0 - self.wave * 0.03)
        self.wave_active = True

    def get_spawn_position(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            return (random.uniform(0, WIDTH), -30)
        if side == "bottom":
            return (random.uniform(0, WIDTH), HEIGHT + 30)
        if side == "left":
            return (-30, random.uniform(0, HEIGHT))
        return (WIDTH + 30, random.uniform(0, HEIGHT))

    def make_zombie(self, pos):
        if self.boss_wave and self.zombies_to_spawn == 1:
            return BossZombie(pos, self.wave)
        roll = random.random()
        if roll < 0.55:
            return NormalZombie(pos, self.wave)
        elif roll < 0.80:
            return FastZombie(pos, self.wave)
        else:
            return TankZombie(pos, self.wave)

    def update(self, dt, zombies_list):
        if not self.wave_active:
            return
        if self.zombies_to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.spawn_interval
                pos = self.get_spawn_position()
                zombies_list.append(self.make_zombie(pos))
                self.zombies_to_spawn -= 1
        else:
            if len(zombies_list) == 0:
                self.wave_active = False


# --------------------------------------------------------------------------
# HIGH SCORE MANAGER
# --------------------------------------------------------------------------

class HighScoreManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(base_dir, "highscore.json")
        self.high_score = 0
        self.load()

    def load(self):
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                self.high_score = int(data.get("high_score", 0))
        except Exception:
            self.high_score = 0

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception:
            pass

    def update(self, score):
        if score > self.high_score:
            self.high_score = score
            self.save()
            return True
        return False


# --------------------------------------------------------------------------
# UI BUTTON
# --------------------------------------------------------------------------

class Button:
    def __init__(self, rect, text, font, base_color=(50, 50, 62),
                 hover_color=(85, 85, 110), text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color

    def draw(self, surf, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if hovered else self.base_color
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, BLACK, self.rect, width=2, border_radius=8)
        label = self.font.render(self.text, True, self.text_color)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def is_clicked(self, mouse_pos, mouse_click):
        return mouse_click and self.rect.collidepoint(mouse_pos)


# --------------------------------------------------------------------------
# MAIN GAME CLASS
# --------------------------------------------------------------------------

class Game:
    def __init__(self):
        # --- 1. Initialize pygame.mixer correctly, before pygame.init() ---
        # pre_init must run before pygame.init() to take effect, and is
        # wrapped safely so a device with no audio hardware (or a broken
        # SDL audio backend under Buildozer/Android) never crashes the game.
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass

        pygame.init()

        self.mixer_ok = True
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            self.mixer_ok = False

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Zombie Survival")
        self.clock = pygame.time.Clock()

        self.assets = AssetManager(self.mixer_ok)

        icon = self.assets.images.get("icon.png")
        if icon is not None:
            try:
                pygame.display.set_icon(icon)
            except Exception:
                pass

        self.font_small = pygame.font.SysFont("arial", 18)
        self.font_med = pygame.font.SysFont("arial", 28)
        self.font_large = pygame.font.SysFont("arial", 52)

        self.high_score_mgr = HighScoreManager()

        self.state = STATE_MENU
        self.music_volume = 0.5

        # Background music starts as soon as the game starts and loops forever
        self._start_music()

        self._build_buttons()
        self.reset_game_state()

    # ---------------------------------------------------------- setup ----

    def _start_music(self):
        if self.mixer_ok and self.assets.music_path:
            try:
                pygame.mixer.music.load(self.assets.music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)  # loop forever
            except Exception:
                pass

    def _set_music_volume(self, vol):
        self.music_volume = clamp(vol, 0.0, 1.0)
        if self.mixer_ok:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

    def _build_buttons(self):
        cx = WIDTH // 2

        self.menu_buttons = {
            "start": Button((cx - 100, 230, 200, 50), "Start Game", self.font_med),
            "settings": Button((cx - 100, 300, 200, 50), "Settings", self.font_med),
            "quit": Button((cx - 100, 370, 200, 50), "Quit", self.font_med),
        }

        self.settings_buttons = {
            "music_down": Button((cx - 170, 210, 46, 40), "-", self.font_med),
            "music_up": Button((cx + 124, 210, 46, 40), "+", self.font_med),
            "sfx_down": Button((cx - 170, 280, 46, 40), "-", self.font_med),
            "sfx_up": Button((cx + 124, 280, 46, 40), "+", self.font_med),
            "back": Button((cx - 100, 400, 200, 50), "Back", self.font_med),
        }

        self.pause_buttons = {
            "resume": Button((cx - 100, 230, 200, 50), "Resume", self.font_med),
            "menu": Button((cx - 100, 300, 200, 50), "Main Menu", self.font_med),
        }

        self.gameover_buttons = {
            "restart": Button((cx - 100, 330, 200, 50), "Restart", self.font_med),
            "menu": Button((cx - 100, 400, 200, 50), "Main Menu", self.font_med),
        }

        self.victory_buttons = {
            "restart": Button((cx - 100, 330, 200, 50), "Play Again", self.font_med),
            "menu": Button((cx - 100, 400, 200, 50), "Main Menu", self.font_med),
        }

    def reset_game_state(self):
        self.player = Player((WIDTH / 2, HEIGHT / 2))
        self.bullets = []
        self.zombies = []
        self.particles = ParticleSystem()
        self.wave_manager = WaveManager()
        self.score = 0
        self.game_over_saved = False
        self.new_high_score = False
        self.assets.update_footsteps(False)

    # ------------------------------------------------------- main loop ----

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            mouse_pos = pygame.mouse.get_pos()
            mouse_click = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_click = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == STATE_PLAYING:
                            self.state = STATE_PAUSED
                        elif self.state == STATE_PAUSED:
                            self.state = STATE_PLAYING
                    if event.key == pygame.K_p:
                        if self.state == STATE_PLAYING:
                            self.state = STATE_PAUSED
                        elif self.state == STATE_PAUSED:
                            self.state = STATE_PLAYING
                    if event.key == pygame.K_r and self.state == STATE_PLAYING:
                        self.player.start_reload(self.assets)

            keys = pygame.key.get_pressed()
            mouse_buttons = pygame.mouse.get_pressed()

            # Footsteps should only ever be audible during active gameplay
            if self.state != STATE_PLAYING:
                self.assets.update_footsteps(False)

            if self.state == STATE_MENU:
                self._update_menu(mouse_pos, mouse_click)
            elif self.state == STATE_SETTINGS:
                self._update_settings(mouse_pos, mouse_click)
            elif self.state == STATE_PLAYING:
                self._update_playing(dt, keys, mouse_pos, mouse_buttons)
            elif self.state == STATE_PAUSED:
                self._update_paused(mouse_pos, mouse_click)
            elif self.state == STATE_GAMEOVER:
                self._update_gameover(mouse_pos, mouse_click)
            elif self.state == STATE_VICTORY:
                self._update_victory(mouse_pos, mouse_click)

            self._draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ------------------------------------------------------ state logic ----

    def _update_menu(self, mouse_pos, mouse_click):
        b = self.menu_buttons
        if b["start"].is_clicked(mouse_pos, mouse_click):
            self.reset_game_state()
            self.wave_manager.start_next_wave()
            self.state = STATE_PLAYING
        elif b["settings"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_SETTINGS
        elif b["quit"].is_clicked(mouse_pos, mouse_click):
            pygame.quit()
            sys.exit()

    def _update_settings(self, mouse_pos, mouse_click):
        b = self.settings_buttons
        if b["music_down"].is_clicked(mouse_pos, mouse_click):
            self._set_music_volume(self.music_volume - 0.1)
        elif b["music_up"].is_clicked(mouse_pos, mouse_click):
            self._set_music_volume(self.music_volume + 0.1)
        elif b["sfx_down"].is_clicked(mouse_pos, mouse_click):
            self.assets.set_sfx_volume(self.assets.sfx_volume - 0.1)
        elif b["sfx_up"].is_clicked(mouse_pos, mouse_click):
            self.assets.set_sfx_volume(self.assets.sfx_volume + 0.1)
        elif b["back"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    def _update_playing(self, dt, keys, mouse_pos, mouse_buttons):
        self.player.handle_input(keys, dt)
        self.player.update(dt, mouse_pos)

        # Footsteps loop while the player is moving, stop the instant they stop
        self.assets.update_footsteps(self.player.moving and self.player.alive)

        if mouse_buttons[0]:
            bullet = self.player.shoot(mouse_pos, self.assets)
            if bullet is not None:
                self.bullets.append(bullet)

        self.wave_manager.update(dt, self.zombies)
        if (not self.wave_manager.wave_active and len(self.zombies) == 0
                and self.wave_manager.zombies_to_spawn == 0):
            if self.wave_manager.wave >= WIN_WAVE:
                self._on_victory()
            else:
                self.wave_manager.start_next_wave()

        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive]

        for z in self.zombies:
            z.update(dt, self.player.pos)

        self._handle_collisions()
        self.particles.update(dt)

        if not self.player.alive:
            self._on_game_over()

    def _handle_collisions(self):
        # bullets vs zombies
        for b in self.bullets:
            if not b.alive:
                continue
            for z in self.zombies:
                if not z.alive:
                    continue
                if b.pos.distance_to(z.pos) < (Bullet.RADIUS + z.RADIUS):
                    died = z.take_damage(b.damage)
                    self.particles.spawn_blood(z.pos, count=8)
                    b.alive = False
                    if died:
                        self.score += z.score_value
                        self.player.kills += 1
                        color = (255, 60, 0) if z.TYPE == "boss" else ORANGE
                        count = 45 if z.TYPE == "boss" else 20
                        self.particles.spawn_explosion(z.pos, color=color, count=count)
                        # Zombie death -> zombie.wav
                        self.assets.play_sound("zombie")
                        if z.TYPE == "boss":
                            # Boss death also triggers the big explosion sound
                            self.assets.play_sound("explosion")
                    break

        self.zombies = [z for z in self.zombies if z.alive]

        # zombies vs player
        for z in self.zombies:
            if z.pos.distance_to(self.player.pos) < (z.RADIUS + Player.RADIUS):
                if z.can_attack():
                    dmg = z.attack()
                    self.player.take_damage(dmg)
                    # Zombie attack -> zombie.wav
                    self.assets.play_sound("zombie")

    def _on_game_over(self):
        if not self.game_over_saved:
            self.new_high_score = self.high_score_mgr.update(self.score)
            self.game_over_saved = True
            self.assets.update_footsteps(False)
            self.assets.play_sound("gameover")
        self.state = STATE_GAMEOVER

    def _on_victory(self):
        if not self.game_over_saved:
            self.new_high_score = self.high_score_mgr.update(self.score)
            self.game_over_saved = True
            self.assets.update_footsteps(False)
            self.assets.play_sound("victory")
        self.state = STATE_VICTORY

    def _update_paused(self, mouse_pos, mouse_click):
        b = self.pause_buttons
        if b["resume"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_PLAYING
        elif b["menu"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    def _update_gameover(self, mouse_pos, mouse_click):
        b = self.gameover_buttons
        if b["restart"].is_clicked(mouse_pos, mouse_click):
            self.reset_game_state()
            self.wave_manager.start_next_wave()
            self.state = STATE_PLAYING
        elif b["menu"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    def _update_victory(self, mouse_pos, mouse_click):
        b = self.victory_buttons
        if b["restart"].is_clicked(mouse_pos, mouse_click):
            self.reset_game_state()
            self.wave_manager.start_next_wave()
            self.state = STATE_PLAYING
        elif b["menu"].is_clicked(mouse_pos, mouse_click):
            self.state = STATE_MENU

    # ------------------------------------------------------------ draw ----

    def _draw(self):
        self.screen.fill(DARK_GRAY)

        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_SETTINGS:
            self._draw_settings()
        elif self.state in (STATE_PLAYING, STATE_PAUSED):
            self._draw_game()
            if self.state == STATE_PAUSED:
                self._draw_pause_overlay()
        elif self.state == STATE_GAMEOVER:
            self._draw_game()
            self._draw_gameover_overlay()
        elif self.state == STATE_VICTORY:
            self._draw_game()
            self._draw_victory_overlay()

    def _draw_menu(self):
        title = self.font_large.render("ZOMBIE SURVIVAL", True, RED)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))

        hs = self.font_small.render(f"High Score: {self.high_score_mgr.high_score}",
                                     True, (200, 200, 200))
        self.screen.blit(hs, hs.get_rect(center=(WIDTH // 2, 175)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons.values():
            btn.draw(self.screen, mouse_pos)

    def _draw_settings(self):
        title = self.font_med.render("SETTINGS", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

        mvol = self.font_med.render(f"Music Volume: {int(self.music_volume * 100)}%", True, WHITE)
        self.screen.blit(mvol, mvol.get_rect(center=(WIDTH // 2, 230)))

        svol = self.font_med.render(f"SFX Volume: {int(self.assets.sfx_volume * 100)}%", True, WHITE)
        self.screen.blit(svol, svol.get_rect(center=(WIDTH // 2, 300)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.settings_buttons.values():
            btn.draw(self.screen, mouse_pos)

    def _draw_game(self):
        bg = self.assets.images.get("background.png")
        if bg is not None:
            self.screen.blit(pygame.transform.scale(bg, (WIDTH, HEIGHT)), (0, 0))

        for z in self.zombies:
            img = self.assets.images.get(f"zombie_{z.TYPE}.png")
            z.draw(self.screen, img)

        bullet_img = self.assets.images.get("bullet.png")
        for b in self.bullets:
            b.draw(self.screen, bullet_img)

        self.player.draw(self.screen, self.assets)
        self.particles.draw(self.screen)
        self._draw_hud()

    def _draw_hud(self):
        pygame.draw.rect(self.screen, GRAY, (20, 20, 220, 24))
        ratio = self.player.health / self.player.max_health
        pygame.draw.rect(self.screen, RED, (20, 20, int(220 * ratio), 24))
        pygame.draw.rect(self.screen, BLACK, (20, 20, 220, 24), width=2)
        hp_text = self.font_small.render(
            f"HP: {int(self.player.health)}/{self.player.max_health}", True, WHITE)
        self.screen.blit(hp_text, (26, 24))

        ammo_text = self.font_med.render(
            f"{self.player.ammo}/{self.player.reserve_ammo}", True, WHITE)
        self.screen.blit(ammo_text, (WIDTH - 150, 20))
        if self.player.reloading:
            rl = self.font_small.render("RELOADING...", True, YELLOW)
            self.screen.blit(rl, (WIDTH - 150, 52))

        score_text = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (20, 55))

        wave_text = self.font_small.render(
            f"Wave: {self.wave_manager.wave} / {WIN_WAVE}", True, WHITE)
        self.screen.blit(wave_text, (20, 92))

        if self.wave_manager.boss_wave and self.wave_manager.wave_active:
            boss_text = self.font_med.render("BOSS WAVE!", True, RED)
            self.screen.blit(boss_text, boss_text.get_rect(center=(WIDTH // 2, 30)))

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("PAUSED", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 150)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.pause_buttons.values():
            btn.draw(self.screen, mouse_pos)

    def _draw_gameover_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

        score_text = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, 195)))

        hs_text = self.font_med.render(
            f"High Score: {self.high_score_mgr.high_score}", True, YELLOW)
        self.screen.blit(hs_text, hs_text.get_rect(center=(WIDTH // 2, 235)))

        if self.new_high_score:
            new_hs = self.font_small.render("NEW HIGH SCORE!", True, YELLOW)
            self.screen.blit(new_hs, new_hs.get_rect(center=(WIDTH // 2, 265)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.gameover_buttons.values():
            btn.draw(self.screen, mouse_pos)

    def _draw_victory_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("VICTORY!", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

        sub = self.font_med.render(f"You survived {WIN_WAVE} waves!", True, WHITE)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 180)))

        score_text = self.font_med.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, 225)))

        hs_text = self.font_med.render(
            f"High Score: {self.high_score_mgr.high_score}", True, YELLOW)
        self.screen.blit(hs_text, hs_text.get_rect(center=(WIDTH // 2, 265)))

        if self.new_high_score:
            new_hs = self.font_small.render("NEW HIGH SCORE!", True, YELLOW)
            self.screen.blit(new_hs, new_hs.get_rect(center=(WIDTH // 2, 295)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.victory_buttons.values():
            btn.draw(self.screen, mouse_pos)


# --------------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------------

if __name__ == "__main__":
    game = Game()
    game.run()
