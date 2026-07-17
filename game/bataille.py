"""Bataille — le duel le plus simple, à 2 (vous contre l'ordinateur).

54 cartes (52 + 2 jokers) partagées en deux pioches face cachée. À chaque
tour, chacun retourne sa carte du dessus ; la plus forte remporte les deux.
Égalité → BATAILLE : une carte face cachée puis une face visible départagent.
Le premier à ramasser toutes les cartes gagne.

Il n'y a aucune décision de jeu (la Bataille est entièrement déterminée par le
hasard) : le joueur clique/espace pour lancer chaque duel, ou active le mode
« Auto ». Toute l'animation et l'état vivent dans cette scène.
"""
import random
from collections import deque

import pygame

from . import constants as C
from . import ui
from .cards import Card, CardRenderer
from .scene import Scene


def card_value(card):
    """Force à la Bataille : 2..10 < V < D < R < As < Joker (jokers égaux)."""
    if card.suit == C.JOKER:
        return 20
    if card.rank == 1:      # As, le plus fort après le joker
        return 14
    return card.rank


class Fly:
    """Carte en vol d'un point à un autre, éventuellement retournée à l'arrivée."""
    def __init__(self, card, start, target, dur=0.34, reveal=False,
                 face_down=False):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0
        self.reveal = reveal        # anime un retournement dos → face
        self.face_down = face_down  # reste face cachée


