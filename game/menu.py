"""Menu principal : selection du mode de jeu."""
import pygame

from . import constants as C
from . import ui
from .scene import Scene


def wrap_text(text, font, max_width, max_lines=2):
    """Découpe un texte en lignes tenant dans max_width (au plus max_lines)."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines - 1:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


class ModeCard:
    """Grande tuile cliquable representant un mode de jeu."""
    def __init__(self, rect, title, desc, suit, available, action):
        self.rect = pygame.Rect(rect)
        self.title = title
        self.desc = desc
        self.suit = suit
        self.available = available
        self.action = action
        self.hover = 0.0
        self._down = False

    def update(self, dt, mouse):
        target = 1.0 if self.rect.collidepoint(mouse) and self.available else 0.0
        self.hover += (target - self.hover) * min(1, dt * 12)

    def handle(self, event):
        if not self.available:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._down = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._down and self.rect.collidepoint(event.pos):
                self.action()
            self._down = False

    def draw(self, surface, title_font, desc_font, tag_font, suit_font):
        lift = int(self.hover * 6)
        r = self.rect.move(0, -lift)
        shadow = pygame.Surface((r.w + 40, r.h + 40), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 110), (20, 26, r.w, r.h),
                         border_radius=18)
        surface.blit(shadow, (r.x - 20, r.y - 20))

        base = (44, 58, 74)
        col = tuple(int(ui.lerp(base[i], (58, 78, 100)[i], self.hover))
                    for i in range(3))
        if not self.available:
            col = (40, 46, 52)
        pygame.draw.rect(surface, col, r, border_radius=18)
        edge = C.ACCENT if self.available else (90, 96, 102)
        pygame.draw.rect(surface, edge, r, width=2, border_radius=18)

        # grande enseigne filigrane
        red = self.suit in C.RED_SUITS
        gcol = C.SUIT_RED if red else (230, 235, 240)
        glyph = suit_font.render(C.SUIT_GLYPH[self.suit], True, gcol)
        glyph.set_alpha(60 if self.available else 30)
        surface.blit(glyph, glyph.get_rect(center=(r.right - 70, r.centery)))

        title = title_font.render(self.title, True,
                                  C.TEXT_LIGHT if self.available else C.TEXT_DIM)
        surface.blit(title, (r.x + 28, r.y + 26))
        lines = wrap_text(self.desc, desc_font, r.w - 56, max_lines=2)
        for i, ln in enumerate(lines):
            desc = desc_font.render(ln, True, C.TEXT_DIM)
            surface.blit(desc, (r.x + 28, r.y + 68 + i * 20))

        tag = "JOUER" if self.available else "BIENTOT"
        tcol = C.ACCENT if self.available else (120, 126, 132)
        t = tag_font.render(tag, True, tcol)
        surface.blit(t, (r.x + 28, r.bottom - 34))


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(C.FONT_UI, 68, bold=True)
        self.sub_font = pygame.font.SysFont(C.FONT_UI, 24)
        self.card_title = pygame.font.SysFont(C.FONT_UI, 30, bold=True)
        self.card_desc = pygame.font.SysFont(C.FONT_UI, 19)
        self.tag_font = pygame.font.SysFont(C.FONT_UI, 17, bold=True)
        self.suit_font = pygame.font.SysFont(C.FONT_SUIT, 130)
        self.small_suit = pygame.font.SysFont(C.FONT_SUIT, 40)
        self.btn_font = pygame.font.SysFont(C.FONT_UI, 17, bold=True)
        self.time = 0.0
        self._build()
        self.fs_btn = ui.Button((C.SCREEN_W - 210, 24, 186, 40),
                                self._fs_label(), self._toggle_fs, self.btn_font,
                                fill=(52, 70, 90), text_col=C.TEXT_LIGHT)

    def _fs_label(self):
        return "Fenêtré  (F11)" if self.app.fullscreen else "Plein écran  (F11)"

    def _toggle_fs(self):
        self.app.toggle_fullscreen()
        self.fs_btn.label = self._fs_label()

    def _build(self):
        cw, ch = 340, 148
        gap = 26
        cols = 3
        total_w = cols * cw + (cols - 1) * gap
        left = (C.SCREEN_W - total_w) // 2
        top = 214
        specs = [
            ("Solitaire", "Klondike ou Spider, au choix.",
             C.SPADE, True, self.app.show_solitaire),
            ("Le Président", "Videz votre main avant les IA.",
             C.HEART, True, self.app.show_president),
            ("Bataille", "Le duel le plus simple (avec jokers).",
             C.SPADE, True, self.app.show_bataille),
            ("Le Pouilleux", "Ne restez pas avec la carte orpheline.",
             C.CLUB, True, self.app.show_pouilleux),
            ("Le Bouclié", "Boucliers et PV : éliminez les autres.",
             C.DIAMOND, True, self.app.show_bouclie),
            ("Le Barbu", "6 manches à contrats : le moins de points.",
             C.SPADE, True, self.app.show_barbu),
            ("Le Dutch", "Mémoire et bluff : visez le plus bas.",
             C.DIAMOND, True, self.app.show_dutch),
            ("Le 98", "Ne faites pas déborder la pile de 98.",
             C.CLUB, True, self.app.show_le98),
        ]
        self.cards = []
        for i, (title, desc, suit, avail, action) in enumerate(specs):
            row, colx = divmod(i, cols)
            rect = (left + colx * (cw + gap), top + row * (ch + gap), cw, ch)
            self.cards.append(ModeCard(rect, title, desc, suit, avail, action))

    def handle_event(self, event):
        if self.fs_btn.handle(event):
            return
        for c in self.cards:
            c.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.app.show_solitaire()

    def update(self, dt):
        self.time += dt
        mouse = pygame.mouse.get_pos()
        self.fs_btn.label = self._fs_label()
        self.fs_btn.update(dt, mouse)
        for c in self.cards:
            c.update(dt, mouse)

    def draw(self, surface):
        ui.draw_felt(surface)
        self.fs_btn.draw(surface)
        # titre
        title = self.title_font.render("Cartes Classic", True, C.TEXT_LIGHT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 120)))
        # enseignes decoratives sous le titre
        glyphs = "  ".join(C.SUIT_GLYPH[s] for s in C.SUITS)
        sub = self.small_suit.render(glyphs, True, C.ACCENT)
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 185)))

        for c in self.cards:
            c.draw(surface, self.card_title, self.card_desc,
                   self.tag_font, self.suit_font)

        hint = self.sub_font.render("Choisissez un mode pour commencer",
                                    True, C.TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(C.SCREEN_W // 2, C.SCREEN_H - 46)))
