"""Le Barbu — jeu de levées à contrats multiples, 3 à 10 joueurs.

Mode **interactif** (humain = siège 0, IA autonomes) sur le patron circulaire du
Bouclié / Pouilleux. Une partie se joue en **6 manches**, chacune avec sa règle
de pénalité (le but est d'avoir le **moins de points** à la fin) :

1. **Sans règle**   — seul le nombre de plis compte (+5 pts par pli).
2. **Les cœurs**    — chaque cœur ramassé coûte 10 pts.
3. **Les dames**    — chaque dame ramassée coûte 20 pts.
4. **Le Roi de pique** — ramasser le K♠ coûte 80 pts.
5. **Le dernier pli**  — ramasser le dernier pli coûte 100 pts.
6. **Tout à la fois**  — cœurs + dames + K♠ + dernier pli, cumulés.

Par **défaut**, à chaque manche les plis rapportent aussi +5 pts (option pour
choisir dans quelles manches ce +5 est compté). Toutes les valeurs de pénalité
sont réglables dans un **écran « Avancé »**.

Mécanique d'un pli (commune à tout) : on **fournit le signe demandé** (♠♥♦♣) si
on l'a, sinon on se défausse librement ; **pas d'atout** — le plus fort du signe
demandé (2 < … < 10 < V < D < R < As) remporte le pli et entame le suivant.

Distribution **égale** : on retire les cartes basses inutiles pour que 52 tombe
juste sur N joueurs, en gardant **toujours** les cartes importantes de la manche
en cours (tous les cœurs au tour des cœurs, les dames au tour des dames, le K♠
au tour du Roi de pique, et cœurs + dames + K♠ au tour « Tout »).
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

GOLD = (232, 196, 110)
RED = (224, 96, 96)
GREEN = (140, 210, 130)
BLUE = (120, 176, 224)

# (clé, nom complet, nom court)
MANCHES = [
    ("plis",      "Sans règle",      "Sans règle"),
    ("coeurs",    "Les cœurs",       "Cœurs"),
    ("dames",     "Les dames",       "Dames"),
    ("roi_pique", "Le Roi de pique", "Roi ♠"),
    ("dernier",   "Le dernier pli",  "Dernier"),
    ("tout",      "Tout à la fois",  "Tout"),
]

PEN_ORDER = ["trick", "heart", "queen", "king", "last"]
PEN_LABEL = {"trick": "Chaque pli", "heart": "Chaque cœur", "queen": "Chaque dame",
             "king": "Roi de pique (K♠)", "last": "Dernier pli"}
PEN_STEP = {"trick": 1, "heart": 5, "queen": 5, "king": 10, "last": 10}
PEN_DEFAULT = {"trick": 5, "heart": 10, "queen": 20, "king": 80, "last": 100}


def rank_val(card):
    """Force au jeu : l'As (rang 1) est la plus forte."""
    return 14 if card.rank == 1 else card.rank


class Fly:
    """Carte en vol d'un point à un autre (toujours face visible ici)."""
    def __init__(self, card, start, target, dur=0.34):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0


class FloatText:
    """Texte flottant (points gagnés sur un pli)."""
    def __init__(self, text, pos, color, dur=1.4):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.t = 0.0
        self.dur = dur


class BarbuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.hand_rend = CardRenderer(80, 114)    # main de l'humain (cliquable)
        self.play_rend = CardRenderer(58, 82)     # cartes du pli + en vol
        self.mini = CardRenderer(30, 43)          # dos des mains adverses
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)
        self.big = pygame.font.SysFont(C.FONT_UI, 50, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 40, bold=True)
        self.field_font = pygame.font.SysFont(C.FONT_UI, 30, bold=True)

        self.cx = C.SCREEN_W // 2
        self.TRICK_C = (self.cx, 366)
        self.EC = (self.cx, 366)
        self.RX, self.RY = 548, 286
        self.TRICK_R = 104

        # réglages
        self.N = 4
        self.penalties = dict(PEN_DEFAULT)
        self.trick_counts = [True] * 6           # +5/pli compté par manche
        # saisie clavier d'une valeur de pénalité (écran avancé)
        self.edit_key = None
        self.edit_buf = ""
        self.caret_t = 0.0
        self.pen_field = {}

        # état
        self.phase = "setup"
        self.players_names = []
        self.hands = []
        self.totals = []
        self.manche_pts = []
        self.manche_deck = []
        self.manche_played = []
        self.manche_idx = 0
        self.contract = "plis"
        self.per = 0
        self.first_seat = 0
        self.leader = 0
        self.cur = 0
        self.trick = []
        self.trick_seats = []
        self.tricks_played = 0
        self.last_winner = None
        self.win_flash = None
        self.direction = 1
        self.think_t = 0.0
        self.hold_t = 0.0
        self.flies = []
        self._after = None
        self.floats = []
        self.pod = {}

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
        self.btn_advanced = ui.Button((0, 0, 260, 46), "Réglages avancés",
                                      self._open_advanced, self.small,
                                      fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.btn_start = ui.Button((0, 0, 260, 54), "Commencer",
                                   self.new_game, self.font)
        self.btn_back = ui.Button((0, 0, 220, 50), "Retour",
                                  self._close_advanced, self.small,
                                  fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.btn_manche_go = ui.Button((cx - 150, 486, 300, 56),
                                       "Commencer la manche", self._begin_play,
                                       self.font)
        self.btn_next_manche = ui.Button((cx - 150, 728, 300, 52), "Suivant",
                                         self._next_manche, self.font)
        # steppers de l'écran avancé
        self.pen_minus, self.pen_plus = {}, {}
        for k in PEN_ORDER:
            self.pen_minus[k] = ui.Button((0, 0, 42, 40), "−",
                                          (lambda kk=k: self._pen_adjust(kk, -1)),
                                          self.font, fill=(96, 120, 150),
                                          text_col=C.TEXT_LIGHT)
            self.pen_plus[k] = ui.Button((0, 0, 42, 40), "+",
                                         (lambda kk=k: self._pen_adjust(kk, 1)),
                                         self.font, fill=(96, 120, 150),
                                         text_col=C.TEXT_LIGHT)
        self.count_btns = [ui.Button((0, 0, 200, 40), "",
                                     (lambda ii=i: self._toggle_count(ii)),
                                     self.small, text_col=C.TEXT_LIGHT)
                           for i in range(6)]
        self.over_buttons = [
            ui.Button((cx - 230, 736, 210, 50), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 736, 210, 50), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _dec(self):
        self.N = max(3, self.N - 1)

    def _inc(self):
        self.N = min(10, self.N + 1)

    def _open_advanced(self):
        self.edit_key = None
        self.edit_buf = ""
        self.phase = "advanced"

    def _close_advanced(self):
        self._commit_edit()
        self.phase = "setup"

    def _pen_adjust(self, key, sign):
        self._commit_edit()
        self.penalties[key] = max(0, self.penalties[key] + sign * PEN_STEP[key])

    def _toggle_count(self, i):
        self._commit_edit()
        self.trick_counts[i] = not self.trick_counts[i]

    def _start_edit(self, key):
        self._commit_edit()
        self.edit_key = key
        self.edit_buf = ""            # vide : on retape le nombre voulu
        self.caret_t = 0.0

    def _commit_edit(self):
        """Valide la saisie clavier en cours (si le champ est vide, on garde
        la valeur précédente)."""
        if self.edit_key is None:
            return
        if self.edit_buf != "":
            self.penalties[self.edit_key] = min(9999, int(self.edit_buf))
        self.edit_key = None
        self.edit_buf = ""

    def _cur_buttons(self):
        if self.phase == "setup":
            self._layout_setup()
            return [self.btn_minus, self.btn_plus, self.btn_advanced,
                    self.btn_start, self.btn_menu]
        if self.phase == "advanced":
            self._layout_advanced()
            btns = [self.btn_back]
            for k in PEN_ORDER:
                btns += [self.pen_minus[k], self.pen_plus[k]]
            btns += list(self.count_btns)
            return btns
        if self.phase == "manche_intro":
            return [self.btn_manche_go, self.btn_menu]
        if self.phase == "manche_end":
            return [self.btn_next_manche, self.btn_menu]
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        return [self.btn_menu]

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def _name(self, i):
        return NAMES[i] if i < len(NAMES) else f"Joueur {i}"

    def new_game(self):
        self.totals = [0] * self.N
        self.manche_idx = 0
        # Siège qui entame la 1re manche : TIRÉ AU SORT (puis la rotation avance
        # d'un siège par manche) — sinon la manche 1 commencerait toujours par
        # l'humain (siège 0).
        self.first_seat = random.randrange(self.N)
        self.floats = []
        self._layout_seats()
        self._start_manche()

    def _is_important(self, card, contract):
        if contract in ("coeurs", "tout") and card.suit == C.HEART:
            return True
        if contract in ("dames", "tout") and card.rank == 12:
            return True
        if (contract in ("roi_pique", "tout")
                and card.suit == C.SPADE and card.rank == 13):
            return True
        return False

    def _deal(self):
        """Construit le paquet de la manche (distribution égale) et distribue."""
        full = [Card(s, r, face_up=True) for s in C.SUITS for r in range(1, 14)]
        self.per = 52 // self.N
        need = self.per * self.N
        to_remove = 52 - need
        if to_remove:
            removable = [c for c in full
                         if not self._is_important(c, self.contract)]
            removable.sort(key=lambda c: (rank_val(c), C.SUITS.index(c.suit)))
            gone = {id(c) for c in removable[:to_remove]}
            deck = [c for c in full if id(c) not in gone]
        else:
            deck = full
        random.shuffle(deck)
        self.manche_deck = list(deck)            # composition exacte (pour l'IA)
        self.hands = [[] for _ in range(self.N)]
        for i, c in enumerate(deck):
            self.hands[i % self.N].append(c)
        for h in self.hands:
            h.sort(key=self._sort_key)

    def _sort_key(self, card):
        return (C.SUITS.index(card.suit), rank_val(card))

    def _start_manche(self):
        self.contract = MANCHES[self.manche_idx][0]
        self._deal()
        self.manche_pts = [0] * self.N
        self.manche_played = []                  # cartes déjà jouées (mémoire IA)
        self.leader = (self.first_seat + self.manche_idx) % self.N
        self.cur = self.leader
        self.trick = []
        self.trick_seats = []
        self.tricks_played = 0
        self.last_winner = None
        self.win_flash = None
        self.flies = []
        self._after = None
        self.floats = []
        self.phase = "manche_intro"

    def _begin_play(self):
        if self.phase != "manche_intro":
            return
        self.phase = "playing"
        self._next_to_play()

    def _next_manche(self):
        if self.manche_idx >= len(MANCHES) - 1:
            self.phase = "over"
        else:
            self.manche_idx += 1
            self._start_manche()

    # ------------------------------------------------------------------
    # Déroulement d'un pli
    # ------------------------------------------------------------------
    def _legal_cards(self, seat):
        hand = self.hands[seat]
        if not self.trick:
            return list(hand)
        led = self.trick[0].suit
        same = [c for c in hand if c.suit == led]
        return same if same else list(hand)

    def _next_to_play(self):
        if self.hands[self.cur] == []:
            return
        if self.cur == 0:
            self.phase = "playing"
        else:
            self.phase = "ai_think"
            self.think_t = 0.6

    def _play_card(self, seat, card):
        start = self._card_start(seat, card)
        self.hands[seat].remove(card)
        self.trick.append(card)
        self.trick_seats.append(seat)
        target = self._trick_slot(seat)
        self.flies = [Fly(card, start, target)]
        self._after = self._after_play
        self.phase = "anim"

    def _after_play(self):
        if len(self.trick) >= self.N:
            self._resolve_trick()
        else:
            self.cur = (self.cur + self.direction) % self.N
            self._next_to_play()

    def _resolve_trick(self):
        led = self.trick[0].suit
        best = 0
        for i, c in enumerate(self.trick):
            if c.suit == led and rank_val(c) > rank_val(self.trick[best]):
                best = i
        winner = self.trick_seats[best]
        is_last = (self.tricks_played == self.per - 1)
        pts = self._trick_points(self.trick, is_last)
        self.manche_pts[winner] += pts
        if pts:
            self._float(winner, f"+{pts}", RED)
        self.manche_played.extend(self.trick)
        self.last_winner = winner
        self.win_flash = winner
        self.leader = winner
        self.cur = winner
        self.tricks_played += 1
        self.phase = "trick_end"
        self.hold_t = 0.9

    def _trick_points(self, cards, is_last):
        c, P = self.contract, self.penalties
        pts = 0
        if self.trick_counts[self.manche_idx]:
            pts += P["trick"]
        if c in ("coeurs", "tout"):
            pts += P["heart"] * sum(1 for x in cards if x.suit == C.HEART)
        if c in ("dames", "tout"):
            pts += P["queen"] * sum(1 for x in cards if x.rank == 12)
        if c in ("roi_pique", "tout"):
            pts += P["king"] * sum(1 for x in cards
                                   if x.suit == C.SPADE and x.rank == 13)
        if c in ("dernier", "tout") and is_last:
            pts += P["last"]
        return pts

    def _collect_trick(self):
        """Les cartes du pli volent vers le vainqueur, puis on enchaîne."""
        if not self.trick:
            self._finish_collect()
            return
        winner = self.last_winner
        wx, wy = self.pod[winner]
        tgt = (wx - self.play_rend.w // 2, wy - self.play_rend.h // 2)
        n = len(self.trick)
        flies = []
        for i, (c, seat) in enumerate(zip(self.trick, self.trick_seats)):
            off = int((i - (n - 1) / 2) * 5)
            flies.append(Fly(c, self._trick_slot(seat),
                             (tgt[0] + off, tgt[1]), dur=0.42))
        self.flies = flies
        self._after = self._finish_collect
        self.phase = "anim"

    def _finish_collect(self):
        self.trick = []
        self.trick_seats = []
        self.win_flash = None
        if self.tricks_played >= self.per:
            self._end_manche()
        else:
            self._next_to_play()

    def _end_manche(self):
        for i in range(self.N):
            self.totals[i] += self.manche_pts[i]
        self.phase = "manche_end"

    # ------------------------------------------------------------------
    # IA (heuristique : cherche à ne pas ramasser les cartes à pénalité)
    # ------------------------------------------------------------------
    def _danger(self, card):
        """Coût de garder / ramasser cette carte pour le contrat courant."""
        c, P = self.contract, self.penalties
        d = 0.0
        if c in ("coeurs", "tout") and card.suit == C.HEART:
            d += P["heart"]
        if c in ("dames", "tout") and card.rank == 12:
            d += P["queen"]
        if c in ("roi_pique", "tout") and card.suit == C.SPADE and card.rank == 13:
            d += P["king"]
        d += rank_val(card) * 0.1        # à défaut, on se débarrasse des hautes
        return d

    def _penalty_of(self, card):
        """Points que CETTE carte ferait encaisser au preneur du pli (contrat
        courant) — sert à ne pas ajouter soi-même de pénalité à un pli qu'on prend."""
        c, P = self.contract, self.penalties
        v = 0
        if c in ("coeurs", "tout") and card.suit == C.HEART:
            v += P["heart"]
        if c in ("dames", "tout") and card.rank == 12:
            v += P["queen"]
        if c in ("roi_pique", "tout") and card.suit == C.SPADE and card.rank == 13:
            v += P["king"]
        return v

    def _outstanding_higher(self, seat, card):
        """Nombre de cartes du même signe, PLUS FORTES, encore en jeu chez les
        autres (déduit de la composition connue de la manche et des cartes vues)."""
        s, hi = card.suit, rank_val(card)
        seen = {(c.suit, c.rank) for c in self.hands[seat]}
        seen |= {(c.suit, c.rank) for c in self.manche_played}
        seen |= {(c.suit, c.rank) for c in self.trick}
        return sum(1 for c in self.manche_deck
                   if c.suit == s and rank_val(c) > hi
                   and (c.suit, c.rank) not in seen)

    def _ai_lead(self, seat, tricks_left):
        hand = self.hands[seat]
        if self.contract == "dernier" and tricks_left > 1:
            # dernier pli : jeter une carte haute tôt, garder des basses pour la fin
            return max(hand, key=rank_val)
        # mener une carte qu'on NE remportera PAS (des plus fortes restent en jeu),
        # la plus basse possible ; à rang égal, sortir plutôt une carte à pénalité
        # (une basse menée passe presque toujours → on la « saigne »). Si toutes nos
        # cartes sont maîtresses, on mène la moins dangereuse.
        losable = [c for c in hand if self._outstanding_higher(seat, c) > 0]
        pool = losable if losable else hand
        return min(pool, key=lambda c: (rank_val(c), -self._penalty_of(c)))

    def _ai_play(self, seat):
        """IA heuristique. Principes : ne jamais prendre un pli si on peut
        l'éviter ; quand on esquive, en profiter pour **lâcher sa carte la plus
        dangereuse** ; quand la prise est **inévitable** (dernier à jouer), ne pas
        y ajouter de pénalité et se débarrasser d'une haute carte sûre."""
        hand = self.hands[seat]
        legal = self._legal_cards(seat)
        tricks_left = self.per - self.tricks_played
        last_to_play = (len(self.trick) == self.N - 1)
        if not self.trick:                       # on entame
            return self._ai_lead(seat, tricks_left)
        led = self.trick[0].suit
        following = any(c.suit == led for c in hand)
        if following:                            # legal = cartes du signe demandé
            best_rank = max(rank_val(c) for c in self.trick if c.suit == led)
            duckers = [c for c in legal if rank_val(c) < best_rank]
            if duckers:
                # passer sous la maîtresse ET lâcher la carte la plus dangereuse
                # (ex. glisser un cœur / une dame / le K♠ sous une carte plus forte)
                return max(duckers, key=self._danger)
            if last_to_play:
                # je vais prendre le pli à coup sûr : éviter d'y ajouter une
                # pénalité, et sinon lâcher ma plus haute carte sûre.
                safe = [c for c in legal if self._penalty_of(c) == 0]
                if safe:
                    return max(safe, key=rank_val)
                return min(legal, key=self._penalty_of)
            # d'autres jouent après moi : jouer bas (pour être surpassé) et sans
            # pénalité de préférence.
            return min(legal, key=lambda c: (self._penalty_of(c), rank_val(c)))
        # on est défaussé : on ne peut pas prendre → jeter la carte la plus dangereuse
        return max(legal, key=self._danger)

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------
    def _layout_seats(self):
        self.pod = {0: (self.cx, C.SCREEN_H - 150)}
        opp = list(range(1, self.N))
        m = len(opp)
        for j, seat in enumerate(opp):
            ang = 90.0 if m == 1 else 202.0 - 224.0 * (j / (m - 1))
            rad = math.radians(ang)
            x = self.EC[0] + self.RX * math.cos(rad)
            y = self.EC[1] - self.RY * math.sin(rad)
            self.pod[seat] = (int(x), int(y))

    def _trick_slot(self, seat):
        tc = self.TRICK_C
        px, py = self.pod[seat]
        dx, dy = px - tc[0], py - tc[1]
        L = math.hypot(dx, dy) or 1.0
        x = tc[0] + dx / L * self.TRICK_R
        y = tc[1] + dy / L * self.TRICK_R
        return (int(x - self.play_rend.w / 2), int(y - self.play_rend.h / 2))

    def _card_start(self, seat, card):
        if seat == 0:
            for c, r in self._hand_slots():
                if c is card:
                    return r.topleft
            return (self.cx, C.SCREEN_H - 150)
        px, py = self.pod[seat]
        return (px - self.play_rend.w // 2, py - self.play_rend.h // 2)

    def _pod_anchor(self, seat):
        return self.pod[seat]

    def _fan_x(self, n):
        cw = self.hand_rend.w
        if n <= 0:
            return C.SCREEN_W // 2, 0
        spacing = 0 if n == 1 else min(int(cw * 0.72), (1060 - cw) // (n - 1))
        total = spacing * (n - 1) + cw
        return (C.SCREEN_W - total) // 2, spacing

    def _hand_slots(self):
        if not self.hands or not self.hands[0]:
            return []
        hand = self.hands[0]
        cw, ch = self.hand_rend.w, self.hand_rend.h
        x0, spacing = self._fan_x(len(hand))
        y = C.SCREEN_H - ch - 34
        return [(hand[i], pygame.Rect(x0 + i * spacing, y, cw, ch))
                for i in range(len(hand))]

    def _float(self, seat, text, color):
        self.floats.append(FloatText(text, self._pod_anchor(seat), color))

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------
    def handle_event(self, event):
        # Écran avancé : saisie clavier d'une valeur de pénalité
        if self.phase == "advanced" and self.edit_key is not None \
                and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._commit_edit()
            elif event.key == pygame.K_ESCAPE:
                self.edit_key = None            # annule la saisie (sans quitter)
                self.edit_buf = ""
            elif event.key == pygame.K_BACKSPACE:
                self.edit_buf = self.edit_buf[:-1]
            elif event.unicode.isdigit() and len(self.edit_buf) < 4:
                self.edit_buf += event.unicode
            return
        for b in self._cur_buttons():
            if b.handle(event):
                return
        if self.phase == "advanced":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for k in PEN_ORDER:
                    if self.pen_field[k].collidepoint(event.pos):
                        self._start_edit(k)
                        return
                self._commit_edit()            # clic ailleurs : on valide
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.phase == "trick_end":
                    self._collect_trick()
                elif self.phase == "manche_intro":
                    self._begin_play()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.phase == "trick_end":
                self._collect_trick()
                return
            if self.phase == "playing" and self.cur == 0:
                legal = self._legal_cards(0)
                for c, r in reversed(self._hand_slots()):
                    if r.collidepoint(event.pos) and c in legal:
                        self._play_card(0, c)
                        return
            return

    # ------------------------------------------------------------------
    # Boucle
    # ------------------------------------------------------------------
    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._cur_buttons():
            b.update(dt, mouse)
        if self.phase == "advanced" and self.edit_key is not None:
            self.caret_t += dt
        if self.phase in ("setup", "advanced"):
            return
        for f in self.floats:
            f.t += dt
        self.floats = [f for f in self.floats if f.t < f.dur]
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
        if self.phase == "ai_think":
            self.think_t -= dt
            if self.think_t <= 0:
                self._play_card(self.cur, self._ai_play(self.cur))
        elif self.phase == "trick_end":
            self.hold_t -= dt
            if self.hold_t <= 0:
                self._collect_trick()

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
        if self.phase == "advanced":
            self._draw_advanced(surface)
            for b in self._cur_buttons():
                b.draw(surface)
            return
        self._draw_hud(surface)
        self._draw_opponents(surface)
        self._draw_trick(surface)
        self._draw_human(surface)
        for f in self.flies:
            img = self.play_rend.face(f.card)
            t = ui.ease_out_cubic(min(1, f.t))
            x = ui.lerp(f.start[0], f.target[0], t)
            y = ui.lerp(f.start[1], f.target[1], t)
            surface.blit(img, (int(x), int(y)))
        self._draw_floats(surface)
        if self.phase == "manche_intro":
            self._draw_intro(surface)
        elif self.phase == "manche_end":
            self._draw_manche_end(surface)
        elif self.phase == "over":
            self._draw_over(surface)
        for b in self._cur_buttons():
            b.draw(surface)

    # ---- écran de config ----
    def _layout_setup(self):
        cx = self.cx
        pw = 620
        px = cx - pw // 2
        top = 250
        grp = 56 + 74 + 56
        gx = px + pw - 24 - grp
        y = top + 54
        self.btn_minus.rect.update(gx, y, 56, 56)
        self.btn_plus.rect.update(gx + 56 + 74, y, 56, 56)
        self._num_pos = (gx + 56 + 37, y + 28)
        self.btn_advanced.rect.update(px + 24, top + 140, 300, 46)
        self.btn_start.rect.update(cx - 130, top + 208, 260, 54)

    def _draw_setup(self, surface):
        self._layout_setup()
        cx = self.cx
        t = self.big.render("Le Barbu", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 120)))
        s = self.small.render("6 manches à contrats — ayez le moins de points",
                              True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 172)))
        pw, ph = 620, 250
        px, py = cx - pw // 2, 250
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 20, 26, 120), panel.get_rect(),
                         border_radius=16)
        pygame.draw.rect(panel, (255, 255, 255, 26), panel.get_rect(),
                         width=1, border_radius=16)
        surface.blit(panel, (px, py))
        hs = self.tiny.render("RÉGLAGES DE LA PARTIE", True, C.ACCENT)
        surface.blit(hs, (px + 22, py + 16))
        pygame.draw.line(surface, C.ACCENT, (px + 22, py + 38),
                         (px + 22 + hs.get_width(), py + 38), 2)
        surface.blit(self.small.render("Nombre de joueurs", True, C.TEXT_LIGHT),
                     (px + 24, py + 68))
        surface.blit(self.dfont.render("Vous + IA (3 à 10) · distribution égale",
                                       True, C.TEXT_DIM), (px + 24, py + 94))
        num = self.num_font.render(str(self.N), True, C.TEXT_LIGHT)
        surface.blit(num, num.get_rect(center=self._num_pos))

    # ---- écran avancé ----
    def _layout_advanced(self):
        cx = self.cx
        pw = 680
        px = cx - pw // 2
        # panneau 1 : valeurs — groupe [−][ champ saisissable ][+] aligné à droite
        top1 = 118
        self._adv_rows = []
        y = top1 + 50
        bwid, fwid, gap = 40, 118, 8
        grp = bwid + gap + fwid + gap + bwid
        gx = px + pw - 24 - grp
        for k in PEN_ORDER:
            self.pen_minus[k].rect.update(gx, y, bwid, 42)
            self.pen_field[k] = pygame.Rect(gx + bwid + gap, y, fwid, 42)
            self.pen_plus[k].rect.update(gx + bwid + gap + fwid + gap, y, bwid, 42)
            self._adv_rows.append((k, y))
            y += 52
        self._adv_p1 = pygame.Rect(px, top1, pw, y - top1 + 8)
        # panneau 2 : plis comptés par manche
        top2 = self._adv_p1.bottom + 34
        yy = top2 + 48
        bw, bh, gap = 210, 40, 14
        for i in range(6):
            col = i % 3
            row = i // 3
            bx = px + 24 + col * (bw + gap)
            by = yy + row * (bh + 12)
            self.count_btns[i].rect.update(bx, by, bw, bh)
        self._adv_p2 = pygame.Rect(px, top2, pw, (yy + 2 * (bh + 12)) - top2 + 6)
        self.btn_back.rect.update(cx - 110, self._adv_p2.bottom + 22, 220, 50)
        # styles des toggles
        for i, b in enumerate(self.count_btns):
            on = self.trick_counts[i]
            b.label = f"{MANCHES[i][2]} : {'+5' if on else 'non'}"
            b.fill = (78, 148, 102) if on else (120, 96, 96)
            b.fill_hover = tuple(min(255, c + 24) for c in b.fill)

    def _draw_advanced(self, surface):
        cx = self.cx
        t = self.big.render("Réglages avancés", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 66)))
        self._layout_advanced()
        for rect, title in ((self._adv_p1, "VALEURS DE PÉNALITÉ (POINTS)"),
                            (self._adv_p2, "PLIS COMPTÉS (+5 / PLI) PAR MANCHE")):
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 20, 26, 120), panel.get_rect(),
                             border_radius=16)
            pygame.draw.rect(panel, (255, 255, 255, 26), panel.get_rect(),
                             width=1, border_radius=16)
            surface.blit(panel, rect.topleft)
            hs = self.tiny.render(title, True, C.ACCENT)
            surface.blit(hs, (rect.x + 22, rect.y + 14))
            pygame.draw.line(surface, C.ACCENT, (rect.x + 22, rect.y + 36),
                             (rect.x + 22 + hs.get_width(), rect.y + 36), 2)
        px = self._adv_p1.x
        for k, y in self._adv_rows:
            surface.blit(self.small.render(PEN_LABEL[k], True, C.TEXT_LIGHT),
                         (px + 24, y + 11))
            self._draw_field(surface, k)
        hint = self.dfont.render(
            "Astuce : cliquez un nombre pour le saisir au clavier "
            "(Entrée pour valider)", True, C.TEXT_DIM)
        surface.blit(hint, hint.get_rect(center=(cx, self._adv_p1.bottom + 12)))

    def _draw_field(self, surface, key):
        """Champ de saisie stylé : boîte arrondie, bord accentué + halo au focus,
        valeur (ou saisie en cours) centrée, caret clignotant."""
        r = self.pen_field[key]
        focus = (self.edit_key == key)
        # halo doux au focus
        if focus:
            glow = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*C.ACCENT, 60), glow.get_rect(),
                             border_radius=14)
            surface.blit(glow, (r.x - 8, r.y - 8))
        pygame.draw.rect(surface, (14, 22, 30), r, border_radius=10)
        # liseré interne sombre (léger effet enfoncé)
        pygame.draw.rect(surface, (6, 10, 14), r.inflate(-4, -4), width=1,
                         border_radius=8)
        edge = C.ACCENT if focus else (96, 112, 128)
        pygame.draw.rect(surface, edge, r, width=2 if focus else 1,
                         border_radius=10)
        txt = self.edit_buf if focus else str(self.penalties[key])
        surf = self.field_font.render(txt, True,
                                      C.ACCENT if focus else C.TEXT_LIGHT)
        trect = surf.get_rect(center=r.center)
        surface.blit(surf, trect)
        if focus and (self.caret_t % 1.0) < 0.5:
            cx0 = trect.right + 3 if txt else r.centerx
            pygame.draw.line(surface, C.ACCENT, (cx0, r.y + 9),
                             (cx0, r.bottom - 9), 2)

    # ---- table ----
    def _rule_text(self, idx):
        key, P = MANCHES[idx][0], self.penalties
        parts = []
        if key == "coeurs":
            parts.append(f"chaque cœur : −{P['heart']}")
        elif key == "dames":
            parts.append(f"chaque dame : −{P['queen']}")
        elif key == "roi_pique":
            parts.append(f"Roi de pique : −{P['king']}")
        elif key == "dernier":
            parts.append(f"dernier pli : −{P['last']}")
        elif key == "tout":
            parts.append(f"cœur −{P['heart']}, dame −{P['queen']}, "
                         f"K♠ −{P['king']}, dernier −{P['last']}")
        if self.trick_counts[idx]:
            parts.append(f"chaque pli : −{P['trick']}")
        return " · ".join(parts) if parts else "aucune pénalité"

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        name = MANCHES[self.manche_idx][1]
        title = f"Le Barbu — Manche {self.manche_idx + 1}/6 : {name}"
        surface.blit(self.title_font.render(title, True, C.TEXT_LIGHT), (24, 10))
        if self.phase == "playing" and self.cur == 0:
            msg, col = "À vous — cliquez une carte à jouer", C.ACCENT
        elif self.phase == "ai_think":
            msg, col = f"{self._name(self.cur)} réfléchit…", C.TEXT_DIM
        elif self.phase == "trick_end" and self.last_winner is not None:
            msg = f"{self._name(self.last_winner)} remporte le pli"
            col = C.TEXT_LIGHT
        else:
            msg, col = self._rule_text(self.manche_idx), C.TEXT_DIM
        s = self.small.render(msg, True, col)
        surface.blit(s, s.get_rect(midright=(C.SCREEN_W - 160, 24)))

    def _live_score(self, seat):
        """Score courant = total acquis + points de la manche en cours."""
        mp = self.manche_pts[seat] if self.manche_pts else 0
        return self.totals[seat] + mp

    def _draw_opponents(self, surface):
        for seat in range(1, self.N):
            cxp, cyp = self.pod[seat]
            n = len(self.hands[seat])
            if n > 0:
                show = min(n, 6)
                fw, sp = self.mini.w, 14
                total = fw + (show - 1) * sp
                x0 = cxp - total // 2
                for i in range(show):
                    surface.blit(self.mini.back,
                                 (x0 + i * sp, cyp - self.mini.h // 2 - 26))
            r = pygame.Rect(0, 0, 164, 44)
            r.center = (cxp, cyp + 30)
            drawer = (seat == self.cur and self.phase in
                      ("playing", "ai_think", "anim"))
            win = (seat == self.win_flash and self.phase == "trick_end")
            bg = (70, 96, 120) if drawer else (46, 62, 78)
            pygame.draw.rect(surface, bg, r, border_radius=10)
            edge = C.ACCENT if drawer else GOLD if win else (90, 100, 110)
            pygame.draw.rect(surface, edge, r,
                             width=2 if (drawer or win) else 1, border_radius=10)
            surface.blit(self.small.render(self._name(seat), True, C.TEXT_LIGHT),
                         (r.x + 12, r.y + 4))
            info = f"{n} c · {self._live_score(seat)} pts"
            surface.blit(self.tiny.render(info, True, C.TEXT_DIM),
                         (r.x + 12, r.y + 25))

    def _draw_trick(self, surface):
        flying = {id(f.card) for f in self.flies}
        for c, seat in zip(self.trick, self.trick_seats):
            if id(c) in flying:
                continue
            pos = self._trick_slot(seat)
            surface.blit(self.play_rend.face(c), pos)
            if self.phase == "trick_end" and seat == self.win_flash:
                r = pygame.Rect(pos[0], pos[1], self.play_rend.w, self.play_rend.h)
                pygame.draw.rect(surface, GOLD, r.inflate(6, 6), width=3,
                                 border_radius=8)

    def _draw_human(self, surface):
        p_name = "Vous"
        cw, ch = self.hand_rend.w, self.hand_rend.h
        legal = (self._legal_cards(0)
                 if self.phase == "playing" and self.cur == 0 else None)
        flying = {id(f.card) for f in self.flies}
        for c, r in self._hand_slots():
            if id(c) in flying:
                continue
            img = self.hand_rend.face(c)
            if legal is not None and c not in legal:
                img = img.copy()
                img.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img, r.topleft)
            if legal is not None and c in legal:
                pygame.draw.rect(surface, C.HILITE, r.inflate(4, 4), width=2,
                                 border_radius=10)
        # plaque humain
        r = pygame.Rect(0, 0, 200, 40)
        r.center = (150, C.SCREEN_H - 22)
        drawer = (self.cur == 0 and self.phase in ("playing", "anim"))
        win = (self.win_flash == 0 and self.phase == "trick_end")
        bg = (70, 96, 120) if drawer else (46, 62, 78)
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, C.ACCENT if drawer else GOLD if win
                         else (90, 100, 110), r,
                         width=2 if (drawer or win) else 1, border_radius=10)
        surface.blit(self.tiny.render(f"{p_name} · {self._live_score(0)} pts",
                                      True, C.TEXT_LIGHT), (r.x + 12, r.centery - 8))

    def _draw_floats(self, surface):
        for f in self.floats:
            k = f.t / f.dur
            y = f.y - int(42 * ui.ease_out_cubic(min(1, k)))
            alpha = 255 if k < 0.7 else int(255 * (1 - (k - 0.7) / 0.3))
            surf = self.font.render(f.text, True, f.color)
            surf.set_alpha(max(0, alpha))
            surface.blit(surf, surf.get_rect(center=(f.x, y)))

    def _draw_intro(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surface.blit(veil, (0, 0))
        cx = self.cx
        pw, ph = 620, 260
        px, py = cx - pw // 2, 210
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (16, 26, 34, 235), panel.get_rect(),
                         border_radius=18)
        pygame.draw.rect(panel, (*C.ACCENT, 180), panel.get_rect(), width=2,
                         border_radius=18)
        surface.blit(panel, (px, py))
        m = MANCHES[self.manche_idx]
        h = self.tiny.render(f"MANCHE {self.manche_idx + 1} / 6", True, C.TEXT_DIM)
        surface.blit(h, h.get_rect(center=(cx, py + 40)))
        t = self.font.render(m[1], True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, py + 84)))
        rule = self.small.render(self._rule_text(self.manche_idx), True,
                                 C.TEXT_LIGHT)
        surface.blit(rule, rule.get_rect(center=(cx, py + 132)))
        lead = self.small.render(f"{self._name(self.leader)} entame",
                                 True, C.TEXT_DIM)
        surface.blit(lead, lead.get_rect(center=(cx, py + 176)))

    def _draw_manche_end(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 190))
        surface.blit(veil, (0, 0))
        cx = self.cx
        last = (self.manche_idx == len(MANCHES) - 1)
        head = (f"Manche {self.manche_idx + 1} — {MANCHES[self.manche_idx][1]} : "
                "terminée")
        t = self.font.render(head, True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 120)))
        cols = self.small.render("Manche          Total", True, C.TEXT_DIM)
        surface.blit(cols, cols.get_rect(midright=(cx + 240, 176)))
        order = sorted(range(self.N), key=lambda i: self.totals[i])
        y = 214
        for rank, i in enumerate(order):
            nm = ("Vous" if i == 0 else self._name(i))
            col = GOLD if i == 0 else C.TEXT_LIGHT
            line = self.font.render(f"{rank + 1}.  {nm}", True, col)
            surface.blit(line, (cx - 250, y))
            mp = self.small.render(f"+{self.manche_pts[i]}", True, RED)
            surface.blit(mp, mp.get_rect(midright=(cx + 120, y + 12)))
            tp = self.font.render(str(self.totals[i]), True, C.TEXT_LIGHT)
            surface.blit(tp, tp.get_rect(midright=(cx + 240, y + 10)))
            y += 40
        self.btn_next_manche.label = "Résultats finaux" if last else "Manche suivante"

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 205))
        surface.blit(veil, (0, 0))
        cx = self.cx
        order = sorted(range(self.N), key=lambda i: self.totals[i])
        winner = order[0]
        if winner == 0:
            txt, col = "Victoire ! Vous avez le moins de points", GOLD
        else:
            txt, col = f"{self._name(winner)} gagne (moins de points)", C.ACCENT
        t = self.big.render(txt, True, col)
        surface.blit(t, t.get_rect(center=(cx, 110)))
        y = 200
        for rank, i in enumerate(order):
            nm = ("Vous" if i == 0 else self._name(i))
            if rank == 0:
                c = GOLD
            elif i == 0:
                c = C.TEXT_LIGHT
            else:
                c = C.TEXT_DIM
            line = self.font.render(f"{rank + 1}.  {nm}", True, c)
            surface.blit(line, (cx - 200, y))
            tp = self.font.render(f"{self.totals[i]} pts", True, c)
            surface.blit(tp, tp.get_rect(midright=(cx + 200, y + 10)))
            y += 44
        for b in self.over_buttons:
            b.draw(surface)