class BattleScene(Scene):
    MAX_BATTLES = 4000              # borne de sécurité (sinon « le plus de cartes »)

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(104, 148)
        self.cw, self.ch = 104, 148
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 30, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.big = pygame.font.SysFont(C.FONT_UI, 56, bold=True)
        self.count_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)

        cx = C.SCREEN_W // 2
        self.cx = cx
        self.FOE_PILE = (cx - 330, 130)
        self.FOE_WON = (cx + 330 - self.cw, 130)
        self.MY_PILE = (cx - 330, C.SCREEN_H - 130 - self.ch)
        self.MY_WON = (cx + 330 - self.cw, C.SCREEN_H - 130 - self.ch)
        self.FOE_UP = (cx - self.cw // 2, 256)
        self.MY_UP = (cx - self.cw // 2, C.SCREEN_H - 256 - self.ch)
        self.mid_y = (self.FOE_UP[1] + self.ch + self.MY_UP[1]) // 2
        self.POT = (cx - self.cw - 70, self.mid_y - self.ch // 2)

        self.auto = False
        self._build_buttons()
        self.new_game()

    # ------------------------------------------------------------------
    def _build_buttons(self):
        self.btn_menu = ui.Button((C.SCREEN_W - 150, 16, 120, 40), "Menu",
                                  self.app.show_menu, self.small,
                                  fill=(150, 92, 92), text_col=C.TEXT_LIGHT)
        self.btn_auto = ui.Button((28, 320, 172, 46), self._auto_label(),
                                  self._toggle_auto, self.small,
                                  fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_new = ui.Button((28, 376, 172, 46), "Nouvelle partie",
                                 self.new_game, self.small,
                                 fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        cx = self.cx
        self.over_buttons = [
            ui.Button((cx - 220, 520, 200, 52), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 520, 200, 52), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _auto_label(self):
        return "Auto : activé" if self.auto else "Auto : désactivé"

    def _toggle_auto(self):
        self.auto = not self.auto
        self.btn_auto.label = self._auto_label()
        if self.auto and self.phase == "idle":
            self.pause_t = 0.2

    def _buttons(self):
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        return [self.btn_menu, self.btn_auto, self.btn_new]

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def new_game(self):
        deck = [Card(s, r) for s in C.SUITS for r in range(1, 14)]
        deck.append(Card(C.JOKER, C.JOKER_RED))
        deck.append(Card(C.JOKER, C.JOKER_BLACK))
        random.shuffle(deck)
        self.my_pile = deque(deck[:27])
        self.foe_pile = deque(deck[27:])
        self.my_won = []
        self.foe_won = []
        self.pot = []                  # cartes en jeu banquées (batailles précédentes)
        self.my_up = None
        self.foe_up = None
        self.win_pending = None
        self.flies = []
        self._after = None
        self.flips = 0
        self.war_count = 0
        self.winner = None
        self.phase = "idle"
        self.pause_t = 0.0
        self.msg = "Cliquez ou Espace pour lancer la bataille"
        self.msg_col = C.TEXT_LIGHT

    # ------------------------------------------------------------------
    # Piles
    # ------------------------------------------------------------------
    def _count(self, which):
        if which == "me":
            return len(self.my_pile) + len(self.my_won)
        return len(self.foe_pile) + len(self.foe_won)

    def _piles(self, which):
        return ((self.my_pile, self.my_won) if which == "me"
                else (self.foe_pile, self.foe_won))

    def _pile_pos(self, which):
        return self.MY_PILE if which == "me" else self.FOE_PILE

    def _draw_card(self, which):
        """Pioche la carte du dessus ; recompose la pioche à partir des gains
        (mélangés) si elle est vide. Renvoie None si le joueur n'a plus rien."""
        pile, won = self._piles(which)
        if not pile:
            if not won:
                return None
            random.shuffle(won)
            pile.extend(won)
            won.clear()
        return pile.popleft()

    # ------------------------------------------------------------------
    # Déroulement d'un duel
    # ------------------------------------------------------------------
    def _launch(self, flies, after):
        self.flies = flies
        self._after = after
        self.phase = "anim"

    def _start_battle(self):
        if self.phase != "idle" or self.flies:
            return
        mc = self._draw_card("me")
        fc = self._draw_card("foe")
        if mc is None or fc is None:
            if mc is not None:
                self.my_pile.appendleft(mc)
            if fc is not None:
                self.foe_pile.appendleft(fc)
            self._finish("foe" if mc is None else "me")
            return
        self.flips += 1
        self.my_up, self.foe_up = mc, fc
        self.msg = ""
        self._launch([
            Fly(fc, self.FOE_PILE, self.FOE_UP, reveal=True),
            Fly(mc, self.MY_PILE, self.MY_UP, reveal=True),
        ], self._resolve)

    def _resolve(self):
        vm, vf = card_value(self.my_up), card_value(self.foe_up)
        if vm == vf:
            self._war()
            return
        win = "me" if vm > vf else "foe"
        self.msg = ("Vous remportez le pli !" if win == "me"
                    else "L'adversaire remporte le pli")
        self.msg_col = C.HILITE if win == "me" else C.SUIT_RED
        # « showdown » : on laisse voir les deux cartes avant de ramasser
        self.win_pending = win
        self.phase = "showdown"
        self.pause_t = 0.9 if self.auto else 1.3

    def _war(self):
        self.war_count += 1
        self.msg = "BATAILLE !"
        self.msg_col = C.ACCENT
        # les cartes à égalité rejoignent le pot
        self.pot.append(self.my_up)
        self.pot.append(self.foe_up)
        self.my_up = self.foe_up = None
        flies = []
        # une carte face cachée chacun (si disponible)
        for which in ("foe", "me"):
            c = self._draw_card(which)
            if c is not None:
                self.pot.append(c)
                flies.append(Fly(c, self._pile_pos(which), self.POT,
                                 face_down=True))
        # une carte face visible (le décideur)
        fc = self._draw_card("foe")
        mc = self._draw_card("me")
        if mc is not None and fc is not None:
            self.flips += 1
            self.my_up, self.foe_up = mc, fc
            flies.append(Fly(fc, self.FOE_PILE, self.FOE_UP, reveal=True))
            flies.append(Fly(mc, self.MY_PILE, self.MY_UP, reveal=True))
            self._launch(flies, self._resolve)
            return
        # forfait : au moins un joueur ne peut pas fournir le décideur
        if mc is not None:
            self.pot.append(mc)
            flies.append(Fly(mc, self.MY_PILE, self.POT, face_down=True))
        if fc is not None:
            self.pot.append(fc)
            flies.append(Fly(fc, self.FOE_PILE, self.POT, face_down=True))
        if mc is None and fc is None:
            self._launch(flies, self._resolve_by_count)
        else:
            win = "me" if fc is None else "foe"
            self.msg = ("Vous remportez la bataille !" if win == "me"
                        else "L'adversaire remporte la bataille")
            self.msg_col = C.HILITE if win == "me" else C.SUIT_RED
            self._launch(flies, lambda: self._collect(win))

    def _collect(self, win):
        dest = self.MY_WON if win == "me" else self.FOE_WON
        cards, starts = list(self.pot), [self.POT] * len(self.pot)
        if self.foe_up is not None:
            cards.append(self.foe_up)
            starts.append(self.FOE_UP)
        if self.my_up is not None:
            cards.append(self.my_up)
            starts.append(self.MY_UP)
        flies = [Fly(c, s, dest, dur=0.3, face_down=True)
                 for c, s in zip(cards, starts)]
        won = self.my_won if win == "me" else self.foe_won
        grabbed = cards

        def done():
            won.extend(grabbed)
            self.pot.clear()
            self.my_up = self.foe_up = None
            self._after_collect()

        self._launch(flies, done)

    def _after_collect(self):
        if (self._count("me") == 0 or self._count("foe") == 0
                or self.flips >= self.MAX_BATTLES):
            self._resolve_by_count()
            return
        self.phase = "idle"
        self.pause_t = 0.55 if self.auto else 0.0

    def _resolve_by_count(self):
        mc, fc = self._count("me"), self._count("foe")
        self.winner = "me" if mc > fc else "foe" if fc > mc else "draw"
        self.msg = ""
        self.phase = "over"

    def _finish(self, winner):
        self.winner = winner
        self.msg = ""
        self.phase = "over"

    # ------------------------------------------------------------------
    # Événements / boucle
    # ------------------------------------------------------------------
    def handle_event(self, event):
        for b in self._buttons():
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            elif event.key == pygame.K_n:
                self.new_game()
            elif event.key == pygame.K_a:
                self._toggle_auto()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._advance()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not any(b.rect.collidepoint(event.pos) for b in self._buttons()):
                self._advance()

    def _advance(self):
        """Clic/Espace : lance un duel (repos) ou accélère le showdown."""
        if self.phase == "idle":
            self._start_battle()
        elif self.phase == "showdown":
            self._collect(self.win_pending)

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._buttons():
            b.update(dt, mouse)
        self.btn_auto.label = self._auto_label()

        if self.flies:
            done = True
            for f in self.flies:
                f.t += dt / f.dur
                if f.t < 1:
                    done = False
            if done:
                cb, self._after, self.flies = self._after, None, []
                if cb:
                    cb()
            return

        if self.phase == "showdown":
            self.pause_t -= dt
            if self.pause_t <= 0:
                self._collect(self.win_pending)
        elif self.phase == "idle" and self.auto:
            self.pause_t -= dt
            if self.pause_t <= 0:
                self._start_battle()

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------
    def draw(self, surface):
        ui.draw_felt(surface)
        self._draw_hud(surface)
        self._draw_pile(surface, self.FOE_PILE, len(self.foe_pile),
                        "Pioche adverse")
        self._draw_pile(surface, self.MY_PILE, len(self.my_pile),
                        "Votre pioche")
        self._draw_pile(surface, self.FOE_WON, len(self.foe_won),
                        "Gains adverse")
        self._draw_pile(surface, self.MY_WON, len(self.my_won),
                        "Vos gains")
        if self.pot:
            self._draw_pot(surface)

        flying = {id(f.card) for f in self.flies}
        if self.foe_up is not None and id(self.foe_up) not in flying:
            surface.blit(self.renderer.face(self.foe_up), self.FOE_UP)
        if self.my_up is not None and id(self.my_up) not in flying:
            surface.blit(self.renderer.face(self.my_up), self.MY_UP)
        for f in self.flies:
            self._draw_fly(surface, f)

        if self.msg:
            t = self.font.render(self.msg, True, self.msg_col)
            mx = (self.MY_UP[0] + self.cw + C.SCREEN_W) // 2   # à droite des cartes
            surface.blit(t, t.get_rect(center=(mx, self.mid_y)))

        for b in self._buttons():
            b.draw(surface)
        if self.phase == "over":
            self._draw_over(surface)

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        surface.blit(self.title_font.render("Bataille", True, C.TEXT_LIGHT),
                     (24, 10))
        info = f"Duel {self.flips}"
        if self.war_count:
            info += f"  ·  {self.war_count} bataille(s)"
        s = self.small.render(info, True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(self.cx, 23)))

    def _draw_pile(self, surface, pos, count, label):
        x, y = pos
        if count > 0:
            depth = min(5, 1 + count // 8)
            for i in range(depth):
                surface.blit(self.renderer.back, (x - i * 2, y - i * 2))
        else:
            surface.blit(self.renderer.slot, (x, y))
        badge = self.count_font.render(str(count), True, C.TEXT_LIGHT)
        br = badge.get_rect(center=(x + self.cw // 2, y + self.ch // 2))
        bg = br.inflate(20, 12)
        s = pygame.Surface(bg.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (18, 22, 28, 190), s.get_rect(), border_radius=10)
        surface.blit(s, bg.topleft)
        surface.blit(badge, br)
        lab = self.small.render(label, True, C.TEXT_DIM)
        surface.blit(lab, lab.get_rect(center=(x + self.cw // 2, y + self.ch + 18)))

    def _draw_pot(self, surface):
        x, y = self.POT
        n = min(6, len(self.pot))
        for i in range(n):
            surface.blit(self.renderer.back, (x + i * 7, y - i * 3))
        lab = self.tiny.render(f"Enjeu : {len(self.pot)}", True, C.ACCENT)
        surface.blit(lab, lab.get_rect(center=(x + self.cw // 2, y - n * 3 - 14)))

    def _draw_fly(self, surface, f):
        t = ui.ease_out_cubic(min(1, f.t))
        x = ui.lerp(f.start[0], f.target[0], t)
        y = ui.lerp(f.start[1], f.target[1], t)
        if f.reveal:
            p = min(1, f.t)
            scale = abs(1 - 2 * p)
            img = self.renderer.back if p < 0.5 else self.renderer.face(f.card)
            w = max(2, int(self.cw * scale))
            img = pygame.transform.smoothscale(img, (w, self.ch))
            surface.blit(img, (int(x + (self.cw - w) / 2), int(y)))
        else:
            img = self.renderer.back if f.face_down else self.renderer.face(f.card)
            surface.blit(img, (int(x), int(y)))

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 180))
        surface.blit(veil, (0, 0))
        if self.winner == "me":
            txt, col = "Victoire !", C.ACCENT
        elif self.winner == "foe":
            txt, col = "Défaite", C.SUIT_RED
        else:
            txt, col = "Égalité", C.TEXT_LIGHT
        t = self.big.render(txt, True, col)
        surface.blit(t, t.get_rect(center=(self.cx, 320)))
        det = self.font.render(
            f"Vous {self._count('me')}  —  {self._count('foe')} Adversaire"
            f"   ·   {self.flips} duels", True, C.TEXT_LIGHT)
        surface.blit(det, det.get_rect(center=(self.cx, 400)))
        for b in self.over_buttons:
            b.draw(surface)
