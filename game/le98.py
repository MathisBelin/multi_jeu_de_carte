"""Le 98 — jeu de défausse à total commun (variante du « 99 »).

2 à 10 joueurs (humain = siège 0, IA autonomes). Chacun a **4 cartes** ; la
**pioche** est au centre, face cachée. À son tour, on **pose une carte** (qui
modifie le total de la pile) puis on **repioche** pour revenir à 4. Le total ne
doit **jamais dépasser 98** : le joueur qui ne peut plus jouer sans le dépasser
**fait déborder la pile** et perd une vie (ou est éliminé en survie).

Valeurs des cartes :
- **2 à 10** : ajoutent leur valeur au total ;
- **As** : +1 **ou** +11 (au choix du joueur) ;
- **Valet** : aucune valeur (0), **inverse le sens** du jeu (« passe son tour ») ;
- **Dame** : **−10** au total ;
- **Roi** : place le total à **70**.

Modes : **normal** (3 vies) et **survie** (1 vie, min 3 joueurs) ; dans les deux
cas, le **dernier survivant gagne**.
"""
import math
import random

import pygame

from . import constants as C
from . import ui
from .cards import Card, CardRenderer
from .scene import Scene

NAMES = ["Vous", "Alice", "Bruno", "Carla", "David", "Elsa", "Hugo", "Inès",
         "Jules", "Kenza"]

RANK_FR = {1: "As", 11: "Valet", 12: "Dame", 13: "Roi"}

SAFE_COL = (150, 200, 130)
LOSER_COL = (210, 92, 92)
LIFE_COL = (224, 96, 96)


def rank_fr(rank):
    return RANK_FR.get(rank, str(rank))


class Fly:
    """Carte en vol (option retournement dos→face / rester face cachée)."""
    def __init__(self, card, start, target, dur=0.36, reveal=False,
                 face_down=False):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0
        self.reveal = reveal
        self.face_down = face_down


class FloatText:
    def __init__(self, text, pos, color, dur=1.1):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.dur = dur
        self.t = 0.0


