"""Spider Solitaire : logique de jeu, glisser-deposer et animations.

Deux jeux (104 cartes), 10 colonnes. On construit des suites descendantes
(n'importe quelle enseigne), mais seule une suite de MEME enseigne se deplace
d'un bloc. Une suite complete Roi -> As de la meme enseigne part en fondation.
Huit fondations = victoire. Difficulte = 1, 2 ou 4 enseignes.
"""
import random
import pygame

from . import constants as C
from . import ui
from .cards import Card, CardRenderer
from .scene import Scene


# Enseignes utilisees selon la difficulte (le paquet fait toujours 104 cartes
# = 8 suites completes : 1 enseigne -> 8 fois, 2 -> 4 fois chacune, 4 -> 2 fois).
SUIT_SETS = {
    1: [C.SPADE],
    2: [C.SPADE, C.HEART],
    4: [C.SPADE, C.HEART, C.DIAMOND, C.CLUB],
}
DIFF_LABEL = {1: "1 couleur", 2: "2 couleurs", 4: "4 couleurs"}


# --------------------------------------------------------------------------
class Col:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.cards = []

    def top(self):
        return self.cards[-1] if self.cards else None


class Move:
    """Animation de deplacement d'une carte.

    dest_col non nul  -> la cible suit l'eventail de la colonne (calculee au vol).
    sinon dest_pos    -> position absolue (fondation).
    """
    def __init__(self, card, start, dest_col=None, dest_pos=None, dur=0.14,
                 delay=0.0, flip_on_arrive=False, on_done=None):
        self.card = card
        self.start = start
        self.dest_col = dest_col
        self.dest_pos = dest_pos
        self.dur = dur
        self.delay = delay
        self.t = 0.0
        self.flip = flip_on_arrive
        self.on_done = on_done


class Flip:
    """Retournement en place d'une carte qui se decouvre."""
    def __init__(self, card, pos, on_done=None):
        self.card = card
        self.pos = pos
        self.t = 0.0
        self.dur = 0.22
        self.on_done = on_done
        self._flipped = False


class Confetti:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-160, 160)
        self.vy = random.uniform(-520, -260)
        self.g = random.uniform(420, 620)
        self.size = random.randint(6, 12)
        self.rot = random.uniform(0, 360)
        self.vrot = random.uniform(-320, 320)
        self.color = random.choice([
            C.ACCENT, C.SUIT_RED, C.HILITE, (90, 160, 240),
            (250, 250, 252), (240, 130, 60)])
        self.life = random.uniform(2.4, 4.0)


