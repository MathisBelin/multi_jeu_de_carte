"""Ecran de choix de variante quand on clique sur la tuile « Solitaire »."""
import pygame

from . import constants as C
from . import ui
from .scene import Scene
from .menu import ModeCard


class SolitaireSelectScene(Scene):
    """Petit hub : choisir entre le Klondike et le Spider."""

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(C.FONT_UI, 60, bold=True)
        self.sub_font = pygame.font.SysFont(C.FONT_UI, 24)
        self.card_title = pygame.font.SysFont(C.FONT_UI, 30, bold=True)
        self.card_desc = pygame.font.SysFont(C.FONT_UI, 19)
        self.tag_font = pygame.font.SysFont(C.FONT_UI, 17, bold=True)
        self.suit_font = pygame.font.SysFont(C.FONT_SUIT, 130)
        self.btn_font = pygame.font.SysFont(C.FONT_UI, 17, bold=True)

        cw, ch = 360, 210
        gap = 46
        total_w = 2 * cw + gap
        left = (C.SCREEN_W - total_w) // 2
        top = 300
        self.cards = [
            ModeCard((left, top, cw, ch), "Klondike",
                     "Le solitaire classique, une carte à la fois.",
                     C.SPADE, True, self.app.show_klondike),
            ModeCard((left + cw + gap, top, cw, ch), "Spider",
                     "Deux jeux, suites d'une même couleur.",
                     C.HEART, True, self.app.show_spider),
        ]
        self.back_btn = ui.Button((C.SCREEN_W // 2 - 90, top + ch + 44, 180, 46),
                                  "Menu", self.app.show_menu, self.btn_font,
                                  fill=(150, 92, 92), text_col=C.TEXT_LIGHT)

    def handle_event(self, event):
        if self.back_btn.handle(event):
            return
        for c in self.cards:
            c.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.show_menu()

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.back_btn.update(dt, mouse)
        for c in self.cards:
            c.update(dt, mouse)

    def draw(self, surface):
        ui.draw_felt(surface)
        title = self.title_font.render("Solitaire", True, C.TEXT_LIGHT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 150)))
        sub = self.sub_font.render("Choisissez une variante", True, C.TEXT_DIM)
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 214)))
        for c in self.cards:
            c.draw(surface, self.card_title, self.card_desc,
                   self.tag_font, self.suit_font)
        self.back_btn.draw(surface)
