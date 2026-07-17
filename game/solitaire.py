"""Solitaire Klondike : logique de jeu, glisser-deposer et animations."""
import random
import pygame

from . import constants as C
from . import ui
from .cards import Card, CardRenderer
from .scene import Scene


# --------------------------------------------------------------------------
class Pile:
    def __init__(self, kind, x, y):
        self.kind = kind          # stock | waste | foundation | tableau
        self.x = x
        self.y = y
        self.cards = []

    def top(self):
        return self.cards[-1] if self.cards else None


class Move:
    """Animation de deplacement d'une carte vers sa pile de destination."""
    def __init__(self, card, start, dest, dur, delay=0.0,
                 flip_on_arrive=False, on_done=None):
        self.card = card
        self.start = start
        self.dest = dest
        self.dur = dur
        self.delay = delay
        self.t = 0.0
        self.flip = flip_on_arrive
        self.on_done = on_done


class Flip:
    """Petite animation de retournement en place."""
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
class SolitaireScene(Scene):
    FAN_UP = 30
    FAN_DOWN = 14
    GRAB_THRESHOLD = 6

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer()
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.big = pygame.font.SysFont(C.FONT_UI, 64, bold=True)
        self._build_layout()
        self._build_buttons()
        self.new_game()

    # ---- mise en place ----
    def _build_layout(self):
        top = 28
        left = 200
        gap = C.CARD_W + 30
        self.stock = Pile("stock", left, top)
        self.waste = Pile("waste", left + gap, top)
        self.foundations = [Pile("foundation", left + gap * (3 + i), top)
                            for i in range(4)]
        tab_y = top + C.CARD_H + 30
        self.tableau = [Pile("tableau", left + gap * i, tab_y) for i in range(7)]
        self.all_piles = ([self.stock, self.waste] + self.foundations
                          + self.tableau)
        self.stock_slot = pygame.Rect(self.stock.x, self.stock.y,
                                       C.CARD_W, C.CARD_H)
        self.toolbar_y = C.SCREEN_H - 58
        self.play_bottom = self.toolbar_y - 14

    def _build_buttons(self):
        y = self.toolbar_y
        f = self.small
        self.buttons = [
            ui.Button((40, y, 150, 40), "Nouvelle", self.new_game, f),
            ui.Button((200, y, 120, 40), "Annuler", self.undo, f,
                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT),
            ui.Button((330, y, 120, 40), "Terminer", self.start_auto, f,
                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT),
            ui.Button((C.SCREEN_W - 160, y, 120, 40), "Menu",
                      self.app.show_menu, f,
                      fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]
        self.btn_auto = self.buttons[2]
        self.win_buttons = [
            ui.Button((C.SCREEN_W // 2 - 220, 470, 200, 52), "Rejouer",
                      self.new_game, self.font),
            ui.Button((C.SCREEN_W // 2 + 20, 470, 200, 52), "Menu",
                      self.app.show_menu, self.font,
                      fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    # ---- nouvelle partie ----
    def new_game(self):
        deck = [Card(s, r) for s in C.SUITS for r in range(1, 14)]
        random.shuffle(deck)
        for p in self.all_piles:
            p.cards = []
        self.anims = []
        self.flips = []
        self.flying = set()
        self.drag = None
        self._press = None
        self._pre = None
        self.undo_stack = []
        self.moves = 0
        self.elapsed = 0.0
        self.timer_on = False
        self.won = False
        self.auto = False
        self.confetti = []
        self.mouse = (0, 0)
        self._last_click_t = -1
        self._last_click_card = None

        # distribution animee
        self.dealing = True
        self.stock.cards = deck[28:]
        dealt = deck[:28]
        idx = 0
        delay = 0.0
        start = (self.stock.x, self.stock.y)
        # pattern round-robin : la derniere carte de chaque colonne est face visible
        for r in range(7):
            for col in range(r, 7):
                card = dealt[idx]; idx += 1
                face_up = (r == col)
                self.tableau[col].cards.append(card)
                self.flying.add(card)
                self.anims.append(Move(card, start, self.tableau[col],
                                       0.26, delay=delay,
                                       flip_on_arrive=face_up))
                delay += 0.035

    # ------------------------------------------------------------------
    # Geometrie
    # ------------------------------------------------------------------
    def fan_offsets(self, pile):
        up, down = self.FAN_UP, self.FAN_DOWN
        n = len(pile.cards)
        if n <= 1:
            return up, down
        n_down = sum(1 for c in pile.cards[:-1] if not c.face_up)
        n_up = (n - 1) - n_down
        span = n_down * down + n_up * up
        max_span = max(1, self.play_bottom - pile.y - C.CARD_H)
        if span > max_span:
            s = max_span / span
            up *= s; down *= s
        return up, down

    def pile_positions(self, pile):
        if pile.kind == "tableau":
            up, down = self.fan_offsets(pile)
            pos = []
            y = pile.y
            for c in pile.cards:
                pos.append((pile.x, y))
                y += up if c.face_up else down
            return pos
        return [(pile.x, pile.y)] * len(pile.cards)

    def card_target(self, card, pile):
        try:
            i = pile.cards.index(card)
        except ValueError:
            return (pile.x, pile.y)
        return self.pile_positions(pile)[i]

    def drop_rect(self, pile):
        if pile.kind == "tableau":
            pos = self.pile_positions(pile)
            if pos:
                bottom = pos[-1][1] + C.CARD_H
            else:
                bottom = pile.y + C.CARD_H
            return pygame.Rect(pile.x, pile.y, C.CARD_W, bottom - pile.y)
        return pygame.Rect(pile.x, pile.y, C.CARD_W, C.CARD_H)

    # ------------------------------------------------------------------
    # Regles
    # ------------------------------------------------------------------
    def can_foundation(self, f, card):
        if not f.cards:
            return card.rank == 1
        t = f.top()
        return t.suit == card.suit and card.rank == t.rank + 1

    def can_tableau(self, t, card):
        if not t.cards:
            return card.rank == 13
        top = t.top()
        return top.face_up and top.red != card.red and card.rank == top.rank - 1

    def is_valid_run(self, cards):
        for a, b in zip(cards, cards[1:]):
            if not (a.face_up and b.face_up
                    and a.red != b.red and b.rank == a.rank - 1):
                return False
        return cards and cards[0].face_up

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def busy(self):
        return bool(self.anims) or bool(self.flips)

    def handle_event(self, event):
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
                self.draw_stock()
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
        """Renvoie (pile, index) de la carte cliquable la plus haute."""
        for pile in self.tableau + [self.waste] + self.foundations:
            positions = self.pile_positions(pile)
            for i in range(len(pile.cards) - 1, -1, -1):
                c = pile.cards[i]
                if c in self.flying:
                    continue
                rect = pygame.Rect(positions[i], (C.CARD_W, C.CARD_H))
                if rect.collidepoint(pos):
                    return pile, i
        return None

    def on_press(self, pos):
        if self.busy():
            return
        if self.stock_slot.collidepoint(pos):
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
            _, pile, idx, start = self._press
            if abs(pos[0] - start[0]) + abs(pos[1] - start[1]) > self.GRAB_THRESHOLD:
                self.begin_drag(pile, idx, pos)

    def begin_drag(self, pile, idx, pos):
        card = pile.cards[idx]
        if not card.face_up:
            self._press = None
            return
        cards = pile.cards[idx:]
        if pile.kind == "tableau":
            if not self.is_valid_run(cards):
                if idx != len(pile.cards) - 1:
                    self._press = None
                    return
                cards = pile.cards[idx:]
        else:  # waste / foundation : seulement la carte du dessus
            if idx != len(pile.cards) - 1:
                self._press = None
                return
            cards = pile.cards[idx:]
        self._pre = self.snapshot()
        top_pos = self.pile_positions(pile)[idx]
        self.drag = {
            "cards": cards,
            "source": pile,
            "gdx": top_pos[0] - pos[0],
            "gdy": top_pos[1] - pos[1],
            "off": self.FAN_UP,
        }
        del pile.cards[idx:]

    def drag_positions(self):
        d = self.drag
        return [(self.mouse[0] + d["gdx"], self.mouse[1] + d["gdy"] + i * d["off"])
                for i in range(len(d["cards"]))]

    def find_drop(self, drag, pos):
        d = drag
        top_rect = pygame.Rect(self.mouse[0] + d["gdx"],
                               self.mouse[1] + d["gdy"], C.CARD_W, C.CARD_H)
        best, best_area = None, 0
        for pile in self.foundations + self.tableau:
            r = self.drop_rect(pile).clip(top_rect)
            area = r.width * r.height
            if area > best_area:
                best_area = area
                best = pile
        return best if best_area > 0 else None

    def valid_drop(self, pile, cards):
        if pile.kind == "foundation":
            return len(cards) == 1 and self.can_foundation(pile, cards[0])
        if pile.kind == "tableau":
            return self.can_tableau(pile, cards[0])
        return False

    def on_release(self, pos):
        if self.drag:
            self.finish_drag(pos)
        elif self._press:
            if self._press[0] == "stock":
                self.draw_stock()
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
        if target and self.valid_drop(target, cards):
            self.undo_stack.append(self._pre)
            for c in cards:
                target.cards.append(c)
            self.animate_settle(cards, starts, target, then=self._post_move_check)
            self.after_move(drag["source"])
            self.moves += 1
            self.timer_on = True
        else:
            src = drag["source"]
            for c in cards:
                src.cards.append(c)
            self.animate_settle(cards, starts, src)

    def after_move(self, source):
        if source.kind == "tableau" and source.cards:
            top = source.top()
            if not top.face_up:
                pos = self.pile_positions(source)[-1]
                self.flips.append(Flip(top, pos))
                self.moves += 1

    def card_click(self, pile, idx):
        now = pygame.time.get_ticks() / 1000.0
        top = idx == len(pile.cards) - 1
        card = pile.cards[idx]
        double = (now - self._last_click_t < 0.35 and self._last_click_card is card)
        self._last_click_t = now
        self._last_click_card = card
        if double and top and pile.kind in ("tableau", "waste"):
            self.try_to_foundation(pile)

    def try_to_foundation(self, pile):
        if not pile.cards:
            return False
        card = pile.top()
        for f in self.foundations:
            if self.can_foundation(f, card):
                self.undo_stack.append(self.snapshot())
                pile.cards.pop()
                start = self.pile_positions(pile)[len(pile.cards)] \
                    if pile.cards else (pile.x, pile.y)
                start = (pile.x, start[1]) if pile.kind == "tableau" else (pile.x, pile.y)
                f.cards.append(card)
                self.animate_settle([card], [start], f, then=self._post_move_check)
                self.after_move(pile)
                self.moves += 1
                self.timer_on = True
                return True
        return False

    def draw_stock(self):
        if self.busy():
            return
        if self.stock.cards:
            self.undo_stack.append(self.snapshot())
            card = self.stock.cards.pop()
            card.face_up = True
            self.waste.cards.append(card)
            self.animate_settle([card], [(self.stock.x, self.stock.y)],
                                self.waste, dur=0.2)
            self.moves += 1
            self.timer_on = True
        elif self.waste.cards:
            self.undo_stack.append(self.snapshot())
            while self.waste.cards:
                c = self.waste.cards.pop()
                c.face_up = False
                self.stock.cards.append(c)
            self.moves += 1

    # ---- auto-finish ----
    def can_auto(self):
        if self.won or self.dealing:
            return False
        if self.stock.cards:
            return False
        return all(c.face_up for p in self.tableau for c in p.cards)

    def start_auto(self):
        if self.can_auto():
            self.auto = True

    def auto_step(self):
        for pile in [self.waste] + self.tableau:
            if pile.cards and not (pile.top() in self.flying):
                card = pile.top()
                for f in self.foundations:
                    if self.can_foundation(f, card):
                        pile.cards.pop()
                        f.cards.append(card)
                        self.animate_settle([card], [(pile.x, pile.y)], f,
                                            dur=0.16, then=self._post_move_check)
                        self.moves += 1
                        return True
        self.auto = False
        return False

    # ------------------------------------------------------------------
    # Undo / snapshot
    # ------------------------------------------------------------------
    def snapshot(self):
        return [[(c.suit, c.rank, c.face_up) for c in p.cards]
                for p in self.all_piles]

    def restore(self, snap):
        for p, cards in zip(self.all_piles, snap):
            p.cards = [Card(s, r, f) for (s, r, f) in cards]

    def undo(self):
        if self.dealing or not self.undo_stack:
            return
        self.anims = []
        self.flips = []
        self.flying = set()
        self.drag = None
        self.auto = False
        self.restore(self.undo_stack.pop())

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------
    def animate_settle(self, cards, starts, dest, dur=0.14, then=None):
        n = len(cards)
        for i, (card, start) in enumerate(zip(cards, starts)):
            self.flying.add(card)
            done = then if i == n - 1 else None
            self.anims.append(Move(card, start, dest, dur, on_done=done))

    def _post_move_check(self):
        if not self.won and all(len(f.cards) == 13 for f in self.foundations):
            self.win()

    def win(self):
        self.won = True
        self.auto = False
        self.timer_on = False
        for _ in range(160):
            self.confetti.append(
                Confetti(random.randint(0, C.SCREEN_W), random.randint(-200, 0)))

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in (self.win_buttons if self.won else self.buttons):
            b.update(dt, mouse)
        if not self.won:
            self.btn_auto.enabled = self.can_auto() or self.auto

        if self.timer_on and not self.won:
            self.elapsed += dt

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

        # auto-finish
        if self.auto and not self.anims and not self.dealing:
            self.auto_step()

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
        self._draw_slots(surface)
        # piles au repos
        for pile in self.all_piles:
            self._draw_pile(surface, pile)
        # retournements
        for fl in self.flips:
            self._draw_flip(surface, fl)
        # deplacements en vol
        for m in self.anims:
            if m.delay > 0:
                continue
            self._draw_move(surface, m)
        # highlight de depose
        if self.drag:
            self._draw_drop_hint(surface)
            self._draw_drag(surface)

        self._draw_hud(surface)
        for b in self.buttons:
            b.draw(surface)
        if self.won:
            self._draw_win(surface)
        self._draw_confetti(surface)

    def _draw_slots(self, surface):
        for pile in self.all_piles:
            if pile.kind in ("stock", "waste", "foundation", "tableau"):
                surface.blit(self.renderer.slot, (pile.x, pile.y))
        # symbole recyclage sur le stock vide
        if not self.stock.cards:
            c = self.stock_slot.center
            pygame.draw.circle(surface, (255, 255, 255, 60), c, 16, 3)

    def _blit_card(self, surface, card, pos, shadow=True):
        if shadow:
            g = 6
            surface.blit(self.renderer.shadow, (pos[0] - g, pos[1] - g))
        surface.blit(self.renderer.surface(card), pos)

    def _draw_pile(self, surface, pile):
        positions = self.pile_positions(pile)
        drag_cards = self.drag["cards"] if self.drag else ()
        for i, card in enumerate(pile.cards):
            if card in self.flying or card in drag_cards:
                continue
            if any(fl.card is card for fl in self.flips):
                continue
            top = (i == len(pile.cards) - 1)
            self._blit_card(surface, card, positions[i], shadow=top)

    def _draw_move(self, surface, m):
        target = self.card_target(m.card, m.dest)
        t = ui.ease_out_cubic(min(1.0, m.t))
        x = ui.lerp(m.start[0], target[0], t)
        y = ui.lerp(m.start[1], target[1], t)
        self._blit_card(surface, m.card, (x, y))

    def _draw_flip(self, surface, fl):
        t = fl.t
        scale = abs(1 - 2 * t)  # 1 -> 0 -> 1
        surf = self.renderer.surface(fl.card)
        w = max(1, int(C.CARD_W * scale))
        scaled = pygame.transform.smoothscale(surf, (w, C.CARD_H))
        x = fl.pos[0] + (C.CARD_W - w) // 2
        surface.blit(scaled, (x, fl.pos[1]))

    def _draw_drop_hint(self, surface):
        pos = pygame.mouse.get_pos()
        target = self.find_drop(self.drag, pos)
        if target and self.valid_drop(target, self.drag["cards"]):
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

    def _draw_hud(self, surface):
        # bandeau bas
        bar = pygame.Surface((C.SCREEN_W, C.SCREEN_H - self.toolbar_y + 14),
                             pygame.SRCALPHA)
        bar.fill((0, 0, 0, 70))
        surface.blit(bar, (0, self.toolbar_y - 14))
        m, s = divmod(int(self.elapsed), 60)
        info = f"Temps  {m:02d}:{s:02d}      Coups  {self.moves}"
        txt = self.small.render(info, True, C.TEXT_LIGHT)
        surface.blit(txt, txt.get_rect(center=(C.SCREEN_W // 2, self.toolbar_y + 20)))

    def _draw_win(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surface.blit(veil, (0, 0))
        title = self.big.render("Bravo !", True, C.ACCENT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 350)))
        m, s = divmod(int(self.elapsed), 60)
        sub = self.font.render(f"Termine en {m:02d}:{s:02d} et {self.moves} coups",
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
