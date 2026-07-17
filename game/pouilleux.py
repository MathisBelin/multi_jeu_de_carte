"""Le Pouilleux (Old Maid à la française) — mode interactif.

On retire une carte du jeu de 52 pour qu'une seule carte reste sans partenaire :
la carte « orpheline ». Deux cartes forment une paire si elles ont le **même
rang ET la même couleur** (rouge = ♥/♦, noir = ♠/♣) ; chaque rang possède donc
exactement une paire rouge et une paire noire.

- **Version classique** : on retire le Valet de Trèfle → le **Valet de Pique**
  reste orphelin (le « pouilleux » est connu à l'avance).
- **Pouilleux mystère** : on retire une carte au hasard → personne ne sait
  quelle carte est orpheline.

Chaque joueur défausse ses paires, puis, à tour de rôle, pioche une carte (face
cachée) chez son voisin. Le joueur qui reste avec la carte orpheline en fin de
partie est le Pouilleux (le perdant). L'humain (siège 0) clique une carte dans
l'éventail du voisin ; les IA piochent au hasard.
"""
import random

import pygame

from . import constants as C
from . import ui
from .cards import Card, CardRenderer
from .scene import Scene

NAMES = ["Vous", "Alice", "Bruno", "Carla", "David", "Elsa", "Hugo", "Inès"]

PARTNER_SUIT = {C.SPADE: C.CLUB, C.CLUB: C.SPADE,
                C.HEART: C.DIAMOND, C.DIAMOND: C.HEART}
SUIT_FR = {C.SPADE: "Pique", C.HEART: "Cœur", C.DIAMOND: "Carreau",
           C.CLUB: "Trèfle"}
RANK_FR = {1: "As", 11: "Valet", 12: "Dame", 13: "Roi"}

SAFE_COL = (150, 200, 130)
LOSER_COL = (210, 92, 92)


def pair_key(card):
    """Deux cartes s'apparient si même rang et même couleur."""
    return (card.rank, card.red)


def card_label(suit, rank):
    return f"{RANK_FR.get(rank, str(rank))} de {SUIT_FR[suit]}"


class Fly:
    """Carte en vol d'un point à un autre (option retournement / dos)."""
    def __init__(self, card, start, target, dur=0.36, reveal=False,
                 face_down=False):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0
        self.reveal = reveal        # anime un retournement dos → face
        self.face_down = face_down  # reste face cachée