# --------------------------------------------------------------------------
class SpiderScene(Scene):
    FAN_UP = 26          # decalage vertical entre 2 cartes face visible
    FAN_DOWN = 12        # ... entre 2 cartes face cachee
    GRAB_THRESHOLD = 6

    def __init__(self, app):
        super().__init__(app)
        # cartes plus compactes que le Klondike (10 colonnes a caser)
        self.cw, self.ch = 92, 130
        self.renderer = CardRenderer(self.cw, self.ch)
        self.mini = CardRenderer(int(self.cw * 0.52), int(self.ch * 0.52))
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15)
        self.big = pygame.font.SysFont(C.FONT_UI, 64, bold=True)
        self.h_font = pygame.font.SysFont(C.FONT_UI, 40, bold=True)
        self.num_suits = 1
        self._build_layout()
        self._build_buttons()
        # etat minimal avant la premiere partie (ecran de choix de difficulte)
        self.phase = "setup"
        self._reset_state()

    # ---- mise en place geometrique ----
    def _build_layout(self):
        n = 10
        pitch = self.cw + 24
        total = (n - 1) * pitch + self.cw
        self.left = (C.SCREEN_W - total) // 2
        self.pitch = pitch
        self.top_strip = 18
        self.tab_y = 168
        self.toolbar_y = C.SCREEN_H - 56
        self.play_bottom = self.toolbar_y - 12
        self.cols = [Col(self.left + i * pitch, self.tab_y) for i in range(n)]
        # pioche (coin haut droit) : pile de dos qui se distribuent
        self.stock_pos = (C.SCREEN_W - self.cw - 46, self.top_strip)
        self.stock_rect = pygame.Rect(self.stock_pos[0] - 24, self.stock_pos[1],
                                      self.cw + 24, self.ch)
        # fondations (coin haut gauche) : 8 emplacements en cartes miniatures
        self.found_gap = self.mini.w + 8
        self.found_y = self.top_strip + 8

    def _found_pos(self, i):
        return (self.left + i * self.found_gap, self.found_y)

    def _build_buttons(self):
        y = self.toolbar_y
        f = self.small
        self.buttons = [
            ui.Button((40, y, 140, 40), "Nouvelle", self.new_game, f),
            ui.Button((188, y, 130, 40), "Difficulté", self.to_setup, f,
                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT),
            ui.Button((326, y, 120, 40), "Annuler", self.undo, f,
                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT),
            ui.Button((C.SCREEN_W - 160, y, 120, 40), "Menu",
                      self.app.show_menu, f,
                      fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]
        self.btn_undo = self.buttons[2]
        # ecran de choix de difficulte
        cx = C.SCREEN_W // 2
        bw, bh = 300, 70
        self.setup_buttons = [
            ui.Button((cx - bw // 2, 320, bw, bh),
                      "1 couleur  —  facile", lambda: self.start(1), self.font),
            ui.Button((cx - bw // 2, 406, bw, bh),
                      "2 couleurs  —  moyen", lambda: self.start(2), self.font,
                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT),
            ui.Button((cx - bw // 2, 492, bw, bh),
                      "4 couleurs  —  difficile", lambda: self.start(4), self.font,
                      fill=(150, 108, 92), text_col=C.TEXT_LIGHT),
            ui.Button((cx - 90, 600, 180, 46), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]
        self.win_buttons = [
            ui.Button((cx - 220, 470, 200, 52), "Rejouer",
                      self.new_game, self.font),
            ui.Button((cx + 20, 470, 200, 52), "Menu",
                      self.app.show_menu, self.font,
                      fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _reset_state(self):
        self.anims = []
        self.flips = []
        self.flying = set()
        self.drag = None
        self._press = None
        self._pre = None
        self.undo_stack = []
        self.stock_cards = []
        self.foundations = []      # liste d'enseignes des suites terminees
        self.moves = 0
        self.score = 500
        self.elapsed = 0.0
        self.timer_on = False
        self.won = False
        self.dealing = False
        self.confetti = []
        self.mouse = (0, 0)
        self.toast_text = ""
        self.toast_t = 0.0
        self._last_click_t = -1
        self._last_click_card = None

    # ---- transitions d'ecran ----
    def to_setup(self):
        self.phase = "setup"

    def start(self, num_suits):
        self.num_suits = num_suits
        self.new_game()

    # ---- nouvelle partie ----
    def new_game(self):
        suits = SUIT_SETS[self.num_suits]
        copies = 8 // len(suits)
        deck = [Card(s, r) for _ in range(copies)
                for s in suits for r in range(1, 14)]
        random.shuffle(deck)

        for c in self.cols:
            c.cards = []
        self._reset_state()
        self.phase = "playing"

        dealt = deck[:54]
        self.stock_cards = deck[54:]           # 50 cartes = 5 distributions
        self.dealing = True
        idx = 0
        delay = 0.0
        start = self.stock_pos
        for ci in range(10):
            count = 6 if ci < 4 else 5
            for k in range(count):
                card = dealt[idx]; idx += 1
                face_up = (k == count - 1)
                self.cols[ci].cards.append(card)
                self.flying.add(card)
                self.anims.append(Move(card, start, dest_col=self.cols[ci],
                                       dur=0.24, delay=delay,
                                       flip_on_arrive=face_up))
                delay += 0.018

    # ------------------------------------------------------------------
    # Geometrie
    # ------------------------------------------------------------------
    def fan(self, col):
        up, down = self.FAN_UP, self.FAN_DOWN
        n = len(col.cards)
        if n <= 1:
            return up, down
        n_down = sum(1 for c in col.cards[:-1] if not c.face_up)
        n_up = (n - 1) - n_down
        span = n_down * down + n_up * up
        max_span = max(1, self.play_bottom - col.y - self.ch)
        if span > max_span:
            s = max_span / span
            up *= s; down *= s
        return up, down

    def col_positions(self, col):
        up, down = self.fan(col)
        pos = []
        y = col.y
        for c in col.cards:
            pos.append((col.x, y))
            y += up if c.face_up else down
        return pos

    def card_target(self, card, col):
        try:
            i = col.cards.index(card)
        except ValueError:
            return (col.x, col.y)
        return self.col_positions(col)[i]

    def drop_rect(self, col):
        pos = self.col_positions(col)
        bottom = (pos[-1][1] + self.ch) if pos else (col.y + self.ch)
        return pygame.Rect(col.x, col.y, self.cw, bottom - col.y)

    # ------------------------------------------------------------------
    # Regles
    # ------------------------------------------------------------------
    def is_run(self, cards):
        """Bloc deplacable : meme enseigne, descendant, tout face visible."""
        if not cards or not cards[0].face_up:
            return False
        for a, b in zip(cards, cards[1:]):
            if not (a.face_up and b.face_up
                    and a.suit == b.suit and b.rank == a.rank - 1):
                return False
        return True

    def can_drop(self, col, card):
        if not col.cards:
            return True
        top = col.top()
        return top.face_up and card.rank == top.rank - 1

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def busy(self):
        return bool(self.anims) or bool(self.flips)

    def handle_event(self, event):
        if self.phase == "setup":
            for b in self.setup_buttons:
                if b.handle(event):
                    return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            return
        if self.won:
            for b in self.win_buttons:
                b.handle(event)
            return
        for b in self.buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            elif event.key == pygame.K_u:
                self.undo()
            elif event.key == pygame.K_n:
                self.new_game()
            elif event.key == pygame.K_SPACE and not self.busy() and not self.dealing:
                self.deal_stock()
            return
        if self.dealing:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_press(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            self.on_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.on_release(event.pos)

    def hit_card(self, pos):
        for col in self.cols:
            positions = self.col_positions(col)
            for i in range(len(col.cards) - 1, -1, -1):
                c = col.cards[i]
                if c in self.flying:
                    continue
                rect = pygame.Rect(positions[i], (self.cw, self.ch))
                if rect.collidepoint(pos):
                    return col, i
        return None

    def on_press(self, pos):
        if self.busy():
            return
        if self.stock_rect.collidepoint(pos) and self.stock_cards:
            self._press = ("stock",)
            return
        hit = self.hit_card(pos)
        if hit:
            self._press = ("card", hit[0], hit[1], pos)
        else:
            self._press = None

    def on_motion(self, pos):
        if self.drag:
            return
        if self._press and self._press[0] == "card":
            _, col, idx, start = self._press
            if abs(pos[0] - start[0]) + abs(pos[1] - start[1]) > self.GRAB_THRESHOLD:
                self.begin_drag(col, idx, pos)

    def begin_drag(self, col, idx, pos):
        cards = col.cards[idx:]
        if not self.is_run(cards):
            self._press = None
            return
        self._pre = self.snapshot()
        top_pos = self.col_positions(col)[idx]
        self.drag = {
            "cards": cards,
            "source": col,
            "gdx": top_pos[0] - pos[0],
            "gdy": top_pos[1] - pos[1],
            "off": self.FAN_UP,
        }
        del col.cards[idx:]

    def drag_positions(self):
        d = self.drag
        return [(self.mouse[0] + d["gdx"], self.mouse[1] + d["gdy"] + i * d["off"])
                for i in range(len(d["cards"]))]

    def find_drop(self, drag, pos):
        d = drag
        top_rect = pygame.Rect(self.mouse[0] + d["gdx"],
                               self.mouse[1] + d["gdy"], self.cw, self.ch)
        best, best_area = None, 0
        for col in self.cols:
            r = self.drop_rect(col).clip(top_rect)
            area = r.width * r.height
            if area > best_area:
                best_area = area
                best = col
        return best if best_area > 0 else None

    def on_release(self, pos):
        if self.drag:
            self.finish_drag(pos)
        elif self._press:
            if self._press[0] == "stock":
                self.deal_stock()
            elif self._press[0] == "card":
                self.card_click(self._press[1], self._press[2])
        self._press = None

    def finish_drag(self, pos):
        drag = self.drag
        self.drag = None
        cards = drag["cards"]
        starts = [(self.mouse[0] + drag["gdx"],
                   self.mouse[1] + drag["gdy"] + i * drag["off"])
                  for i in range(len(cards))]
        target = self.find_drop(drag, pos)
        if target and target is not drag["source"] and self.can_drop(target, cards[0]):
            self.undo_stack.append(self._pre)
            for c in cards:
                target.cards.append(c)
            self.animate_settle(cards, starts, target, then=self._after_settle)
            self.after_move(drag["source"])
            self.moves += 1
            self.score = max(0, self.score - 1)
            self.timer_on = True
        else:
            src = drag["source"]
            for c in cards:
                src.cards.append(c)
            self.animate_settle(cards, starts, src)

    def after_move(self, source):
        """Retourne la carte decouverte au sommet de la colonne source."""
        if source.cards:
            top = source.top()
            if not top.face_up:
                pos = self.col_positions(source)[-1]
                self.flips.append(Flip(top, pos))

    # ---- double-clic : deplacement automatique ----
    def card_click(self, col, idx):
        now = pygame.time.get_ticks() / 1000.0
        card = col.cards[idx]
        double = (now - self._last_click_t < 0.35 and self._last_click_card is card)
        self._last_click_t = now
        self._last_click_card = card
        if double:
            self.auto_move(col, idx)

    def auto_move(self, col, idx):
        cards = col.cards[idx:]
        if not self.is_run(cards):
            return False
        target = self._best_target(col, cards[0])
        if target is None:
            return False
        self._pre = self.snapshot()
        self.undo_stack.append(self._pre)
        starts = [self.col_positions(col)[idx + i] for i in range(len(cards))]
        del col.cards[idx:]
        for c in cards:
            target.cards.append(c)
        self.animate_settle(cards, starts, target, then=self._after_settle)
        self.after_move(col)
        self.moves += 1
        self.score = max(0, self.score - 1)
        self.timer_on = True
        return True

    def _best_target(self, source, card):
        """Meilleure colonne d'accueil : meme enseigne d'abord, puis toute
        colonne compatible non vide, puis une colonne vide."""
        same, other, empty = None, None, None
        for col in self.cols:
            if col is source:
                continue
            if not col.cards:
                if empty is None:
                    empty = col
                continue
            top = col.top()
            if top.face_up and card.rank == top.rank - 1:
                if top.suit == card.suit and same is None:
                    same = col
                elif other is None:
                    other = col
        return same or other or empty

    # ---- pioche ----
    def deal_stock(self):
        if self.busy() or self.dealing or not self.stock_cards:
            return
        if any(not c.cards for c in self.cols):
            self._toast("Chaque colonne doit avoir au moins une carte")
            return
        self.undo_stack.append(self.snapshot())
        delay = 0.0
        n = len(self.cols)
        for i, col in enumerate(self.cols):
            card = self.stock_cards.pop()
            card.face_up = True
            col.cards.append(card)
            self.flying.add(card)
            done = self._after_settle if i == n - 1 else None
            self.anims.append(Move(card, self.stock_pos, dest_col=col,
                                   dur=0.2, delay=delay, on_done=done))
            delay += 0.03
        self.moves += 1
        self.timer_on = True

    # ---- suites terminees ----
    def _scan_completed(self):
        for col in self.cols:
            cards = col.cards
            if len(cards) < 13:
                continue
            last = cards[-13:]
            if not all(c.face_up for c in last):
                continue
            suit = last[0].suit
            if all(c.suit == suit for c in last) and \
                    [c.rank for c in last] == list(range(13, 0, -1)):
                return col, last
        return None

    def _after_settle(self):
        res = self._scan_completed()
        if not res:
            self._check_win()
            return
        col, cards = res
        base = len(col.cards) - len(cards)
        starts = [self.col_positions(col)[base + k] for k in range(len(cards))]
        del col.cards[base:]
        n = len(self.foundations)
        self.foundations.append(cards[0].suit)
        self.score += 100
        fx, fy = self._found_pos(n)
        for c in cards:
            self.flying.add(c)
        m = len(cards)
        for k, (card, start) in enumerate(zip(cards, starts)):
            done = self._after_complete if k == m - 1 else None
            self.anims.append(Move(card, start, dest_pos=(fx + k * 2, fy),
                                   dur=0.22, delay=k * 0.02, on_done=done))
        # retourne la carte decouverte sous la suite retiree
        if col.cards and not col.top().face_up:
            self.flips.append(Flip(col.top(), self.col_positions(col)[-1]))

    def _after_complete(self):
        # une suite retiree peut en decouvrir une autre : on rescanne
        self._after_settle()

    def _check_win(self):
        if not self.won and len(self.foundations) >= 8:
            self.win()

    # ------------------------------------------------------------------
    # Undo / snapshot
    # ------------------------------------------------------------------
    def snapshot(self):
        return {
            "cols": [[(c.suit, c.rank, c.face_up) for c in col.cards]
                     for col in self.cols],
            "stock": [(c.suit, c.rank) for c in self.stock_cards],
            "found": list(self.foundations),
            "moves": self.moves,
            "score": self.score,
        }

    def restore(self, snap):
        for col, cards in zip(self.cols, snap["cols"]):
            col.cards = [Card(s, r, f) for (s, r, f) in cards]
        self.stock_cards = [Card(s, r, False) for (s, r) in snap["stock"]]
        self.foundations = list(snap["found"])
        self.moves = snap["moves"]
        self.score = snap["score"]

    def undo(self):
        if self.dealing or not self.undo_stack:
            return
        self.anims = []
        self.flips = []
        self.flying = set()
        self.drag = None
        self.restore(self.undo_stack.pop())

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------
    def animate_settle(self, cards, starts, dest_col, dur=0.14, then=None):
        n = len(cards)
        for i, (card, start) in enumerate(zip(cards, starts)):
            self.flying.add(card)
            done = then if i == n - 1 else None
            self.anims.append(Move(card, start, dest_col=dest_col, dur=dur,
                                   on_done=done))

    def _toast(self, text):
        self.toast_text = text
        self.toast_t = 2.2

    def win(self):
        self.won = True
        self.timer_on = False
        for _ in range(180):
            self.confetti.append(
                Confetti(random.randint(0, C.SCREEN_W), random.randint(-200, 0)))

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        if self.phase == "setup":
            for b in self.setup_buttons:
                b.update(dt, mouse)
            return
        for b in (self.win_buttons if self.won else self.buttons):
            b.update(dt, mouse)
        if not self.won:
            self.btn_undo.enabled = bool(self.undo_stack)

        if self.timer_on and not self.won:
            self.elapsed += dt
        if self.toast_t > 0:
            self.toast_t -= dt

        # deplacements
        done = []
        for m in self.anims:
            if m.delay > 0:
                m.delay -= dt
                continue
            m.t += dt / m.dur
            if m.t >= 1.0:
                done.append(m)
        for m in done:
            self.anims.remove(m)
            self.flying.discard(m.card)
            if m.flip:
                m.card.face_up = True
            if m.on_done:
                m.on_done()
        if self.dealing and not self.anims:
            self.dealing = False

        # retournements
        fdone = []
        for fl in self.flips:
            fl.t += dt / fl.dur
            if fl.t >= 0.5 and not fl._flipped:
                fl.card.face_up = True
                fl._flipped = True
            if fl.t >= 1.0:
                fdone.append(fl)
        for fl in fdone:
            self.flips.remove(fl)
            if fl.on_done:
                fl.on_done()

        # confettis
        for p in self.confetti:
            p.vy += p.g * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.vrot * dt
            p.life -= dt
        self.confetti = [p for p in self.confetti
                         if p.life > 0 and p.y < C.SCREEN_H + 40]

    # ------------------------------------------------------------------
    # Rendu
    # ------------------------------------------------------------------
    def draw(self, surface):
        ui.draw_felt(surface)
        if self.phase == "setup":
            self._draw_setup(surface)
            return

        self._draw_slots(surface)
        self._draw_foundations(surface)
        self._draw_stock(surface)
        for col in self.cols:
            self._draw_col(surface, col)
        for fl in self.flips:
            self._draw_flip(surface, fl)
        for m in self.anims:
            if m.delay > 0:
                continue
            self._draw_move(surface, m)
        if self.drag:
            self._draw_drop_hint(surface)
            self._draw_drag(surface)

        self._draw_header(surface)
        self._draw_hud(surface)
        for b in self.buttons:
            b.draw(surface)
        self._draw_toast(surface)
        if self.won:
            self._draw_win(surface)
        self._draw_confetti(surface)

    def _draw_slots(self, surface):
        for col in self.cols:
            surface.blit(self.renderer.slot, (col.x, col.y))

    def _blit_card(self, surface, card, pos, shadow=True):
        if shadow:
            g = 6
            surface.blit(self.renderer.shadow, (pos[0] - g, pos[1] - g))
        surface.blit(self.renderer.surface(card), pos)

    def _draw_col(self, surface, col):
        positions = self.col_positions(col)
        drag_cards = self.drag["cards"] if self.drag else ()
        for i, card in enumerate(col.cards):
            if card in self.flying or card in drag_cards:
                continue
            if any(fl.card is card for fl in self.flips):
                continue
            top = (i == len(col.cards) - 1)
            self._blit_card(surface, card, positions[i], shadow=top)

    def _draw_move(self, surface, m):
        if m.dest_col is not None:
            target = self.card_target(m.card, m.dest_col)
        else:
            target = m.dest_pos
        t = ui.ease_out_cubic(min(1.0, m.t))
        x = ui.lerp(m.start[0], target[0], t)
        y = ui.lerp(m.start[1], target[1], t)
        self._blit_card(surface, m.card, (x, y))

    def _draw_flip(self, surface, fl):
        scale = abs(1 - 2 * fl.t)
        surf = self.renderer.surface(fl.card)
        w = max(1, int(self.cw * scale))
        scaled = pygame.transform.smoothscale(surf, (w, self.ch))
        x = fl.pos[0] + (self.cw - w) // 2
        surface.blit(scaled, (x, fl.pos[1]))

    def _draw_drop_hint(self, surface):
        target = self.find_drop(self.drag, pygame.mouse.get_pos())
        if target and self.can_drop(target, self.drag["cards"][0]):
            r = self.drop_rect(target).inflate(6, 6)
            glow = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C.HILITE, 70), glow.get_rect(),
                             border_radius=C.CARD_RADIUS + 2)
            pygame.draw.rect(glow, (*C.HILITE, 200), glow.get_rect(), width=3,
                             border_radius=C.CARD_RADIUS + 2)
            surface.blit(glow, r.topleft)

    def _draw_drag(self, surface):
        for card, pos in zip(self.drag["cards"], self.drag_positions()):
            self._blit_card(surface, card, pos)

    def _draw_foundations(self, surface):
        for i in range(8):
            x, y = self._found_pos(i)
            surface.blit(self.mini.slot, (x, y))
            if i < len(self.foundations):
                card = Card(self.foundations[i], 13, True)
                surface.blit(self.mini.surface(card), (x, y))

    def _draw_stock(self, surface):
        deals = len(self.stock_cards) // 10
        bx, by = self.stock_pos
        if deals == 0:
            surface.blit(self.renderer.slot, (bx, by))
            return
        for k in range(deals):
            surface.blit(self.renderer.back, (bx - k * 6, by))

    def _draw_header(self, surface):
        done = len(self.foundations)
        title = self.small.render(
            f"Spider  ·  {DIFF_LABEL[self.num_suits]}", True, C.TEXT_DIM)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 34)))
        sub = self.font.render(f"Réussites  {done} / 8", True, C.ACCENT)
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 66)))

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, C.SCREEN_H - self.toolbar_y + 14),
                             pygame.SRCALPHA)
        bar.fill((0, 0, 0, 70))
        surface.blit(bar, (0, self.toolbar_y - 14))
        m, s = divmod(int(self.elapsed), 60)
        info = f"Temps  {m:02d}:{s:02d}      Coups  {self.moves}      Score  {self.score}"
        txt = self.small.render(info, True, C.TEXT_LIGHT)
        surface.blit(txt, txt.get_rect(center=(C.SCREEN_W // 2, self.toolbar_y + 20)))

    def _draw_toast(self, surface):
        if self.toast_t <= 0:
            return
        alpha = int(255 * min(1.0, self.toast_t / 0.6))
        txt = self.small.render(self.toast_text, True, C.TEXT_LIGHT)
        pad = 16
        box = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + 14),
                             pygame.SRCALPHA)
        box.fill((30, 34, 40, min(200, alpha)))
        r = box.get_rect(center=(C.SCREEN_W // 2, self.play_bottom - 30))
        surface.blit(box, r.topleft)
        txt.set_alpha(alpha)
        surface.blit(txt, txt.get_rect(center=r.center))

    def _draw_setup(self, surface):
        title = self.big.render("Spider Solitaire", True, C.TEXT_LIGHT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 170)))
        sub = self.font.render("Choisissez la difficulté", True, C.TEXT_DIM)
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 240)))
        for b in self.setup_buttons:
            b.draw(surface)

    def _draw_win(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surface.blit(veil, (0, 0))
        title = self.big.render("Bravo !", True, C.ACCENT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 350)))
        m, s = divmod(int(self.elapsed), 60)
        sub = self.font.render(
            f"Termine en {m:02d}:{s:02d} — {self.moves} coups — score {self.score}",
            True, C.TEXT_LIGHT)
        surface.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 415)))
        for b in self.win_buttons:
            b.draw(surface)

    def _draw_confetti(self, surface):
        for p in self.confetti:
            s = pygame.Surface((p.size, p.size), pygame.SRCALPHA)
            s.fill(p.color)
            s = pygame.transform.rotate(s, p.rot)
            surface.blit(s, (p.x, p.y))
