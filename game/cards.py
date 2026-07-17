"""Modele de carte et rendu graphique (surfaces mises en cache)."""
import pygame
from . import constants as C
from . import ui


class Card:
    __slots__ = ("suit", "rank", "face_up")

    def __init__(self, suit, rank, face_up=False):
        self.suit = suit
        self.rank = rank
        self.face_up = face_up

    @property
    def is_joker(self):
        return self.suit == C.JOKER

    @property
    def red(self):
        if self.suit == C.JOKER:
            return self.rank == C.JOKER_RED
        return self.suit in C.RED_SUITS

    @property
    def color(self):
        return C.SUIT_RED if self.red else C.SUIT_BLACK

    def __repr__(self):
        if self.suit == C.JOKER:
            return "JOKER" + ("♥" if self.red else "♠")
        return f"{C.rank_label(self.rank)}{C.SUIT_GLYPH[self.suit]}"


class CardRenderer:
    """Fabrique et met en cache les faces des cartes a une taille donnee."""

    def __init__(self, w=C.CARD_W, h=C.CARD_H):
        self.w, self.h = w, h
        self.rank_font = pygame.font.SysFont(C.FONT_UI, int(h * 0.20), bold=True)
        self.suit_corner = pygame.font.SysFont(C.FONT_SUIT, int(h * 0.15))
        self.suit_big = pygame.font.SysFont(C.FONT_SUIT, int(h * 0.46))
        self._faces = {}
        self.back = self._make_back()
        self.slot = self._make_slot()
        self.shadow = ui.soft_shadow((w, h), C.CARD_RADIUS)

    # -- construction --
    def _corner(self, card):
        """Petit index vertical rang + enseigne."""
        rank = self.rank_font.render(C.rank_label(card.rank), True, card.color)
        suit = self.suit_corner.render(C.SUIT_GLYPH[card.suit], True, card.color)
        cw = max(rank.get_width(), suit.get_width())
        surf = pygame.Surface((cw, rank.get_height() + suit.get_height() - 4),
                              pygame.SRCALPHA)
        surf.blit(rank, ((cw - rank.get_width()) // 2, 0))
        surf.blit(suit, ((cw - suit.get_width()) // 2, rank.get_height() - 4))
        return surf

    def _make_joker(self, card):
        """Face d'un joker : étoile centrale + mot « JOKER », en rouge ou noir."""
        w, h = self.w, self.h
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rect = surf.get_rect()
        pygame.draw.rect(surf, C.CARD_FACE, rect, border_radius=C.CARD_RADIUS)
        pygame.draw.rect(surf, C.CARD_FACE_EDGE, rect, width=1,
                         border_radius=C.CARD_RADIUS)
        col = card.color
        pad = int(h * 0.055)
        star_c = self.suit_corner.render("★", True, col)
        surf.blit(star_c, (pad, pad))
        surf.blit(pygame.transform.rotate(star_c, 180),
                  (w - pad - star_c.get_width(), h - pad - star_c.get_height()))
        big = self.suit_big.render("★", True, col)
        surf.blit(big, big.get_rect(center=(w // 2, int(h * 0.42))))
        word = self.rank_font.render("JOKER", True, col)
        maxw = w - int(w * 0.16)
        if word.get_width() > maxw:
            word = pygame.transform.smoothscale(
                word, (maxw, word.get_height()))
        surf.blit(word, word.get_rect(center=(w // 2, int(h * 0.72))))
        return surf

    def _make_face(self, card):
        if card.suit == C.JOKER:
            return self._make_joker(card)
        w, h = self.w, self.h
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rect = surf.get_rect()
        pygame.draw.rect(surf, C.CARD_FACE, rect, border_radius=C.CARD_RADIUS)
        pygame.draw.rect(surf, C.CARD_FACE_EDGE, rect, width=1,
                         border_radius=C.CARD_RADIUS)

        corner = self._corner(card)
        pad = int(h * 0.055)
        surf.blit(corner, (pad, pad))
        surf.blit(pygame.transform.rotate(corner, 180),
                  (w - pad - corner.get_width(), h - pad - corner.get_height()))

        big = self.suit_big.render(C.SUIT_GLYPH[card.suit], True, card.color)
        surf.blit(big, big.get_rect(center=(w // 2, int(h * 0.5))))
        return surf

    def _make_back(self):
        w, h = self.w, self.h
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rect = surf.get_rect()
        pygame.draw.rect(surf, C.BACK_MAIN, rect, border_radius=C.CARD_RADIUS)
        inner = rect.inflate(-int(w * 0.14), -int(h * 0.10))
        pygame.draw.rect(surf, C.BACK_DARK, inner, border_radius=C.CARD_RADIUS - 3)
        # motif de losanges
        clip = pygame.Surface(inner.size, pygame.SRCALPHA)
        step = 16
        for i in range(-inner.height, inner.width, step):
            pygame.draw.line(clip, (*C.BACK_LIGHT, 90),
                             (i, 0), (i + inner.height, inner.height), 2)
            pygame.draw.line(clip, (*C.BACK_LIGHT, 90),
                             (i, inner.height), (i + inner.height, 0), 2)
        mask = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                         border_radius=C.CARD_RADIUS - 3)
        clip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(clip, inner.topleft)
        pygame.draw.rect(surf, C.BACK_EDGE, inner, width=2,
                         border_radius=C.CARD_RADIUS - 3)
        pygame.draw.rect(surf, C.CARD_FACE_EDGE, rect, width=1,
                         border_radius=C.CARD_RADIUS)
        return surf

    def _make_slot(self):
        w, h = self.w, self.h
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 255, 255, 22), surf.get_rect(),
                         border_radius=C.CARD_RADIUS)
        pygame.draw.rect(surf, (255, 255, 255, 55), surf.get_rect(), width=2,
                         border_radius=C.CARD_RADIUS)
        return surf

    # -- acces --
    def face(self, card):
        key = (card.suit, card.rank)
        surf = self._faces.get(key)
        if surf is None:
            surf = self._make_face(card)
            self._faces[key] = surf
        return surf

    def surface(self, card):
        return self.face(card) if card.face_up else self.back
