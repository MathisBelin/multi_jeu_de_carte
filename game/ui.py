"""Utilitaires UI : easing, degrade, boutons, aides de dessin."""
import pygame
from . import constants as C


# --------------------------------------------------------------------------
# Easing / interpolation
# --------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# --------------------------------------------------------------------------
# Dessin
# --------------------------------------------------------------------------
_gradient_cache = {}


def draw_felt(surface):
    """Fond feutre : degrade vertical + legere vignette, mis en cache."""
    w, h = surface.get_size()
    key = (w, h)
    bg = _gradient_cache.get(key)
    if bg is None:
        bg = pygame.Surface((w, h)).convert()
        for y in range(h):
            t = y / max(1, h - 1)
            col = (
                int(lerp(C.FELT_TOP[0], C.FELT_BOT[0], t)),
                int(lerp(C.FELT_TOP[1], C.FELT_BOT[1], t)),
                int(lerp(C.FELT_TOP[2], C.FELT_BOT[2], t)),
            )
            pygame.draw.line(bg, col, (0, y), (w, y))
        # vignette radiale sombre sur les bords
        vig = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2, h / 2
        maxd = (cx ** 2 + cy ** 2) ** 0.5
        step = 6
        for r in range(int(maxd), 0, -step):
            a = int(90 * (r / maxd) ** 2.2)
            pygame.draw.circle(vig, (0, 0, 0, a), (int(cx), int(cy)), r)
        bg.blit(vig, (0, 0))
        _gradient_cache[key] = bg
    surface.blit(bg, (0, 0))


def round_rect(surface, rect, color, radius, width=0):
    pygame.draw.rect(surface, color, rect, width, border_radius=radius)


def soft_shadow(size, radius, alpha=90, grow=6):
    """Surface d'ombre douce pour une carte."""
    w, h = size
    surf = pygame.Surface((w + grow * 2, h + grow * 2), pygame.SRCALPHA)
    layers = 6
    for i in range(layers, 0, -1):
        a = int(alpha * (i / layers) / layers * 2)
        r = pygame.Rect(grow - i, grow - i + 3, w + i * 2, h + i * 2)
        pygame.draw.rect(surf, (0, 0, 0, a), r, border_radius=radius + i)
    return surf


# --------------------------------------------------------------------------
# Bouton
# --------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, callback, font,
                 fill=C.ACCENT, fill_hover=None, text_col=(30, 34, 40),
                 icon=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.font = font
        self.fill = fill
        self.fill_hover = fill_hover or tuple(min(255, c + 22) for c in fill)
        self.text_col = text_col
        self.icon = icon
        self.hover = 0.0
        self.enabled = True
        self._down = False

    def update(self, dt, mouse_pos):
        target = 1.0 if (self.enabled and self.rect.collidepoint(mouse_pos)) else 0.0
        self.hover += (target - self.hover) * min(1, dt * 14)

    def handle(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._down = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._down and self.rect.collidepoint(event.pos):
                self._down = False
                if self.callback:
                    self.callback()
                return True
            self._down = False
        return False

    def draw(self, surface):
        r = self.rect.copy()
        lift = int(self.hover * 2)
        r.y -= lift
        shadow = pygame.Rect(r.x, r.y + 4, r.w, r.h)
        pygame.draw.rect(surface, (0, 0, 0, 60), shadow, border_radius=12)
        col = self.fill if self.enabled else (110, 118, 120)
        col = tuple(int(lerp(col[i], self.fill_hover[i], self.hover)) for i in range(3))
        pygame.draw.rect(surface, col, r, border_radius=12)
        # liseré clair haut
        top = pygame.Rect(r.x, r.y, r.w, r.h // 2)
        hl = pygame.Surface((r.w, r.h // 2), pygame.SRCALPHA)
        pygame.draw.rect(hl, (255, 255, 255, 32), hl.get_rect(),
                         border_top_left_radius=12, border_top_right_radius=12)
        surface.blit(hl, top)
        txt = self.font.render(self.label, True, self.text_col)
        surface.blit(txt, txt.get_rect(center=r.center))