class Le98Scene(Scene):
    LIMIT = 98
    KING_VALUE = 70
    MAX_MANCHE_TURNS = 220          # garde-fou anti-boucle (rarissime)

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(96, 136)
        self.mini = CardRenderer(46, 65)
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)
        self.big = pygame.font.SysFont(C.FONT_UI, 52, bold=True)
        self.total_font = pygame.font.SysFont(C.FONT_UI, 76, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 44, bold=True)

        self.cx = C.SCREEN_W // 2
        # pile jouée et pioche écartées symétriquement ; le total géant occupe
        # le vide central entre les deux (jamais masqué par un adversaire).
        self.PILE = (self.cx - 210, 244)
        self.STOCK = (self.cx + 114, 244)
        self.total_center = (self.cx, 300)

        self.N = 4
        self.survival = False
        self.phase = "setup"
        self.flies = []
        self._after = None
        self.floats = []
        self.banner = ""
        self.hold_t = 0.0
        self.think_t = 0.0
        self.pending_ace = None
        self.bust_seat = None
        self._build_buttons()

    # ------------------------------------------------------------------
    # Boutons
    # ------------------------------------------------------------------
    def _build_buttons(self):
        cx = self.cx
        self.btn_menu = ui.Button((C.SCREEN_W - 150, 16, 120, 40), "Menu",
                                  self.app.show_menu, self.small,
                                  fill=(150, 92, 92), text_col=C.TEXT_LIGHT)
        self.btn_minus = ui.Button((0, 0, 56, 56), "−", self._dec,
                                   self.num_font, fill=(96, 120, 150),
                                   text_col=C.TEXT_LIGHT)
        self.btn_plus = ui.Button((0, 0, 56, 56), "+", self._inc,
                                  self.num_font, fill=(96, 120, 150),
                                  text_col=C.TEXT_LIGHT)
        self.btn_mode = ui.Button((0, 0, 210, 44), self._mode_label(),
                                  self._toggle_mode, self.small,
                                  fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_start = ui.Button((cx - 130, 0, 260, 56), "Commencer",
                                   self.new_game, self.font)
        self.btn_ace1 = ui.Button((0, 0, 120, 48), "As = 1",
                                  lambda: self._choose_ace(1), self.small)
        self.btn_ace11 = ui.Button((0, 0, 120, 48), "As = 11",
                                   lambda: self._choose_ace(11), self.small,
                                   fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.over_buttons = [
            ui.Button((cx - 230, 596, 210, 52), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 596, 210, 52), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _mode_label(self):
        return "Survie" if self.survival else "Manche unique"

    def _dec(self):
        floor = 3 if self.survival else 2
        self.N = max(floor, self.N - 1)

    def _inc(self):
        self.N = min(10, self.N + 1)

    def _toggle_mode(self):
        self.survival = not self.survival
        if self.survival and self.N < 3:
            self.N = 3
        self.btn_mode.label = self._mode_label()

    def _cur_buttons(self):
        if self.phase == "setup":
            self._layout_setup()
            return [self.btn_minus, self.btn_plus, self.btn_mode,
                    self.btn_start, self.btn_menu]
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        if self.phase == "ace":
            self._place_ace_buttons()
            btns = [self.btn_menu]
            if self._ace_ok(1):
                btns.append(self.btn_ace1)
            if self._ace_ok(11):
                btns.append(self.btn_ace11)
            return btns
        return [self.btn_menu]

    # ---- écran de config ----
    def _layout_setup(self):
        self._panels, self._texts, self._dividers = [], [], []
        cx = self.cx
        pw = 660
        px = cx - pw // 2
        top, pad = 210, 22
        y = top + 54
        self._texts.append(("Nombre de joueurs", self.small, C.TEXT_LIGHT,
                            (px + pad, y + 14), "left"))
        floor = 3 if self.survival else 2
        self._texts.append((f"Vous + IA ({floor} à 10)", self.dfont, C.TEXT_DIM,
                            (px + pad, y + 40), "left"))
        gx = px + pw - pad - (56 + 80 + 56)
        self.btn_minus.rect.update(gx, y, 56, 56)
        self.btn_plus.rect.update(gx + 56 + 80, y, 56, 56)
        self._num_pos = (gx + 56 + 40, y + 28)
        y += 70
        self._dividers.append((px + pad, px + pw - pad, y)); y += 14
        md = ("Chaque perdant est éliminé ; on rejoue jusqu'au dernier (min 3)"
              if self.survival else "Une seule manche : le premier à déborder perd")
        self._texts.append(("Mode de jeu", self.small, C.TEXT_LIGHT,
                            (px + pad, y + 11), "left"))
        self._texts.append((md, self.dfont, C.TEXT_DIM, (px + pad, y + 54),
                            "left"))
        self.btn_mode.fill = ((196, 110, 78) if self.survival else (78, 148, 102))
        self.btn_mode.fill_hover = tuple(min(255, c + 24) for c in self.btn_mode.fill)
        self.btn_mode.label = self._mode_label()
        self.btn_mode.rect.update(px + pw - pad - 210, y, 210, 44)
        y += 82
        bottom = y + 6
        self._panels.append((pygame.Rect(px, top, pw, bottom - top),
                             "RÉGLAGES DE LA PARTIE", C.ACCENT))
        self.btn_start.rect.update(cx - 130, bottom + 30, 260, 56)

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def new_game(self):
        if self.survival and self.N < 3:
            self.N = 3
        self.alive = [True] * self.N
        self.elim_order = []
        self.direction = 1
        self.winner = None
        self.loser = None
        self.floats = []
        self.flies = []
        self._after = None
        self.pending_ace = None
        self._layout_seats()
        starter = random.randrange(self.N)
        self._deal_manche(starter)
        self._begin_turn()

    def _deal_manche(self, starter):
        deck = [Card(s, r, True) for s in C.SUITS for r in range(1, 14)]
        random.shuffle(deck)
        self.hands = [[] for _ in range(self.N)]
        for seat in range(self.N):
            if self.alive[seat]:
                for _ in range(4):
                    self.hands[seat].append(deck.pop())
        self.stock = deck
        self.discard = []
        self.pile_total = 0
        self.pile_top = None
        self.manche_turns = 0
        self.cur = starter if self.alive[starter] else self._next_alive(starter)

    # cercle des joueurs (humain en bas, adversaires sur l'arc supérieur)
    EC = (C.SCREEN_W // 2, 402)
    RX, RY = 552, 284

    def _layout_seats(self):
        self.pod_center = {0: (self.cx, C.SCREEN_H - 208)}
        opp = list(range(1, self.N))
        m = len(opp)
        for j, seat in enumerate(opp):
            ang = 90.0 if m == 1 else 200.0 - 220.0 * (j / (m - 1))
            rad = math.radians(ang)
            x = self.EC[0] + self.RX * math.cos(rad)
            y = self.EC[1] - self.RY * math.sin(rad)
            self.pod_center[seat] = (int(x), int(y))

    # ------------------------------------------------------------------
    # Règles / valeurs
    # ------------------------------------------------------------------
    def _result_total(self, card, ace_val=1):
        r = card.rank
        if r == 11:            # Valet : aucune valeur
            return self.pile_total
        if r == 12:            # Dame : −10
            return max(0, self.pile_total - 10)
        if r == 13:            # Roi : total = 70
            return self.KING_VALUE
        if r == 1:             # As : +1 ou +11
            return self.pile_total + ace_val
        return self.pile_total + r

    def _is_legal(self, card):
        if card.rank == 1:
            return self.pile_total + 1 <= self.LIMIT
        return self._result_total(card) <= self.LIMIT

    def _legal_cards(self, seat):
        return [c for c in self.hands[seat] if self._is_legal(c)]

    def _ace_ok(self, val):
        return self.pile_total + val <= self.LIMIT

    # ------------------------------------------------------------------
    # Tour de jeu
    # ------------------------------------------------------------------
    def _name(self, i):
        return NAMES[i] if i < len(NAMES) else f"Joueur {i}"

    def _alive_seats(self):
        return [i for i in range(self.N) if self.alive[i]]

    def _next_alive(self, seat):
        step = self.direction
        for s in range(1, self.N + 1):
            j = (seat + s * step) % self.N
            if j != seat and self.alive[j]:
                return j
        return seat

    def _begin_turn(self):
        alive = self._alive_seats()
        if len(alive) <= 1:
            self._finish(alive[0] if alive else None)
            return
        if not self.alive[self.cur]:
            self.cur = self._next_alive(self.cur)
        if not self._legal_cards(self.cur):
            self._bust(self.cur)
            return
        self.pending_ace = None
        if self.cur == 0:
            self.phase = "playing"
        else:
            self.phase = "ai_think"
            self.think_t = 0.75

    def _bust(self, seat):
        self.bust_seat = seat
        self.phase = "bust"
        self.hold_t = 1.7
        verb = "éliminé" if self.survival else "perdu"
        self.banner = f"{self._name(seat)} fait déborder la pile ({self.pile_total}) — {verb} !"
        pc = self.pod_center[seat]
        self.floats.append(FloatText("Déborde !", (pc[0], pc[1] - 60), LOSER_COL))

    def _resolve_bust(self):
        seat = self.bust_seat
        if not self.survival:
            # Manche unique : le premier à déborder a perdu, la partie s'arrête.
            self.loser = seat
            self.phase = "over"
            return
        # Survie : le joueur est éliminé, on rejoue tant qu'il en reste ≥ 2.
        self.alive[seat] = False
        self.elim_order.append(seat)
        alive = self._alive_seats()
        if len(alive) <= 1:
            self._finish(alive[0] if alive else None)
            return
        starter = self._next_alive(seat)
        self.banner = ""
        self._deal_manche(starter)
        self._begin_turn()

    # ---- poser une carte ----
    def _human_play(self, card):
        if self.phase != "playing" or self.cur != 0:
            return
        if not self._is_legal(card):
            return
        if card.rank == 1 and self._ace_ok(11) and self._ace_ok(1):
            self.pending_ace = card
            self.phase = "ace"
            return
        ace_val = 1 if card.rank == 1 else 1
        self._play_card(0, card, ace_val)

    def _choose_ace(self, val):
        if self.phase != "ace" or self.pending_ace is None:
            return
        card = self.pending_ace
        self.pending_ace = None
        self._play_card(0, card, val)

    def _place_ace_buttons(self):
        y = C.SCREEN_H - self.renderer.h - 150
        self.btn_ace1.rect.update(self.cx - 134, y, 120, 48)
        self.btn_ace11.rect.update(self.cx + 14, y, 120, 48)

    def _ai_choose(self, seat):
        """IA « agressive » : pousse le total le plus haut possible tout en
        restant ≤ 98 (elle refile la pression au suivant), et n'emploie une
        carte qui baisse le total (Dame/Roi) que si rien d'autre n'est légal.
        Résultat : la pile reste près de la limite → les débordements arrivent
        vite (sinon les manches ne finiraient jamais)."""
        legal = self._legal_cards(seat)
        best, best_total, best_ace = None, -1, 1
        for c in legal:
            if c.rank == 1:                   # As : viser +11 si possible
                for av in (11, 1):
                    if self._ace_ok(av):
                        rt = self.pile_total + av
                        if rt > best_total:
                            best, best_total, best_ace = c, rt, av
                        break
            else:
                rt = self._result_total(c)
                if rt > best_total:
                    best, best_total, best_ace = c, rt, 1
        return best, best_ace

    def _play_card(self, seat, card, ace_val=1):
        self.hands[seat].remove(card)
        self._played = (seat, card, ace_val)
        pc = self.pod_center[seat]
        start = (pc[0] - self.renderer.w // 2, pc[1] - self.renderer.h // 2)
        target = self.PILE
        reveal = (seat != 0)                  # les cartes des IA se révèlent
        fly = Fly(card, start, target, dur=0.42, reveal=reveal,
                  face_down=False)
        self._launch([fly], self._land_card)

    def _land_card(self):
        seat, card, ace_val = self._played
        if self.pile_top is not None:
            self.discard.append(self.pile_top)
        self.pile_top = card
        r = card.rank
        pc = self.pod_center[seat]
        if r == 11:                           # Valet : inverse le sens
            self.direction *= -1
            self.floats.append(FloatText("Sens inversé", (self.cx, 176),
                                          C.ACCENT))
        elif r == 12:
            self.pile_total = max(0, self.pile_total - 10)
        elif r == 13:
            self.pile_total = self.KING_VALUE
        elif r == 1:
            self.pile_total += ace_val
        else:
            self.pile_total += r
        self._draw_to(seat)

    def _draw_to(self, seat):
        if len(self.hands[seat]) >= 4:
            self._advance()
            return
        if not self.stock:
            self.stock = self.discard
            self.discard = []
            random.shuffle(self.stock)
        if not self.stock:
            self._advance()
            return
        card = self.stock.pop()
        pc = self.pod_center[seat]
        target = (pc[0] - self.renderer.w // 2, pc[1] - self.renderer.h // 2)
        reveal = (seat == 0)                  # l'humain découvre sa carte
        fly = Fly(card, self.STOCK, target, dur=0.34, reveal=reveal,
                  face_down=not reveal)
        self._drawn = (seat, card)
        self._launch([fly], self._land_draw)

    def _land_draw(self):
        seat, card = self._drawn
        self.hands[seat].append(card)
        self._advance()

    def _advance(self):
        self.manche_turns += 1
        if self.manche_turns > self.MAX_MANCHE_TURNS:
            self._bust(self.cur)              # garde-fou : la manche traîne
            return
        self.cur = self._next_alive(self.cur)
        self._begin_turn()

    def _finish(self, winner):
        self.winner = winner
        self.ranking = list(reversed(self.elim_order))
        if winner is not None and winner not in self.ranking:
            self.ranking.insert(0, winner)
        self.phase = "over"

    def _launch(self, flies, after):
        self.flies = flies
        self._after = after
        self.phase_anim_prev = self.phase
        self.phase = "anim"

    # ------------------------------------------------------------------
    # Événements / boucle
    # ------------------------------------------------------------------
    def handle_event(self, event):
        for b in self._cur_buttons():
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.phase == "playing" and self.cur == 0:
                for c, r in reversed(self._hand_slots()):
                    if r.collidepoint(event.pos):
                        self._human_play(c)
                        return

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._cur_buttons():
            b.update(dt, mouse)

        for f in self.floats:
            f.t += dt / f.dur
            f.y -= 22 * dt
        self.floats = [f for f in self.floats if f.t < 1]

        if self.phase == "anim":
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

        if self.phase == "bust":
            self.hold_t -= dt
            if self.hold_t <= 0:
                self._resolve_bust()
            return

        if self.phase == "ai_think":
            self.think_t -= dt
            if self.think_t <= 0:
                card, ace_val = self._ai_choose(self.cur)
                self._play_card(self.cur, card, ace_val)

    # ------------------------------------------------------------------
    # Géométrie de la main
    # ------------------------------------------------------------------
    def _hand_slots(self):
        if self.phase == "setup" or not getattr(self, "hands", None):
            return []
        hand = self.hands[0]
        cw, ch = self.renderer.w, self.renderer.h
        n = len(hand)
        if n == 0:
            return []
        spacing = 0 if n == 1 else min(int(cw * 1.08), (760 - cw) // (n - 1))
        total = spacing * (n - 1) + cw
        x0 = self.cx - total // 2
        y = C.SCREEN_H - ch - 40
        return [(hand[i], pygame.Rect(x0 + i * spacing, y, cw, ch))
                for i in range(n)]

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------
    def draw(self, surface):
        ui.draw_felt(surface)
        if self.phase == "setup":
            self._draw_setup(surface)
            for b in self._cur_buttons():
                b.draw(surface)
            return
        self._draw_hud(surface)
        self._draw_center(surface)
        self._draw_opponents(surface)
        self._draw_human(surface)
        for f in self.flies:
            self._draw_fly(surface, f)
        for f in self.floats:
            self._draw_float(surface, f)
        for b in self._cur_buttons():
            b.draw(surface)
        if self.phase == "ace":
            self._draw_ace_prompt(surface)
        if self.phase == "over":
            self._draw_over(surface)

    def _draw_setup(self, surface):
        cx = self.cx
        t = self.big.render("Le 98", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 104)))
        s = self.small.render("Ne faites pas déborder la pile au-dessus de 98",
                              True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 150)))
        for rect, title, accent in self._panels:
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 20, 26, 120), panel.get_rect(),
                             border_radius=16)
            pygame.draw.rect(panel, (255, 255, 255, 26), panel.get_rect(),
                             width=1, border_radius=16)
            surface.blit(panel, rect.topleft)
            hs = self.tiny.render(title, True, accent)
            surface.blit(hs, (rect.x + 22, rect.y + 16))
            pygame.draw.line(surface, accent, (rect.x + 22, rect.y + 38),
                             (rect.x + 22 + hs.get_width(), rect.y + 38), 2)
        for x1, x2, y in self._dividers:
            pygame.draw.line(surface, (74, 88, 100), (x1, y), (x2, y), 1)
        for text, font, color, pos, align in self._texts:
            surf = font.render(text, True, color)
            surface.blit(surf, surf.get_rect(center=pos) if align == "center"
                         else pos)
        num = self.num_font.render(str(self.N), True, C.TEXT_LIGHT)
        surface.blit(num, num.get_rect(center=self._num_pos))

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        mode = "Survie" if self.survival else "Manche unique"
        surface.blit(self.title_font.render(f"Le 98 — {mode}", True,
                                            C.TEXT_LIGHT), (24, 10))
        msg = self.banner
        if not msg:
            if self.phase == "playing" and self.cur == 0:
                msg = "À vous : posez une carte (les injouables sont grisées)"
            elif self.phase == "ace":
                msg = "Choisissez la valeur de votre As"
            elif self.cur is not None and self.phase in ("ai_think", "anim"):
                msg = f"{self._name(self.cur)} joue…"
        if msg:
            col = LOSER_COL if self.phase == "bust" else C.ACCENT
            s = self.small.render(msg, True, col)
            surface.blit(s, s.get_rect(center=(self.cx, 23)))

    def _draw_center(self, surface):
        flying = {id(f.card) for f in self.flies}
        cw, ch = self.renderer.w, self.renderer.h

        def label(txt, cx0, y):
            s = self.tiny.render(txt, True, C.TEXT_DIM)
            surface.blit(s, s.get_rect(center=(cx0, y)))

        # pioche
        sx, sy = self.STOCK
        surface.blit(self.renderer.back if self.stock else self.renderer.slot,
                     (sx, sy))
        label("Pioche", sx + cw // 2, sy + ch + 14)
        # pile jouée
        px, py = self.PILE
        surface.blit(self.renderer.slot, (px, py))
        if self.pile_top is not None and id(self.pile_top) not in flying:
            surface.blit(self.renderer.face(self.pile_top), (px, py))
        label("Pile", px + cw // 2, py + ch + 14)

        # total géant au centre + « / 98 » + sens du jeu
        danger = self.pile_total >= 85
        col = LOSER_COL if danger else (C.ACCENT if self.pile_total >= 70
                                        else C.TEXT_LIGHT)
        num = self.total_font.render(str(self.pile_total), True, col)
        surface.blit(num, num.get_rect(center=(self.total_center[0],
                                               self.total_center[1])))
        arrow = "sens horaire" if self.direction == 1 else "sens anti-horaire"
        sub = self.small.render(f"/ 98    ·    {arrow}", True, C.TEXT_DIM)
        surface.blit(sub, sub.get_rect(center=(self.total_center[0],
                                               self.total_center[1] + 54)))

    def _draw_opponents(self, surface):
        flying = {id(f.card) for f in self.flies}
        for seat in range(1, self.N):
            cxp, cyp = self.pod_center[seat]
            n = len(self.hands[seat])
            alive = self.alive[seat]
            if alive and n > 0:
                show = n
                fw = self.mini.w
                sp = 20
                total = fw + (show - 1) * sp
                x0 = cxp - total // 2
                for i in range(show):
                    surface.blit(self.mini.back,
                                 (x0 + i * sp, cyp - self.mini.h // 2))
            r = pygame.Rect(0, 0, 158, 52)
            r.center = (cxp, cyp + 58)
            drawer = (seat == self.cur and alive
                      and self.phase in ("ai_think", "anim", "bust"))
            bg = (70, 96, 120) if drawer else (46, 62, 78) if alive else (38, 40, 44)
            pygame.draw.rect(surface, bg, r, border_radius=10)
            edge = C.ACCENT if drawer else (90, 100, 110)
            pygame.draw.rect(surface, edge, r, width=2 if drawer else 1,
                             border_radius=10)
            surface.blit(self.small.render(self._name(seat), True,
                         C.TEXT_LIGHT if alive else C.TEXT_DIM),
                         (r.x + 12, r.y + 4))
            if alive:
                surface.blit(self.tiny.render(f"{n} carte(s)", True, C.TEXT_DIM),
                             (r.x + 12, r.y + 30))
            else:
                surface.blit(self.tiny.render("Éliminé", True, LOSER_COL),
                             (r.x + 12, r.y + 30))

    def _draw_human(self, surface):
        flying = {id(f.card) for f in self.flies}
        slots = self._hand_slots()
        legal_ids = {id(c) for c in self._legal_cards(0)} if self.alive[0] else set()
        my_turn = (self.cur == 0 and self.phase in ("playing", "ace"))
        for c, r in slots:
            if id(c) in flying:
                continue
            surface.blit(self.renderer.face(c), r.topleft)
            if my_turn and id(c) not in legal_ids:
                veil = pygame.Surface(r.size, pygame.SRCALPHA)
                veil.fill((10, 14, 18, 150))
                surface.blit(veil, r.topleft)
            elif my_turn and id(c) in legal_ids:
                pygame.draw.rect(surface, C.HILITE, r.inflate(6, 6),
                                 width=3, border_radius=12)
        # plaque humain
        r = pygame.Rect(0, 0, 220, 48)
        r.center = (150, C.SCREEN_H - 30)
        drawer = (self.cur == 0 and self.phase in ("playing", "ace"))
        bg = (70, 96, 120) if drawer else (46, 62, 78) if self.alive[0] else (38, 40, 44)
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, C.ACCENT if drawer else (90, 100, 110), r,
                         width=2 if drawer else 1, border_radius=10)
        surface.blit(self.small.render("Vous", True,
                     C.TEXT_LIGHT if self.alive[0] else C.TEXT_DIM),
                     (r.x + 12, r.y + 4))
        if self.alive[0]:
            surface.blit(self.tiny.render(f"{len(self.hands[0])} carte(s)", True,
                         C.TEXT_DIM), (r.x + 12, r.y + 27))
        else:
            surface.blit(self.tiny.render("Éliminé", True, LOSER_COL),
                         (r.x + 12, r.y + 27))

    def _draw_ace_prompt(self, surface):
        s = self.small.render("As : 1 ou 11 ?", True, C.ACCENT)
        y = C.SCREEN_H - self.renderer.h - 176
        surface.blit(s, s.get_rect(center=(self.cx, y)))

    def _draw_fly(self, surface, f):
        t = ui.ease_out_cubic(min(1, f.t))
        x = ui.lerp(f.start[0], f.target[0], t)
        y = ui.lerp(f.start[1], f.target[1], t)
        cw, ch = self.renderer.w, self.renderer.h
        if f.reveal:
            p = min(1, f.t)
            scale = abs(1 - 2 * p)
            img = self.renderer.back if p < 0.5 else self.renderer.face(f.card)
            w = max(2, int(cw * scale))
            img = pygame.transform.smoothscale(img, (w, ch))
            surface.blit(img, (int(x + (cw - w) / 2), int(y)))
        else:
            img = self.renderer.back if f.face_down else self.renderer.face(f.card)
            surface.blit(img, (int(x), int(y)))

    def _draw_float(self, surface, f):
        alpha = int(255 * (1 - f.t))
        surf = self.font.render(f.text, True, f.color)
        surf.set_alpha(alpha)
        surface.blit(surf, surf.get_rect(center=(int(f.x), int(f.y))))

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 185))
        surface.blit(veil, (0, 0))
        cx = self.cx
        if not self.survival:
            # manche unique : un seul perdant, les autres survivent
            if self.loser == 0:
                txt, col = "Vous avez perdu !", LOSER_COL
            elif self.loser is not None:
                txt, col = f"{self._name(self.loser)} a perdu !", C.ACCENT
            else:
                txt, col = "Match nul", C.TEXT_LIGHT
            t = self.big.render(txt, True, col)
            surface.blit(t, t.get_rect(center=(cx, 160)))
            sub = self.small.render("… en faisant déborder la pile au-dessus de 98",
                                    True, C.TEXT_DIM)
            surface.blit(sub, sub.get_rect(center=(cx, 218)))
            y = 288
            for seat in range(self.N):
                if seat == self.loser:
                    continue
                s = self.font.render(f"{self._name(seat)} · sauvé", True, SAFE_COL)
                surface.blit(s, s.get_rect(center=(cx, y)))
                y += 40
            for b in self.over_buttons:
                b.draw(surface)
            return
        # survie : un grand gagnant + ordre d'élimination
        if self.winner == 0:
            txt, col = "Vous gagnez la survie !", C.ACCENT
        elif self.winner is not None:
            txt, col = f"{self._name(self.winner)} gagne la survie !", C.ACCENT
        else:
            txt, col = "Match nul", C.TEXT_LIGHT
        t = self.big.render(txt, True, col)
        surface.blit(t, t.get_rect(center=(cx, 160)))
        y = 250
        for place, seat in enumerate(self.ranking):
            name = self._name(seat)
            if seat == self.winner:
                line, col = f"1.  {name} · survivant", SAFE_COL
            else:
                line, col = f"{place + 1}.  {name} · éliminé", C.TEXT_DIM
            s = self.font.render(line, True, col)
            surface.blit(s, s.get_rect(center=(cx, y)))
            y += 42
        for b in self.over_buttons:
            b.draw(surface)