class PouilleuxScene(Scene):
    MAX_STEPS = 5000                # borne de sécurité anti-boucle

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(88, 126)
        self.mini = CardRenderer(40, 58)
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)   # descriptions d'options
        self.big = pygame.font.SysFont(C.FONT_UI, 52, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 44, bold=True)

        self.cx = C.SCREEN_W // 2
        self.DISCARD = (C.SCREEN_W - 176, 384)

        self.N = 4
        self.version = "classic"    # "classic" | "mystery"
        self.mode = "auto"          # "auto" | "manual"
        self.phase = "setup"
        self.victim = None
        self.cur = 0
        self.flies = []
        self._after = None
        self.think_t = 0.0
        self.hands = []
        self.out_order = []
        self.discard_count = 0
        self.orphan_label = ""
        self.loser = None
        self.ranking = []
        self.pod_center = {}
        self.selected = []          # ids de cartes cochées (défausse manuelle)
        self._discarding = False    # anim de défausse manuelle en cours
        # Réordonnancement manuel de sa main (glisser-déposer)
        self._press_card = None     # carte pressée (clic court ou début de glisser)
        self._press_pos = (0, 0)
        self._drag_card = None       # carte en cours de glisser-déposer
        self._drag_pos = (0, 0)
        self._drag_offset = (0, 0)
        self._card_x = {}            # x animé de chaque carte de la main (lissage)
        self._hand_draw = []         # (carte, x, y) rendus de la main humaine
        self._hand_ph = None         # x de l'emplacement cible pendant un glisser

        self._build_buttons()

    # ------------------------------------------------------------------
    # Boutons
    # ------------------------------------------------------------------
    def _build_buttons(self):
        cx = self.cx
        self.btn_menu = ui.Button((C.SCREEN_W - 150, 16, 120, 40), "Menu",
                                  self.app.show_menu, self.small,
                                  fill=(150, 92, 92), text_col=C.TEXT_LIGHT)
        self.btn_minus = ui.Button((cx - 176, 338, 64, 64), "−", self._dec,
                                   self.num_font, fill=(96, 120, 150),
                                   text_col=C.TEXT_LIGHT)
        self.btn_plus = ui.Button((cx + 112, 338, 64, 64), "+", self._inc,
                                  self.num_font, fill=(96, 120, 150),
                                  text_col=C.TEXT_LIGHT)
        self.btn_version = ui.Button((cx - 230, 424, 460, 46), self._version_label(),
                                     self._toggle_version, self.small,
                                     fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_mode = ui.Button((cx - 230, 478, 460, 46), self._mode_label(),
                                  self._toggle_mode, self.small,
                                  fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_start = ui.Button((cx - 130, 566, 260, 54), "Commencer",
                                   self.new_game, self.font)
        self.btn_ready = ui.Button((cx - 130, 512, 260, 54), "Prêt",
                                   self._ready_done, self.font)
        self.btn_donner = ui.Button((cx - 130, 512, 260, 54), "Donner",
                                    self._donner_done, self.font)
        self.btn_give = ui.Button((cx - 130, 512, 260, 54), "Donner",
                                  self._give_consent, self.font)
        self.btn_shuffle = ui.Button((cx - 120, 452, 240, 46), "Mélanger la main",
                                     self._shuffle_hand, self.small,
                                     fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.btn_discard_float = ui.Button((0, 0, 128, 38), "Défausser",
                                           self._manual_discard, self.small)
        self.over_buttons = [
            ui.Button((cx - 230, 596, 210, 52), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 596, 210, 52), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _version_label(self):
        return "Classique" if self.version == "classic" else "Mystère"

    def _mode_label(self):
        return "Automatique" if self.mode == "auto" else "Manuelle"

    # ---- écran de config : compartiment, code couleur, titres ----
    def _style_setup_buttons(self):
        BLUE, PURPLE = (70, 108, 158), (132, 96, 168)
        GREEN, ORANGE = (78, 148, 102), (196, 132, 70)
        self.btn_version.fill = BLUE if self.version == "classic" else PURPLE
        self.btn_version.label = self._version_label()
        self.btn_mode.fill = GREEN if self.mode == "auto" else ORANGE
        self.btn_mode.label = self._mode_label()
        for b in (self.btn_version, self.btn_mode):
            b.fill_hover = tuple(min(255, c + 24) for c in b.fill)
            b.text_col = C.TEXT_LIGHT

    def _opt_row(self, px, pw, y, title, desc, button):
        pad, bw, bh = 22, 210, 44
        button.rect.update(px + pw - pad - bw, y, bw, bh)
        self._texts.append((title, self.small, C.TEXT_LIGHT, (px + pad, y + 11),
                            "left"))
        yy = y + bh + 6
        if desc:
            self._texts.append((desc, self.dfont, C.TEXT_DIM, (px + pad, yy),
                                "left"))
            yy += 22
        return yy + 12

    def _layout_setup(self):
        self._style_setup_buttons()
        self._panels, self._texts, self._dividers = [], [], []
        cx = self.cx
        pw = 660
        px = cx - pw // 2
        top, pad = 196, 22
        y = top + 54
        # nombre de joueurs (stepper)
        self._texts.append(("Nombre de joueurs", self.small, C.TEXT_LIGHT,
                            (px + pad, y + 14), "left"))
        self._texts.append(("Vous + IA (2 à 8)", self.dfont, C.TEXT_DIM,
                            (px + pad, y + 40), "left"))
        grp = 56 + 80 + 56
        gx = px + pw - pad - grp
        self.btn_minus.rect.update(gx, y, 56, 56)
        self.btn_plus.rect.update(gx + 56 + 80, y, 56, 56)
        self._num_pos = (gx + 56 + 40, y + 28)
        y += 70
        self._dividers.append((px + pad, px + pw - pad, y)); y += 14
        vd = ("Le Valet de Pique est le pouilleux (connu d'avance)"
              if self.version == "classic"
              else "La carte orpheline reste inconnue de tous")
        y = self._opt_row(px, pw, y, "Version", vd, self.btn_version)
        self._dividers.append((px + pad, px + pw - pad, y)); y += 14
        md = ("Les paires sont écartées automatiquement" if self.mode == "auto"
              else "Vous écartez vous-même vos paires (les IA restent auto)")
        y = self._opt_row(px, pw, y, "Défausse des paires", md, self.btn_mode)
        bottom = y + 12
        self._panels.append((pygame.Rect(px, top, pw, bottom - top),
                             "RÉGLAGES DE LA PARTIE", C.ACCENT))
        self.btn_start.rect.update(cx - 130, bottom + 30, 260, 56)

    def _dec(self):
        self.N = max(2, self.N - 1)

    def _inc(self):
        self.N = min(8, self.N + 1)

    def _toggle_version(self):
        self.version = "mystery" if self.version == "classic" else "classic"
        self.btn_version.label = self._version_label()

    def _toggle_mode(self):
        self.mode = "manual" if self.mode == "auto" else "auto"
        self.btn_mode.label = self._mode_label()

    def _cur_buttons(self):
        if self.phase == "setup":
            self._layout_setup()
            return [self.btn_minus, self.btn_plus, self.btn_version,
                    self.btn_mode, self.btn_start, self.btn_menu]
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        if self.phase == "ready":
            btns = [self.btn_shuffle, self.btn_ready, self.btn_menu]
            self._place_discard_float(btns)
            return btns
        if self.phase == "discard":
            btns = [self.btn_donner, self.btn_menu]
            self._place_discard_float(btns)
            return btns
        if self.phase == "give":
            return [self.btn_shuffle, self.btn_give, self.btn_menu]
        if self.phase == "wait" and self._reorder_allowed():
            return [self.btn_shuffle, self.btn_menu]
        return [self.btn_menu]

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def new_game(self):
        deck = [Card(s, r) for s in C.SUITS for r in range(1, 14)]
        if self.version == "classic":
            removed = next(c for c in deck if c.suit == C.CLUB and c.rank == 11)
        else:
            removed = random.choice(deck)
        deck.remove(removed)
        o_suit, o_rank = PARTNER_SUIT[removed.suit], removed.rank
        self.orphan_label = card_label(o_suit, o_rank)

        random.shuffle(deck)
        self.hands = [[] for _ in range(self.N)]
        for i, c in enumerate(deck):
            self.hands[i % self.N].append(c)
        for i, h in enumerate(self.hands):
            # En manuel, l'humain (siège 0) écarte lui-même ses paires initiales.
            if not (self.mode == "manual" and i == 0):
                self._discard_initial(h)
            h.sort(key=self._sort_key)

        self.out_order = [i for i in range(self.N) if not self.hands[i]]
        self.discard_count = (52 - 1 - sum(len(h) for h in self.hands)) // 2
        self.flies = []
        self._after = None
        self._discarding = False
        self.selected = []
        self._press_card = None
        self._drag_card = None
        self._card_x = {}
        self._hand_draw = []
        self._hand_ph = None
        self.loser = None
        self.ranking = []
        self._layout_seats()

        if self.mode == "manual":
            # Tout le monde écarte ses paires, puis on clique « Prêt ».
            self.victim = None
            self.cur = 0
            self.phase = "ready"
            return

        active = [i for i in range(self.N) if self.hands[i]]
        self.cur = random.choice(active) if active else 0
        self._begin_turn()

    def _ready_done(self):
        """Fin de la mise en place manuelle : on lance la première pioche."""
        if self.phase != "ready" or self._paired_ids():
            return
        self.selected = []
        active = [i for i in range(self.N) if self.hands[i]]
        self.cur = random.choice(active) if active else 0
        self._begin_turn()

    def _donner_done(self):
        """L'humain a défaussé ses doubles : il présente sa main au suivant."""
        if self.phase != "discard" or self._paired_ids():
            return
        self.selected = []
        self._post_turn()

    def _give_consent(self):
        """L'humain (victime) donne son accord : le voisin pioche chez lui."""
        if self.phase != "give":
            return
        self._press_card = None
        self._drag_card = None
        v = self.victim
        if not self.hands[v]:
            self._post_turn()
            return
        self._do_draw(random.randrange(len(self.hands[v])))

    def _shuffle_hand(self):
        """Mélange aléatoirement la main de l'humain."""
        if self.hands and self.hands[0]:
            random.shuffle(self.hands[0])

    # ------------------------------------------------------------------
    # Défausse manuelle (mode manuel)
    # ------------------------------------------------------------------
    def _paired_ids(self):
        """Ids des cartes de la main humaine qui forment une paire."""
        groups = {}
        for c in self.hands[0]:
            groups.setdefault(pair_key(c), []).append(c)
        ids = set()
        for cs in groups.values():
            if len(cs) >= 2:
                ids.update(id(c) for c in cs)
        return ids

    def _toggle_select(self, card):
        if id(card) in self.selected:
            self.selected.remove(id(card))
        else:
            self.selected.append(id(card))

    def _manual_discard(self):
        """Défausse les paires valides parmi les cartes sélectionnées."""
        if self._discarding:
            return
        sel = [c for c in self.hands[0] if id(c) in self.selected]
        groups = {}
        for c in sel:
            groups.setdefault(pair_key(c), []).append(c)
        to_go = []
        for cs in groups.values():
            n = len(cs) - len(cs) % 2
            to_go.extend(cs[:n])
        if not to_go:
            return
        gone = {id(c) for c in to_go}
        self.selected = [i for i in self.selected if i not in gone]
        slots = {id(c): r for c, r in self._hand_slots()}
        dp = self.DISCARD
        flies = []
        ret_phase = self.phase
        for j, c in enumerate(to_go):
            r = slots.get(id(c))
            start = r.topleft if r else dp
            off = j % 2
            flies.append(Fly(c, start, (dp[0] + off * 16, dp[1] - off * 6),
                             dur=0.3))
            self.hands[0].remove(c)
        self.discard_count += len(to_go) // 2
        self._discarding = True

        def after():
            self._discarding = False
            self.phase = ret_phase
        self._launch(flies, after)

    def _selected_pair_ready(self):
        """Vrai si les cartes cochées contiennent au moins une paire valide."""
        sel = [c for c in self.hands[0] if id(c) in self.selected]
        groups = {}
        for c in sel:
            groups.setdefault(pair_key(c), []).append(c)
        return any(len(cs) >= 2 for cs in groups.values())

    def _place_discard_float(self, btns):
        """Petit bouton flottant « Défausser » centré au-dessus des cartes
        cochées (dès qu'une paire valide est sélectionnée, en défausse manuelle)."""
        if (self.mode != "manual" or self._discarding or not self.hands
                or not self._selected_pair_ready()):
            return
        cw, ch = self.renderer.w, self.renderer.h
        rects = [pygame.Rect(int(x), int(y), cw, ch)
                 for c, x, y in self._hand_draw if id(c) in self.selected]
        if not rects:
            return
        box = rects[0].unionall(rects)
        bw, bh = 128, 38
        bx = max(8, min(box.centerx - bw // 2, C.SCREEN_W - bw - 8))
        self.btn_discard_float.rect = pygame.Rect(bx, box.top - 8 - bh, bw, bh)
        btns.append(self.btn_discard_float)

    def _discard_initial(self, hand):
        seen = {}
        keep = []
        for c in hand:
            k = pair_key(c)
            if k in seen:
                keep.remove(seen[k])
                del seen[k]
            else:
                seen[k] = c
                keep.append(c)
        hand[:] = keep

    def _sort_key(self, card):
        return (card.rank, C.SUITS.index(card.suit))

    def _layout_seats(self):
        cx = self.cx
        self.pod_center = {0: (cx, C.SCREEN_H - 150)}
        opp = list(range(1, self.N))
        m = len(opp)
        y = 150
        for j, seat in enumerate(opp):
            x = cx if m == 1 else int(ui.lerp(240, C.SCREEN_W - 240, j / (m - 1)))
            self.pod_center[seat] = (x, y)

    # ------------------------------------------------------------------
    # Déroulement
    # ------------------------------------------------------------------
    def _name(self, i):
        return NAMES[i] if i < len(NAMES) else f"Joueur {i}"

    def _next_active(self, i):
        for s in range(1, self.N):
            j = (i + s) % self.N
            if self.hands[j]:
                return j
        return i

    def _victim(self, i):
        for s in range(1, self.N):
            j = (i - s) % self.N
            if self.hands[j]:
                return j
        return i

    def _begin_turn(self):
        active = [i for i in range(self.N) if self.hands[i]]
        if len(active) <= 1:
            self._finish(active[0] if active else None)
            return
        if not self.hands[self.cur]:
            self.cur = self._next_active(self.cur)
        self.victim = self._victim(self.cur)
        # Les IA mélangent aussi leur main autant qu'elles le veulent : juste
        # avant qu'on pioche chez elle, une IA-victime rebat ses cartes pour
        # rester imprévisible (l'équivalent du « Donner »/« Mélanger » humain).
        if self.victim != 0 and self.hands[self.victim]:
            random.shuffle(self.hands[self.victim])
        self.think_t = 0.7
        self._press_card = None
        self._drag_card = None
        # Quand un voisin va piocher chez l'humain, on attend son accord
        # (bouton « Donner ») pour lui laisser le temps de mélanger sa main.
        if self.cur != 0 and self.victim == 0:
            self.phase = "give"
        else:
            self.phase = "wait"

    def _launch(self, flies, after):
        self.flies = flies
        self._after = after
        self.phase = "anim"

    def _do_draw(self, k):
        v, cur = self.victim, self.cur
        if not self.hands[v] or k >= len(self.hands[v]):
            return
        # position de départ de la carte piochée
        if cur == 0:
            slots = self._zone_slots(len(self.hands[v]))
            start = slots[k].topleft
        elif v == 0:
            start = self._hand_slots()[k][1].topleft
        else:
            pc = self.pod_center[v]
            start = (pc[0] - self.renderer.w // 2, pc[1] - self.renderer.h // 2)
        card = self.hands[v].pop(k)
        tp = self.pod_center[cur]
        target = (tp[0] - self.renderer.w // 2, tp[1] - self.renderer.h // 2)
        reveal = (cur == 0)
        face_up = (v == 0 and cur != 0)
        face_down = not (reveal or face_up)
        self._launch([Fly(card, start, target, reveal=reveal,
                          face_down=face_down)],
                     lambda: self._after_draw(card))

    def _after_draw(self, card):
        cur = self.cur
        self.hands[cur].append(card)
        if self.mode == "manual" and cur == 0:
            # L'humain défausse lui-même son éventuel double, puis « Donner ».
            # (Pas de tri : il choisit lui-même l'ordre de sa main.)
            self.selected = []
            self.phase = "discard"
            return
        k = pair_key(card)
        partner = next((c for c in self.hands[cur]
                        if c is not card and pair_key(c) == k), None)
        if partner is not None:
            self.hands[cur].remove(card)
            self.hands[cur].remove(partner)
            self.discard_count += 1
            pc = self.pod_center[cur]
            start = (pc[0] - self.renderer.w // 2, pc[1] - self.renderer.h // 2)
            dp = self.DISCARD
            flies = [Fly(card, start, dp, dur=0.3),
                     Fly(partner, (start[0] + 16, start[1] - 6),
                         (dp[0] + 16, dp[1] - 6), dur=0.3)]
            self._launch(flies, self._post_turn)
        else:
            if cur != 0:                       # l'IA rebat sa main (imprévisible)
                random.shuffle(self.hands[cur])
            self._post_turn()

    def _post_turn(self):
        for i in (self.victim, self.cur):
            if not self.hands[i] and i not in self.out_order:
                self.out_order.append(i)
        active = [i for i in range(self.N) if self.hands[i]]
        if len(active) <= 1:
            self._finish(active[0] if active else None)
            return
        self.cur = self._next_active(self.cur)
        self._begin_turn()

    def _finish(self, loser):
        self.loser = loser
        self.ranking = list(self.out_order)
        if loser is not None and loser not in self.ranking:
            self.ranking.append(loser)
        self.phase = "over"

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
            if self.phase == "wait" and self.cur == 0 and self.victim is not None:
                slots = self._zone_slots(len(self.hands[self.victim]))
                for i in range(len(slots) - 1, -1, -1):
                    if slots[i].collidepoint(event.pos):
                        self._do_draw(i)
                        return
            if self.phase in ("ready", "discard") and not self._discarding:
                cw, ch = self.renderer.w, self.renderer.h
                dr = pygame.Rect(self.DISCARD[0], self.DISCARD[1], cw, ch)
                if dr.collidepoint(event.pos):
                    self._manual_discard()
                    return
            # Prise d'une carte de sa main : clic court = (dé)sélection,
            # glisser = réordonnancement (selon la phase).
            if (self.phase in ("ready", "discard", "give", "wait", "anim")
                    and not self._discarding and self.hands):
                for c, r in reversed(self._hand_slots()):
                    if r.collidepoint(event.pos):
                        self._press_card = c
                        self._press_pos = event.pos
                        self._drag_card = None
                        self._drag_offset = (event.pos[0] - r.x,
                                             event.pos[1] - r.y)
                        return
            return

        if event.type == pygame.MOUSEMOTION and self._press_card is not None:
            dx = event.pos[0] - self._press_pos[0]
            dy = event.pos[1] - self._press_pos[1]
            if (self._drag_card is None and self._reorder_allowed()
                    and dx * dx + dy * dy > 64):
                self._drag_card = self._press_card
            if self._drag_card is not None:
                self._drag_pos = event.pos
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag_card is not None:
                self._drop_drag(event.pos)
            elif (self._press_card is not None
                  and self.phase in ("ready", "discard")
                  and not self._discarding):
                self._toggle_select(self._press_card)
            self._press_card = None
            self._drag_card = None
            return

    def _reorder_allowed(self):
        """On ne peut réordonner sa main que hors de son propre tour."""
        return (self.phase in ("ready", "give")
                or (self.phase == "wait" and self.cur != 0))

    def _drop_drag(self, pos):
        card = self._drag_card
        hand = self.hands[0]
        if card not in hand:
            return
        self._drag_pos = pos
        hand.remove(card)
        hand.insert(self._insert_index(hand), card)

    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._cur_buttons():
            b.update(dt, mouse)
        if self.phase == "setup":
            pass   # labels/couleurs/positions gérés par _layout_setup
        if self.phase == "ready":
            self.btn_ready.enabled = not self._paired_ids()
        if self.phase == "discard":
            self.btn_donner.enabled = not self._paired_ids()

        self._animate_hand(dt)

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

        if self.phase == "wait" and self.cur != 0 and self.victim is not None:
            # On laisse l'humain réordonner sa main : tant qu'il manipule une
            # carte, l'IA patiente (elle ne pioche pas).
            if self._press_card is not None or self._drag_card is not None:
                return
            self.think_t -= dt
            if self.think_t <= 0:
                self._do_draw(random.randrange(len(self.hands[self.victim])))

    # ------------------------------------------------------------------
    # Géométrie
    # ------------------------------------------------------------------
    def _zone_slots(self, n):
        cw, ch = self.renderer.w, self.renderer.h
        if n == 0:
            return []
        spacing = 0 if n == 1 else min(int(cw * 0.92), (760 - cw) // (n - 1))
        total = spacing * (n - 1) + cw
        x0 = self.cx - total // 2
        y = 322
        return [pygame.Rect(x0 + i * spacing, y, cw, ch) for i in range(n)]

    def _fan_x(self, n):
        """x de départ et espacement pour disposer n cartes dans la main."""
        cw = self.renderer.w
        if n <= 0:
            return C.SCREEN_W // 2, 0
        spacing = 0 if n == 1 else min(int(cw * 0.72), (1000 - cw) // (n - 1))
        total = spacing * (n - 1) + cw
        return (C.SCREEN_W - total) // 2, spacing

    def _hand_slots(self):
        if not self.hands or not self.hands[0]:
            return []
        hand = self.hands[0]
        cw, ch = self.renderer.w, self.renderer.h
        x0, spacing = self._fan_x(len(hand))
        y = C.SCREEN_H - ch - 52
        return [(hand[i], pygame.Rect(x0 + i * spacing, y, cw, ch))
                for i in range(len(hand))]

    def _insert_index(self, rest):
        """Index d'insertion (0..len(rest)) d'après le centre de la carte
        glissée, sur la disposition compacte des cartes restantes."""
        cw = self.renderer.w
        x0, spacing = self._fan_x(len(rest))
        cxp = self._drag_pos[0] - self._drag_offset[0] + cw // 2
        for i in range(len(rest)):
            if cxp < x0 + i * spacing + cw // 2:
                return i
        return len(rest)

    def _hand_layout(self):
        """(carte, x, y) des cartes visibles de la main + x de l'emplacement
        réservé à la carte glissée (ou None hors glisser-déposer). Pendant un
        glisser, un « trou » de la largeur d'une carte s'ouvre à l'endroit
        d'insertion : les cartes voisines s'écartent pour le révéler."""
        if not self.hands or not self.hands[0]:
            return [], None
        hand = self.hands[0]
        cw, ch = self.renderer.w, self.renderer.h
        y = C.SCREEN_H - ch - 52
        if self._drag_card is None or self._drag_card not in hand:
            x0, spacing = self._fan_x(len(hand))
            return ([(hand[i], x0 + i * spacing, y) for i in range(len(hand))],
                    None)
        rest = [c for c in hand if c is not self._drag_card]
        ins = self._insert_index(rest)
        seq = rest[:ins] + [None] + rest[ins:]   # None = emplacement réservé
        x0, spacing = self._fan_x(len(seq))
        out, ph = [], None
        for i, c in enumerate(seq):
            x = x0 + i * spacing
            if c is None:
                ph = x
            else:
                out.append((c, x, y))
        return out, ph

    def _animate_hand(self, dt):
        """Lisse le glissement des cartes de la main vers leur position cible
        (écartement progressif autour de l'emplacement d'insertion)."""
        layout, self._hand_ph = self._hand_layout()
        k = min(1.0, dt * 16)
        live = set()
        self._hand_draw = []
        for c, x, y in layout:
            live.add(id(c))
            cur = self._card_x.get(id(c), x)
            cur += (x - cur) * k
            self._card_x[id(c)] = cur
            self._hand_draw.append((c, cur, y))
        for key in list(self._card_x):
            if key not in live:
                del self._card_x[key]

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
        self._draw_opponents(surface)
        self._draw_center(surface)
        self._draw_human(surface)
        self._draw_discard(surface)
        for f in self.flies:
            self._draw_fly(surface, f)
        for b in self._cur_buttons():
            b.draw(surface)
        if self.phase == "over":
            self._draw_over(surface)

    def _draw_setup(self, surface):
        cx = self.cx
        t = self.big.render("Le Pouilleux", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 100)))
        s = self.small.render("Réglez la partie, puis lancez", True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 146)))
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
            if align == "center":
                surface.blit(surf, surf.get_rect(center=pos))
            else:
                surface.blit(surf, pos)
        num = self.num_font.render(str(self.N), True, C.TEXT_LIGHT)
        surface.blit(num, num.get_rect(center=self._num_pos))

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        surface.blit(self.title_font.render("Le Pouilleux", True, C.TEXT_LIGHT),
                     (24, 10))
        if self.phase == "ready":
            txt = ("Écartez vos paires (surlignées) : cliquez les 2 cartes puis "
                   "la pile de défausse, puis « Prêt »")
            s = self.small.render(txt, True, C.ACCENT)
            surface.blit(s, s.get_rect(center=(self.cx, 23)))
        elif self.phase == "discard":
            txt = ("Défaussez votre double (cliquez les 2 cartes puis la pile), "
                   "puis « Donner »")
            s = self.small.render(txt, True, C.ACCENT)
            surface.blit(s, s.get_rect(center=(self.cx, 23)))
        elif self.phase == "give":
            txt = (f"{self._name(self.cur)} va piocher chez vous — mélangez "
                   f"ou réordonnez, puis cliquez « Donner »")
            s = self.small.render(txt, True, C.ACCENT)
            surface.blit(s, s.get_rect(center=(self.cx, 23)))
        elif self.phase in ("wait", "anim") and self.victim is not None:
            if self.cur == 0:
                txt = f"À vous : piochez une carte chez {self._name(self.victim)}"
            else:
                txt = f"{self._name(self.cur)} pioche chez {self._name(self.victim)}…"
            s = self.small.render(txt, True, C.ACCENT)
            surface.blit(s, s.get_rect(center=(self.cx, 23)))

    def _draw_opponents(self, surface):
        for seat in range(1, self.N):
            cxp, cyp = self.pod_center[seat]
            n = len(self.hands[seat])
            if n > 0:
                show = min(n, 6)
                fw = self.mini.w
                sp = 16
                total = fw + (show - 1) * sp
                x0 = cxp - total // 2
                for i in range(show):
                    surface.blit(self.mini.back,
                                 (x0 + i * sp, cyp - self.mini.h // 2))
            # plaque nom + état
            r = pygame.Rect(0, 0, 150, 46)
            r.center = (cxp, cyp + 58)
            drawer = (seat == self.cur)
            vict = (seat == self.victim)
            bg = (70, 96, 120) if drawer else (46, 62, 78)
            pygame.draw.rect(surface, bg, r, border_radius=10)
            edge = (C.ACCENT if drawer else (232, 196, 110) if vict
                    else (90, 100, 110))
            pygame.draw.rect(surface, edge, r,
                             width=2 if (drawer or vict) else 1, border_radius=10)
            surface.blit(self.small.render(self._name(seat), True, C.TEXT_LIGHT),
                         (r.x + 12, r.y + 4))
            if n == 0:
                info, col = "Sauvé", SAFE_COL
            else:
                info, col = f"{n} carte(s)", C.TEXT_DIM
            surface.blit(self.tiny.render(info, True, col), (r.x + 12, r.y + 26))

    def _draw_center(self, surface):
        v = self.victim
        if v is None:
            return
        flying = {id(f.card) for f in self.flies}
        if (self.cur == 0 and self.phase in ("wait", "anim")
                and not self._discarding and self.hands[v]):
            slots = self._zone_slots(len(self.hands[v]))
            for c, r in zip(self.hands[v], slots):
                if id(c) in flying:
                    continue
                surface.blit(self.renderer.back, r.topleft)
            if self.phase == "wait":
                p = self.small.render(
                    f"Cliquez une carte de {self._name(v)}", True, C.TEXT_LIGHT)
                surface.blit(p, p.get_rect(center=(self.cx, 300)))

    def _draw_human(self, surface):
        cw, ch = self.renderer.w, self.renderer.h
        flying = {id(f.card) for f in self.flies}
        rects = [(c, pygame.Rect(int(x), int(y), cw, ch))
                 for c, x, y in self._hand_draw]
        if self.phase in ("give", "wait", "anim") and self.victim == 0 and rects:
            hl = rects[0][1].unionall([r for _, r in rects]).inflate(24, 24)
            box = pygame.Surface(hl.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (232, 196, 110, 40), box.get_rect(),
                             border_radius=14)
            pygame.draw.rect(box, (232, 196, 110, 150), box.get_rect(),
                             width=2, border_radius=14)
            surface.blit(box, hl.topleft)
        # emplacement cible du glisser-déposer (là où la carte va s'insérer)
        if self._hand_ph is not None:
            phr = pygame.Rect(int(self._hand_ph), C.SCREEN_H - ch - 52, cw, ch)
            slot = pygame.Surface(phr.size, pygame.SRCALPHA)
            pygame.draw.rect(slot, (232, 196, 110, 60), slot.get_rect(),
                             border_radius=12)
            pygame.draw.rect(slot, C.ACCENT, slot.get_rect(),
                             width=3, border_radius=12)
            surface.blit(slot, phr.topleft)
        paired = (self._paired_ids() if self.phase in ("ready", "discard")
                  else set())
        for c, r in rects:
            if id(c) in flying:
                continue
            surface.blit(self.renderer.face(c), r.topleft)
            if id(c) in self.selected:
                pygame.draw.rect(surface, C.ACCENT, r.inflate(8, 8),
                                 width=4, border_radius=12)
            elif id(c) in paired:
                pygame.draw.rect(surface, C.HILITE, r.inflate(6, 6),
                                 width=3, border_radius=12)
        # indice de réordonnancement (hors de son tour)
        if (self._reorder_allowed() and self.hands[0] and rects
                and self._drag_card is None):
            hint = self.tiny.render(
                "Glissez vos cartes pour changer leur ordre", True, C.TEXT_DIM)
            surface.blit(hint, hint.get_rect(
                center=(self.cx, rects[0][1].y - 32)))
        # carte en cours de glisser-déposer (au-dessus du reste)
        if self._drag_card is not None:
            dx, dy = self._drag_offset
            pos = (self._drag_pos[0] - dx, self._drag_pos[1] - dy)
            surface.blit(self.renderer.face(self._drag_card), pos)
            dr = pygame.Rect(pos[0], pos[1], self.renderer.w, self.renderer.h)
            pygame.draw.rect(surface, C.ACCENT, dr.inflate(8, 8),
                             width=3, border_radius=12)
        # plaque humain
        r = pygame.Rect(0, 0, 210, 40)
        r.center = (150, C.SCREEN_H - 34)
        drawer = (self.cur == 0 and self.phase in ("wait", "anim"))
        bg = (70, 96, 120) if drawer else (46, 62, 78)
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, C.ACCENT if drawer else (90, 100, 110), r,
                         width=2 if drawer else 1, border_radius=10)
        if not self.hands[0] and self.phase != "setup":
            label, col = "Vous · Sauvé", SAFE_COL
        else:
            label, col = "Vous", C.TEXT_LIGHT
        surface.blit(self.tiny.render(label, True, col),
                     (r.x + 12, r.centery - 8))

    def _draw_discard(self, surface):
        x, y = self.DISCARD
        cw, ch = self.renderer.w, self.renderer.h
        surface.blit(self.renderer.slot, (x, y))
        if self.phase in ("ready", "discard") and not self._discarding:
            pygame.draw.rect(surface, C.ACCENT,
                             pygame.Rect(x, y, cw, ch).inflate(8, 8),
                             width=3, border_radius=12)
            hint = self.tiny.render("Défausse", True, C.ACCENT)
            surface.blit(hint, hint.get_rect(center=(x + cw // 2, y - 14)))
        lab = self.tiny.render(f"Paires écartées : {self.discard_count}",
                               True, C.TEXT_DIM)
        surface.blit(lab, lab.get_rect(center=(x + cw // 2, y + ch + 16)))

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

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 185))
        surface.blit(veil, (0, 0))
        cx = self.cx
        if self.loser is None:
            txt, col = "Personne n'est pouilleux !", C.ACCENT
        elif self.loser == 0:
            txt, col = "Vous êtes le Pouilleux !", LOSER_COL
        else:
            txt, col = f"{self._name(self.loser)} est le Pouilleux !", C.ACCENT
        t = self.big.render(txt, True, col)
        surface.blit(t, t.get_rect(center=(cx, 150)))
        rev = self.small.render(f"Carte orpheline : {self.orphan_label}",
                                True, C.TEXT_DIM)
        surface.blit(rev, rev.get_rect(center=(cx, 214)))

        y = 280
        for place, seat in enumerate(self.ranking):
            last = (seat == self.loser)
            name = self._name(seat)
            if last:
                line, col = f"Pouilleux · {name}", LOSER_COL
            else:
                line, col = f"{place + 1}.  {name} · sauvé", SAFE_COL
            s = self.font.render(line, True, col)
            surface.blit(s, s.get_rect(center=(cx, y)))
            y += 42
        for b in self.over_buttons:
            b.draw(surface)
