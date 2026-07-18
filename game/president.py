"""Le Président — scène pygame (affichage, animations, saisie).

Toute la **logique de règles** vit dans `PresidentGame` (`president_game.py`).
Cette scène ne fait que : l'écran de configuration, l'animation des cartes, la
pause entre plis, le rythme des IA, l'écran d'échange, et le rendu. Elle lit
l'état via le moteur `self.g` et lui délègue les actions.
"""
import math
import random
import threading

import pygame

from . import constants as C
from . import ui
from . import ai
from . import ai_mc
from .cards import CardRenderer
from .president_game import PresidentGame
from .scene import Scene

COMBO_NAME = {1: "un", 2: "une paire de", 3: "un brelan de", 4: "un carré de"}
NEUTRAL_COL = (150, 160, 170)


class Move:
    def __init__(self, card, start, target, dur=0.3):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0


class PresidentScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(96, 136)
        self.cw, self.ch = 96, 136
        self.mini_back = pygame.transform.smoothscale(self.renderer.back, (50, 70))
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)   # descriptions d'options
        self.big = pygame.font.SysFont(C.FONT_UI, 56, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 44, bold=True)
        # configuration
        self.N = 4
        self.equitable = True
        self.small_roles = "ends"      # <4 joueurs : "ends" (Prés/Trou) ou "vices"
        self.ai_level = "normal"       # "normal" (heuristique) ou "mc" (Monte-Carlo)
        self.a_la_volee = False        # option « à la volée » (fermeture hors-tour)
        self.snap_reactivity = "slow"  # réaction des bots : "none" / "slow" (3 s) / "instant"
        self.self_steal = False        # sous-option « voler son propre jeu » (2 cartes d'un coup)
        # etat moteur + UI
        self.g = None
        self.moves = []
        self._anim_cb = None
        self.center_display = []
        self.selected = set()
        self.pending = None
        self.think_t = 0.0
        self.pause_t = 0.0
        self.next_leader = None
        self.forced_now = False
        self.give_to = None
        self.give_count = 0
        self.exchange_mode = None       # "give_back" (gagnant) / "give_best" (perdant)
        self.toast = ""
        self.toast_t = 0.0
        self._mc_thread = None         # calcul Monte-Carlo en fond
        self._mc_result = None
        self._mc_token = None          # jeton anti-résultat périmé (préemption snap)
        self.snap_idx = None           # « à la volée » : unique snappeur possible
        self.snap_cards = None         # combo à poser pour fermer
        self.snap_t = 0.0              # délai de réaction (snappeur IA)
        self.snap_hold = False         # fenêtre humaine sans limite (réactivité "none")
        self._snap_key = None          # identité de l'occasion courante (préserve le délai)
        self._snap_declined = None     # occasion refusée via « Ne pas voler »
        self.roles_open = True          # bandeau « CLASSEMENT » déroulé / replié
        self.roles_anim = 1.0           # ouverture animée (0 replié → 1 déroulé)
        self._roles_header = None       # zone cliquable de l'en-tête (toggle)
        self.phase = "setup"
        self._build_buttons()

    # ------------------------------------------------------------------
    # Accès en lecture à l'état du moteur (le moteur = source de vérité)
    # ------------------------------------------------------------------
    @property
    def players(self):
        return self.g.players

    @property
    def turn(self):
        return self.g.turn

    @property
    def revolution(self):
        return self.g.revolution

    @property
    def top_combo(self):
        return self.g.top_combo

    @property
    def required(self):
        return self.g.required

    @property
    def run_len(self):
        return self.g.run_len

    @property
    def couched(self):
        return self.g.couched

    @property
    def places(self):
        return self.g.places

    @property
    def ranking(self):
        return self.g.ranking

    @property
    def round_no(self):
        return self.g.round_no

    def power(self, card):
        return self.g.power(card)

    def prank(self, rank):
        return self.g.prank(rank)

    def closer_rank(self):
        return self.g.closer_rank()

    def finished(self, idx):
        return self.g.finished(idx)

    def title_for(self, place):
        return self.g.title_for(place)

    _TITLE_COLS = {"Président": (212, 175, 55),
                   "Vice-Président": (150, 190, 120),
                   "Vice-Trou": (190, 150, 120),
                   "Trou du cul": (200, 90, 90)}

    def title_col(self, place):
        # Couleur d'après le titre effectif (gère aussi les schémas à < 4 joueurs).
        return self._TITLE_COLS.get(self.title_for(place), NEUTRAL_COL)

    # ------------------------------------------------------------------
    # Boutons
    # ------------------------------------------------------------------
    def _build_buttons(self):
        y = C.SCREEN_H - 54
        cx = C.SCREEN_W // 2
        self.btn_play = ui.Button((cx - 170, y, 150, 42), "Jouer",
                                  self.human_play, self.small)
        self.btn_pass = ui.Button((cx + 20, y, 150, 42), "Coucher",
                                  self.human_pass, self.small,
                                  fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.btn_decline = ui.Button((cx + 180, y, 160, 42), "Ne pas voler",
                                     self._decline_snap, self.small,
                                     fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.btn_confirm = ui.Button((cx - 145, y, 290, 42),
                                     "Confirmer le don", self.finish_exchange,
                                     self.small)
        self.btn_place = ui.Button((0, 0, 104, 34), "Poser",
                                   self._floating_action, self.small)
        self.btn_menu = ui.Button((C.SCREEN_W - 150, 20, 120, 40), "Menu",
                                  self.app.show_menu, self.small,
                                  fill=(150, 92, 92), text_col=C.TEXT_LIGHT)
        self.over_buttons = [
            ui.Button((cx - 220, 590, 200, 50), "Manche suivante",
                      self._start_round, self.small),
            ui.Button((cx + 20, 590, 200, 50), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]
        self.btn_minus = ui.Button((cx - 176, 338, 64, 64), "−", self._dec,
                                   self.num_font, fill=(96, 120, 150),
                                   text_col=C.TEXT_LIGHT)
        self.btn_plus = ui.Button((cx + 112, 338, 64, 64), "+", self._inc,
                                  self.num_font, fill=(96, 120, 150),
                                  text_col=C.TEXT_LIGHT)
        self.btn_dist = ui.Button((cx - 185, 440, 370, 44), self._dist_label(),
                                  self._toggle_dist, self.small,
                                  fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_small = ui.Button((cx - 185, 490, 370, 44), self._small_label(),
                                   self._toggle_small, self.small,
                                   fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_ai = ui.Button((cx - 185, 490, 370, 44), self._ai_label(),
                                self._toggle_ai, self.small,
                                fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_volee = ui.Button((cx - 185, 540, 370, 44), self._volee_label(),
                                   self._toggle_volee, self.small,
                                   fill=(72, 96, 120), text_col=C.TEXT_LIGHT)
        self.btn_react = ui.Button((cx - 185, 590, 370, 44), self._react_label(),
                                   self._cycle_react, self.small,
                                   fill=(64, 84, 108), text_col=C.TEXT_LIGHT)
        self.btn_steal = ui.Button((cx - 185, 640, 370, 44), self._steal_label(),
                                   self._toggle_steal, self.small,
                                   fill=(64, 84, 108), text_col=C.TEXT_LIGHT)
        self.btn_start = ui.Button((cx - 130, 598, 260, 54), "Commencer",
                                   self._begin, self.font)

    # ---- configuration ----
    def _has_remainder(self):
        return 52 % self.N != 0

    def _dist_label(self):
        return "Équitable" if self.equitable else "Complète"

    def _toggle_dist(self):
        self.equitable = not self.equitable
        self.btn_dist.label = self._dist_label()

    def _small_label(self):
        return ("Vice-Prés. & Vice-Trou" if self.small_roles == "vices"
                else "Président & Trou du cul")

    def _toggle_small(self):
        self.small_roles = "vices" if self.small_roles == "ends" else "ends"
        self.btn_small.label = self._small_label()

    def _ai_label(self):
        return "Forte" if self.ai_level == "mc" else "Normale"

    def _toggle_ai(self):
        self.ai_level = "mc" if self.ai_level == "normal" else "normal"
        self.btn_ai.label = self._ai_label()

    def _volee_label(self):
        return "Activée" if self.a_la_volee else "Désactivée"

    def _toggle_volee(self):
        self.a_la_volee = not self.a_la_volee
        self.btn_volee.label = self._volee_label()

    _REACT_LABELS = {"none": "Ne volent pas",
                     "slow": "Réaction 3 s",
                     "instant": "Instantané"}
    _REACT_CYCLE = ["slow", "instant", "none"]

    def _react_label(self):
        return self._REACT_LABELS[self.snap_reactivity]

    def _cycle_react(self):
        i = self._REACT_CYCLE.index(self.snap_reactivity)
        self.snap_reactivity = self._REACT_CYCLE[(i + 1) % len(self._REACT_CYCLE)]
        self.btn_react.label = self._react_label()

    def _steal_label(self):
        return "Oui" if self.self_steal else "Non"

    def _toggle_steal(self):
        self.self_steal = not self.self_steal
        self.btn_steal.label = self._steal_label()

    def _dec(self):
        self.N = max(2, self.N - 1)

    def _inc(self):
        self.N = min(10, self.N + 1)

    def _begin(self):
        self.g = PresidentGame(self.N, self.equitable, small_roles=self.small_roles)
        self._start_round()

    # ------------------------------------------------------------------
    # Démarrage d'une manche
    # ------------------------------------------------------------------
    def _start_round(self):
        self.moves = []
        self._anim_cb = None
        self.center_display = []
        self.selected = set()
        self.pending = None
        self.think_t = 0.0
        self.pause_t = 0.0
        self.next_leader = None
        self.forced_now = False
        self.toast = ""
        self.toast_t = 0.0
        self._clear_snap()
        self._snap_key = None
        self._snap_declined = None
        res = self.g.new_round()
        if res[0] == "exchange":
            _, self.exchange_mode, self.give_to, self.give_count = res
            if self.exchange_mode == "give_best":
                # cartes imposées (les meilleures), présélectionnées et verrouillées
                self.selected = set(self.g.human_best_gift())
                self.btn_confirm.label = "Donner mes meilleures cartes"
            else:
                self.selected = set()
                self.btn_confirm.label = "Confirmer le don"
            self.phase = "exchange"
            return
        self.phase = "playing"
        if self.g.round_no == 1:
            start = res[1]
            arrow = "sens horaire" if self.g.direction == -1 else "sens antihoraire"
            self._flash(f"{self.g.players[start].name} commence "
                        f"(Dame de cœur) — {arrow}")
        self._schedule(self.g.turn)

    def finish_exchange(self):
        if self.phase != "exchange":
            return
        if self.exchange_mode == "give_best":
            self.g.apply_human_give_best()          # don obligatoire (meilleures)
        elif len(self.selected) == self.give_count:
            self.g.apply_human_gift(list(self.selected))
        else:
            return
        self.selected = set()
        self.phase = "playing"
        self._schedule(self.g.turn)

    # ------------------------------------------------------------------
    # Ordonnancement des tours
    # ------------------------------------------------------------------
    def _schedule(self, idx):
        self.pending = None
        self.think_t = 0.0
        self.forced_now = False
        self.selected = set()          # repartir d'une sélection vide à chaque tour
        p = self.g.players[idx]
        if self.g.is_forced():
            matches = [c for c in p.hand if c.rank == self.g.top_combo[0].rank]
            if matches:
                if p.human:
                    self.forced_now = True
                    self._flash("Main forcée : posez la carte égale ou couchez-vous")
                else:
                    sc = (self.g.self_complete_move(idx)
                          if (self.a_la_volee and self.self_steal) else None)
                    self.pending = ("play", sc if sc else [matches[0]])
                    self.think_t = 0.55
                    self._flash(f"{p.name} — main forcée")
            else:
                self.pending = ("skip",)
                self.think_t = 0.5
                if idx == 0:
                    self._flash("Main forcée : aucune carte égale, tour suivant")
        elif self.g.top_combo is not None and not self.g.has_legal(idx):
            self.pending = ("couche",)
            self.think_t = 0.5
            if idx == 0:
                self._flash("Aucune carte jouable — vous passez")
        elif not p.human:
            self.think_t = random.uniform(0.55, 0.95)
            if self.ai_level == "mc":
                self._mc_launch(idx)       # calcul en fond pendant la réflexion
                self.pending = ("ai_mc",)
            else:
                self.pending = ("ai",)
        # sinon : humain, on attend son action
        self._open_snaps()

    def _mc_launch(self, idx):
        """Lance le Monte-Carlo dans un thread (il ne fait que cloner self.g)."""
        self._mc_result = None
        self._mc_token = token = object()
        g = self.g

        def work():
            try:
                r = ai_mc.choose_mc(g, idx)
            except Exception:
                r = ai.choose(ai.build_view(g, idx))
            if self._mc_token is token:   # ignore un résultat périmé (snap préempté)
                self._mc_result = r

        self._mc_thread = threading.Thread(target=work, daemon=True)
        self._mc_thread.start()

    # ------------------------------------------------------------------
    # « À la volée » : fermeture d'un carré hors-tour (option)
    # ------------------------------------------------------------------
    def _clear_snap(self):
        self.snap_idx = None
        self.snap_cards = None
        self.snap_t = 0.0
        self.snap_hold = False

    def _open_snaps(self):
        """Ouvre une éventuelle occasion de « snap » hors-tour. Au plus un
        joueur peut la saisir. On n'ouvre les snaps que pendant le tour d'une
        IA (jamais quand l'humain réfléchit, sinon une IA fermerait toujours
        avant lui). La réactivité des bots (`snap_reactivity`) règle leur délai :
        « none » (ils ne volent pas + l'humain a tout son temps), « slow » (3 s),
        « instant »."""
        old_key, old_t = self._snap_key, self.snap_t
        self._clear_snap()
        self._snap_key = None
        g = self.g
        if not self.a_la_volee or g is None or g.top_combo is None:
            self._snap_declined = None      # nouveau pli / plus d'occasion
            return
        turn = g.turn
        if turn is None or turn == 0:
            return
        for i in range(self.N):
            if i == turn:
                continue
            mv = g.snap_moves(i)
            if not mv:
                continue
            key = (i, g.top_combo[0].rank, g.required, g.run_cards)
            if g.players[i].human:
                if self.snap_reactivity == "none":
                    if key == self._snap_declined:
                        return              # déjà refusé cette occasion
                    self.snap_idx, self.snap_cards, self._snap_key = i, mv[0], key
                    self.snap_hold = True   # pas de limite : le tour attend
                    self._flash("À la volée possible — à vous (ou « Ne pas voler »)")
                else:
                    self.snap_idx, self.snap_cards, self._snap_key = i, mv[0], key
                    win = 3.0 if self.snap_reactivity == "slow" else 1.0
                    self.think_t = max(self.think_t, win)
                    self._flash("À la volée ! Posez la carte pour fermer le pli")
            else:
                if self.snap_reactivity == "none":
                    return                  # les bots ne volent pas
                self.snap_idx, self.snap_cards, self._snap_key = i, mv[0], key
                base = 3.0 if self.snap_reactivity == "slow" else 0.12
                # même occasion qui perdure : on conserve le temps déjà écoulé
                self.snap_t = old_t if (key == old_key and old_t > 0) else base
            return

    def _decline_snap(self):
        """Bouton « Ne pas voler » (réactivité "none") : renoncer à fermer et
        laisser le jeu reprendre son cours normal."""
        self._snap_declined = self._snap_key
        self._clear_snap()

    def _do_snap(self, idx, cards):
        """Applique un coup « à la volée » (hors-tour) : annule l'action en
        attente du tour courant et pose la fermeture."""
        self.pending = None
        self.think_t = 0.0
        self._mc_thread = None
        self._mc_result = None
        self._mc_token = object()      # invalide un calcul MC en cours
        self._clear_snap()
        self._flash(f"{self.g.players[idx].name} — à la volée !")
        self._do_play(idx, list(cards))

    def _execute(self, pending, idx):
        kind = pending[0]
        if kind == "play":
            self._do_play(idx, pending[1])
        elif kind == "skip":
            self._after_action(self.g.forced_skip(idx))
        elif kind == "couche":
            self._after_action(self.g.couche(idx))
        elif kind == "ai":
            cards = self.ai_pick(idx)
            if cards:
                self._do_play(idx, cards)
            else:
                self._after_action(self.g.couche(idx))

    # ------------------------------------------------------------------
    # Application d'un coup (avec animation)
    # ------------------------------------------------------------------
    def _do_play(self, idx, cards):
        starts = [self._card_origin(idx, c) for c in cards]
        was_chain = (self.g.top_combo is not None and len(cards) == 1
                     and self.g.power(cards[0]) == self.g.power(self.g.top_combo[0]))
        closer_val = self.g.closer_rank()
        was_closer = (cards[0].rank == closer_val)
        res = self.g.play(idx, cards)
        self.phase = "anim"
        self._start_anim(cards, starts,
                         lambda: self._after_play_anim(cards, res, was_chain,
                                                       was_closer, closer_val))

    def _after_play_anim(self, cards, res, was_chain, was_closer, closer_val):
        if was_chain and len(cards) == 1:
            self.center_display += cards
        else:
            self.center_display = list(cards)

        if res.revolution_toggled:
            self._flash("Révolution ! Ordre inversé pour la manche"
                        if self.g.revolution else "Contre-révolution ! Ordre rétabli")
        if res.finished:
            idx2, place = res.finished
            title = self.g.title_for(place)
            if idx2 == 0:
                if was_closer:
                    self._flash(f"Vous finissez sur un {C.rank_label(closer_val)}"
                                f" — vous êtes {title} !")
                else:
                    self._flash(f"Vous avez posé toutes vos cartes — "
                                f"vous êtes {title} !")
            elif was_closer:
                self._flash(f"{self.g.players[idx2].name} finit sur un "
                            f"{C.rank_label(closer_val)} → {title} !")
        if res.round_over:
            self.phase = "round_over"
            return
        if res.trick_closed:
            self.next_leader = res.winner
            self.phase = "pause"
            self.pause_t = 0.85
        else:
            self.phase = "playing"
            self._schedule(self.g.turn)

    def _after_action(self, res):
        if res.round_over:
            self.phase = "round_over"
        elif res.trick_closed:
            self.next_leader = res.winner
            self.phase = "pause"
            self.pause_t = 0.85
        else:
            self.phase = "playing"
            self._schedule(self.g.turn)

    # ------------------------------------------------------------------
    # IA
    # ------------------------------------------------------------------
    def ai_pick(self, idx):
        if self.ai_level == "mc":
            try:
                return ai_mc.choose_mc(self.g, idx)
            except Exception:
                # sécurité : en cas d'imprévu, repli sur l'heuristique
                pass
        return ai.choose(ai.build_view(self.g, idx))

    # ------------------------------------------------------------------
    # Humain
    # ------------------------------------------------------------------
    def human_play(self):
        if self.g is None or self.phase != "playing":
            return
        hand = self.g.players[0].hand
        self.selected = {c for c in self.selected if c in hand}   # écarte tout résidu
        combo = sorted(self.selected, key=self.g.power)
        my_turn = self.turn == 0 and not self.pending

        # « À la volée » hors-tour : poser la fermeture même si ce n'est pas mon tour
        if not my_turn:
            if self.snap_idx == 0 and self.snap_cards:
                rank = self.snap_cards[0].rank
                need = len(self.snap_cards)
                if not combo:
                    self._do_snap(0, self.snap_cards)          # Entrée = snap direct
                elif len(combo) == need and all(c.rank == rank for c in combo):
                    self._do_snap(0, combo)
                else:
                    self._flash("À la volée : sélectionnez la carte qui ferme")
            return

        if not combo:
            self._flash("Sélectionnez une ou plusieurs cartes de même valeur")
            return
        # « Je vole mon propre jeu » : 2 simples égaux d'un coup pour fermer le carré
        if (self.a_la_volee and self.self_steal
                and len(combo) == 2 and self.g.required == 1):
            sc = self.g.self_complete_move(0)
            if sc and combo[0].rank == sc[0].rank:
                self.forced_now = False
                self._do_play(0, combo)
                return
        if self.forced_now and combo[0].rank != self.g.top_combo[0].rank:
            self._flash("Main forcée : posez la carte égale ou couchez-vous")
            return
        if self.g.top_combo is not None and len(combo) != self.g.required:
            self._flash(f"Il faut poser {self.g.required} carte(s)")
            return
        if not self.g.can_beat(combo):
            self._flash("Coup trop faible")
            return
        self.forced_now = False
        self._do_play(0, combo)

    def human_pass(self):
        if self.g is None or self.turn != 0 or self.phase != "playing" or self.pending:
            return
        if self.g.top_combo is None:
            self._flash("Vous ouvrez : vous devez poser")
            return
        self.forced_now = False
        self._after_action(self.g.couche(0))

    def _flash(self, msg):
        self.toast = msg
        self.toast_t = 2.6

    # ------------------------------------------------------------------
    # Géométrie / animations
    # ------------------------------------------------------------------
    def _start_anim(self, cards, starts, on_done):
        targets = self.center_positions(len(cards))
        for c, s, t in zip(cards, starts, targets):
            self.moves.append(Move(c, s, t))
        self._anim_cb = on_done

    def _card_origin(self, idx, card):
        if idx == 0:
            for c, rect in self.hand_layout():
                if c is card:
                    return rect.topleft
        return self._anchor(idx)

    def seat_center(self, seat):
        cx, cy = C.SCREEN_W // 2, 352
        rx, ry = 548, 236
        ang = math.radians(90 + seat * 360 / self.N)
        return (cx + rx * math.cos(ang), cy + ry * math.sin(ang))

    def _anchor(self, idx):
        if idx == 0:
            return (C.SCREEN_W // 2 - self.cw // 2, C.SCREEN_H - 180)
        sx, sy = self.seat_center(idx)
        return (int(sx - self.cw // 2), int(sy - self.ch // 2))

    def center_positions(self, n):
        cw = self.cw
        spread = 46
        cx, cy = C.SCREEN_W // 2, C.SCREEN_H // 2 - 30
        x0 = cx - (spread * (n - 1)) // 2 - cw // 2
        return [(x0 + i * spread, cy - self.ch // 2) for i in range(n)]

    def center_zone(self):
        r = pygame.Rect(0, 0, 380, 210)
        r.center = (C.SCREEN_W // 2, C.SCREEN_H // 2 - 30)
        return r

    def hand_layout(self):
        hand = self.g.players[0].hand
        n = len(hand)
        cw = self.cw
        out = []
        if n == 0:
            return out
        spacing = min(int(cw * 0.72), (1000 - cw) // max(1, n - 1))
        total = spacing * (n - 1) + cw
        x0 = (C.SCREEN_W - total) // 2
        base_y = C.SCREEN_H - self.ch - 66
        for i, c in enumerate(hand):
            y = base_y - (30 if c in self.selected else 0)
            out.append((c, pygame.Rect(x0 + i * spacing, y, cw, self.ch)))
        return out

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------
    def _setup_options(self):
        """Boutons-bascule actifs sur l'écran de config (pour événements/survol)."""
        opts = [self.btn_ai]
        if self._has_remainder():
            opts.append(self.btn_dist)
        if self.N < 4:
            opts.append(self.btn_small)
        opts.append(self.btn_volee)
        if self.a_la_volee:
            opts.append(self.btn_react)
            opts.append(self.btn_steal)
        return opts

    # ---- couleurs des bascules selon leur état (code couleur) ----
    _SETUP_GREY = (92, 104, 118)
    _SETUP_BLUE = (70, 108, 158)
    _SETUP_GREEN = (78, 148, 102)
    _SETUP_ORANGE = (196, 132, 70)
    _SETUP_GOLD = (200, 160, 72)
    _SETUP_RED = (188, 96, 96)

    def _style_setup_buttons(self):
        self.btn_ai.fill = self._SETUP_RED if self.ai_level == "mc" else self._SETUP_BLUE
        self.btn_ai.label = self._ai_label()
        self.btn_dist.fill = self._SETUP_GREEN if self.equitable else self._SETUP_ORANGE
        self.btn_dist.label = self._dist_label()
        self.btn_small.fill = (self._SETUP_ORANGE if self.small_roles == "vices"
                               else self._SETUP_BLUE)
        self.btn_small.label = self._small_label()
        self.btn_small.fill_hover = tuple(min(255, c + 24) for c in self.btn_small.fill)
        self.btn_small.text_col = C.TEXT_LIGHT
        self.btn_volee.fill = self._SETUP_GOLD if self.a_la_volee else self._SETUP_GREY
        self.btn_volee.label = self._volee_label()
        self.btn_react.fill = {"none": self._SETUP_GREY, "slow": self._SETUP_BLUE,
                               "instant": self._SETUP_RED}[self.snap_reactivity]
        self.btn_react.label = self._react_label()
        self.btn_steal.fill = self._SETUP_GOLD if self.self_steal else self._SETUP_GREY
        self.btn_steal.label = self._steal_label()
        for b in (self.btn_ai, self.btn_dist, self.btn_volee, self.btn_react,
                  self.btn_steal):
            b.fill_hover = tuple(min(255, c + 24) for c in b.fill)
            b.text_col = C.TEXT_LIGHT

    def _opt_row(self, px, pw, y, title, desc, button):
        """Une option dans un compartiment : titre (gauche) + bascule (droite),
        description en dessous. Renvoie le y du bas de la ligne."""
        pad, bw, bh = 22, 196, 42
        button.rect.update(px + pw - pad - bw, y, bw, bh)
        self._texts.append((title, self.small, C.TEXT_LIGHT, (px + pad, y + 9),
                            "left"))
        yy = y + bh + 6
        if desc:
            self._texts.append((desc, self.dfont, C.TEXT_DIM, (px + pad, yy),
                                "left"))
            yy += 22
        return yy + 12

    def _layout_setup(self):
        """Construit les compartiments, titres et positions de l'écran de config."""
        self._style_setup_buttons()
        self._panels = []          # (rect, titre, accent)
        self._texts = []           # (texte, police, couleur, pos, alignement)
        self._dividers = []        # (x1, x2, y)
        cx = C.SCREEN_W // 2
        pad = 22
        top = 168
        gap = 40
        pw = 468
        lx = cx - gap // 2 - pw
        rx = cx + gap // 2

        # ---------- Compartiment gauche : PARTIE ----------
        ly = top + 52
        self._texts.append(("Nombre de joueurs", self.small, C.TEXT_LIGHT,
                            (lx + pad, ly + 12), "left"))
        self._texts.append(("Vous + IA", self.dfont, C.TEXT_DIM,
                            (lx + pad, ly + 38), "left"))
        grp_w = 52 + 74 + 52
        gx = lx + pw - pad - grp_w
        self.btn_minus.rect.update(gx, ly, 52, 52)
        self.btn_plus.rect.update(gx + 52 + 74, ly, 52, 52)
        self._num_pos = (gx + 52 + 37, ly + 26)
        ly += 64
        if self._has_remainder():
            self._dividers.append((lx + pad, lx + pw - pad, ly))
            ly += 14
            per, rem = 52 // self.N, 52 % self.N
            if self.equitable:
                desc = f"{per} cartes chacun · {rem} retirée(s) du jeu"
            else:
                desc = f"{rem} voisin(s) à {per + 1}, les autres à {per}"
            ly = self._opt_row(lx, pw, ly, "Distribution des cartes", desc,
                               self.btn_dist)
        else:
            self._dividers.append((lx + pad, lx + pw - pad, ly))
            ly += 14
            self._texts.append(("Distribution", self.small, C.TEXT_LIGHT,
                                (lx + pad, ly), "left"))
            self._texts.append(("52 cartes réparties également — 13 par joueur",
                                self.dfont, C.TEXT_DIM, (lx + pad, ly + 26),
                                "left"))
            ly += 56
        if self.N < 4:
            self._dividers.append((lx + pad, lx + pw - pad, ly))
            ly += 14
            desc = ("Neutre au milieu à 3 joueurs · "
                    + ("1 carte échangée" if self.small_roles == "vices"
                       else "2 cartes échangées"))
            ly = self._opt_row(lx, pw, ly, "Titres (moins de 4 joueurs)", desc,
                               self.btn_small)
        left_bottom = ly + 12
        self._panels.append((pygame.Rect(lx, top, pw, left_bottom - top),
                             "PARTIE", (120, 170, 210)))

        # ---------- Compartiment droit : ADVERSAIRES & RÈGLES ----------
        ry = top + 52
        ry = self._opt_row(rx, pw, ry, "Niveau des adversaires",
                           "Normale : rapide · Forte : Monte-Carlo, redoutable",
                           self.btn_ai)
        self._dividers.append((rx + pad, rx + pw - pad, ry))
        ry += 12
        ry = self._opt_row(rx, pw, ry, "Fermeture « à la volée »",
                           "Fermer un carré hors-tour pour reprendre la main",
                           self.btn_volee)
        if self.a_la_volee:
            self._dividers.append((rx + pad, rx + pw - pad, ry))
            ry += 12
            ry = self._opt_row(rx, pw, ry, "Réactivité des bots",
                               "Vitesse à laquelle les IA volent la fermeture",
                               self.btn_react)
            self._dividers.append((rx + pad, rx + pw - pad, ry))
            ry += 12
            ry = self._opt_row(rx, pw, ry, "Voler son propre jeu",
                               "Poser ses 2 dernières cartes d'un coup, à son tour",
                               self.btn_steal)
        right_bottom = ry + 12
        self._panels.append((pygame.Rect(rx, top, pw, right_bottom - top),
                             "ADVERSAIRES & RÈGLES", (226, 188, 88)))

        start_y = max(left_bottom, right_bottom) + 34
        self.btn_start.rect.update(cx - 150, start_y, 300, 56)

    def _cur_buttons(self):
        if self.phase == "setup":
            self._layout_setup()
            return ([self.btn_minus, self.btn_plus] + self._setup_options()
                    + [self.btn_start, self.btn_menu])
        if self.phase == "round_over":
            return self.over_buttons
        if self.phase == "exchange":
            btns = [self.btn_confirm, self.btn_menu]
            self._place_floating(btns)
            return btns
        btns = [self.btn_play, self.btn_pass, self.btn_menu]
        if self.snap_hold:
            btns.append(self.btn_decline)
        self._place_floating(btns)
        return btns

    def _floating_action(self):
        if self.phase == "exchange":
            self.finish_exchange()
        else:
            self.human_play()

    def _floating_button(self):
        """Rect + libellé du petit bouton flottant au-dessus des cartes
        sélectionnées (« Poser » en jeu, « Donner » à l'échange), ou None."""
        if not self.selected:
            return None
        if self.phase == "exchange":
            ok = (self.exchange_mode == "give_best"
                  or len(self.selected) == self.give_count)
            label = "Donner"
        elif self.phase == "playing" and ((self.turn == 0 and not self.pending)
                                          or self.snap_idx == 0):
            ok, label = True, "Poser"
        else:
            return None
        if not ok:
            return None
        rects = [r for c, r in self.hand_layout() if c in self.selected]
        if not rects:
            return None
        box = rects[0].unionall(rects)
        bw, bh = 104, 34
        bx = max(8, min(box.centerx - bw // 2, C.SCREEN_W - bw - 8))
        return pygame.Rect(bx, box.top - 8 - bh, bw, bh), label

    def _place_floating(self, btns):
        fb = self._floating_button()
        if fb:
            self.btn_place.rect, self.btn_place.label = fb
            btns.append(self.btn_place)

    def handle_event(self, event):
        for b in self._cur_buttons():
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            elif event.key == pygame.K_RETURN and self.phase == "exchange":
                self.finish_exchange()
            elif event.key == pygame.K_RETURN and self.phase == "playing":
                self.human_play()
            elif event.key == pygame.K_SPACE and self.phase == "playing":
                self.human_pass()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (self.phase != "round_over" and self._roles_header
                    and self._roles_header.collidepoint(event.pos)):
                self.roles_open = not self.roles_open
                return
            if self.phase == "exchange":
                self._click_hand(event.pos, exchange=True)
            elif self.phase == "playing" and ((self.turn == 0 and not self.pending)
                                              or self.snap_idx == 0):
                if self.center_zone().collidepoint(event.pos):
                    self.human_play()
                else:
                    self._click_hand(event.pos, exchange=False)

    def _click_hand(self, pos, exchange):
        hit = None
        for c, rect in self.hand_layout():
            if rect.collidepoint(pos):
                hit = c
        if hit is None:
            return
        if exchange:
            if self.exchange_mode == "give_best":
                return          # cartes imposées (meilleures) : pas de triche
            if hit in self.selected:
                self.selected.discard(hit)
            elif len(self.selected) < self.give_count:
                self.selected.add(hit)
            return
        if hit in self.selected:
            self.selected.discard(hit)
        elif not self.selected or next(iter(self.selected)).rank == hit.rank:
            self.selected.add(hit)
        else:
            self.selected = {hit}

    # ------------------------------------------------------------------
    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._cur_buttons():
            b.update(dt, mouse)
        if self.toast_t > 0:
            self.toast_t -= dt
        target = 1.0 if self.roles_open else 0.0
        self.roles_anim += (target - self.roles_anim) * min(1, dt * 12)
        if self.phase == "setup":
            return   # labels/couleurs/positions gérés par _layout_setup

        can_act = self.turn == 0 and self.phase == "playing" and not self.pending
        can_snap = self.phase == "playing" and self.snap_idx == 0
        self.btn_play.enabled = can_act or can_snap
        self.btn_pass.enabled = can_act and self.g.top_combo is not None
        self.btn_confirm.enabled = (self.phase == "exchange"
                                    and (self.exchange_mode == "give_best"
                                         or len(self.selected) == self.give_count))

        done = True
        for m in self.moves:
            m.t += dt / m.dur
            if m.t < 1:
                done = False
        if self.moves and done:
            self.moves = []
        if self.phase == "anim" and not self.moves and self._anim_cb:
            cb, self._anim_cb = self._anim_cb, None
            cb()

        if self.phase == "pause":
            self.pause_t -= dt
            if self.pause_t <= 0:
                self.center_display = []
                self.phase = "playing"
                self._schedule(self.g.turn)

        # « À la volée » : le snappeur IA ferme le pli quand son délai expire
        if (self.phase == "playing" and not self.moves
                and self.snap_idx is not None
                and not self.g.players[self.snap_idx].human):
            self.snap_t -= dt
            if self.snap_t <= 0:
                self._do_snap(self.snap_idx, self.snap_cards)
                return

        if (self.phase == "playing" and not self.moves and self.pending
                and not self.snap_hold):     # hold : l'humain a tout son temps
            self.think_t -= dt
            if self.think_t <= 0:
                if self.pending[0] == "ai_mc":
                    # attendre la fin du calcul en fond (masqué par la réflexion)
                    if self._mc_thread is None or not self._mc_thread.is_alive():
                        self._mc_thread = None
                        cards = self._mc_result
                        self.pending = None
                        idx = self.turn
                        if cards:
                            self._do_play(idx, cards)
                        else:
                            self._after_action(self.g.couche(idx))
                else:
                    pend, self.pending = self.pending, None
                    self._execute(pend, self.turn)

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
        self._draw_center(surface)
        for p in self.g.players:
            self._draw_player(surface, p)
        self._draw_moves(surface)
        self._draw_hud(surface)
        self._draw_roles_panel(surface)   # bandeau horizontal sous le tas central
        for b in self._cur_buttons():
            b.draw(surface)
        if self.toast_t > 0:
            self._draw_toast(surface)
        if self.phase == "round_over":
            self._draw_over(surface)

    def _draw_setup(self, surface):
        cx = C.SCREEN_W // 2
        t = self.big.render("Le Président", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 76)))
        s = self.small.render("Réglez la partie, puis lancez", True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 122)))
        # compartiments
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

    def _draw_center(self, surface):
        r = self.center_zone()
        glow = pygame.Surface(r.size, pygame.SRCALPHA)
        col = (255, 210, 120, 22) if self.revolution else (255, 255, 255, 14)
        edge = (240, 190, 100, 90) if self.revolution else (255, 255, 255, 40)
        pygame.draw.rect(glow, col, glow.get_rect(), border_radius=16)
        pygame.draw.rect(glow, edge, glow.get_rect(), width=2, border_radius=16)
        surface.blit(glow, r.topleft)
        flying = {id(m.card) for m in self.moves}
        cards = self.center_display[-4:]
        for c, pos in zip(cards, self.center_positions(len(cards))):
            if id(c) in flying:
                continue
            surface.blit(self.renderer.face(c), pos)
        if not cards and not self.moves and self.phase != "exchange":
            t = self.small.render("Pli en cours…", True, C.TEXT_DIM)
            surface.blit(t, t.get_rect(center=r.center))

    def _draw_moves(self, surface):
        for m in self.moves:
            t = ui.ease_out_cubic(min(1, m.t))
            x = ui.lerp(m.start[0], m.target[0], t)
            y = ui.lerp(m.start[1], m.target[1], t)
            surface.blit(self.renderer.face(m.card), (x, y))

    def _draw_player(self, surface, p):
        active = (self.turn == p.index and self.phase in ("playing", "anim")
                  and not self.finished(p.index))
        if p.human:
            self._draw_human_hand(surface)
            self._draw_human_status(surface, active)
        else:
            self._draw_ai_pod(surface, p, active)

    def _legal_ranks(self):
        g = self.g
        p = g.players[0]
        groups = {}
        for c in p.hand:
            groups.setdefault(c.rank, []).append(c)
        if self.forced_now:
            return {g.top_combo[0].rank}
        if g.top_combo is None:
            return set(groups)
        r = g.required
        tp = g.power(g.top_combo[0])
        return {rank for rank, cs in groups.items()
                if len(cs) >= r and g.power(cs[0]) >= tp}

    def _active_legal_ranks(self):
        if self.turn == 0 and self.phase == "playing" and not self.pending:
            return self._legal_ranks()
        if self.phase == "playing" and self.snap_idx == 0 and self.snap_cards:
            return {self.snap_cards[0].rank}
        return None

    def _draw_human_hand(self, surface):
        legal = self._active_legal_ranks()
        # À l'ÉCHANGE : les cartes non sélectionnées deviennent transparentes
        # (mise au point sur le don). En jeu, on ne grise QUE les cartes
        # injouables — jamais les cartes qu'on peut encore jouer.
        for c, rect in self.hand_layout():
            surf = self.renderer.face(c)
            illegal = (legal is not None and self.g.top_combo is not None
                       and c.rank not in legal)
            unsel = (self.phase == "exchange" and self.selected
                     and c not in self.selected)
            if illegal or unsel:
                surf = surf.copy()
                surf.fill((120, 120, 130, 120), special_flags=pygame.BLEND_RGBA_MULT)
            if c in self.selected:
                gl = rect.inflate(8, 8)
                pygame.draw.rect(surface, C.ACCENT, gl, border_radius=12)
            surface.blit(surf, rect.topleft)

    def _draw_ai_pod(self, surface, p, active):
        sx, sy = self.seat_center(p.seat)
        sx, sy = int(sx), int(sy)
        n = len(p.hand)
        show = min(n, 7)
        mw, mh = self.mini_back.get_size()
        spread = 12
        total = (show - 1) * spread + mw
        fx = sx - total // 2
        fy = sy - mh - 12
        for i in range(show):
            surface.blit(self.mini_back, (fx + i * spread, fy))
        r = pygame.Rect(0, 0, 168, 50)
        r.center = (sx, sy + 22)
        bg = (70, 96, 120) if active else (46, 62, 78)
        pygame.draw.rect(surface, bg, r, border_radius=11)
        pygame.draw.rect(surface, C.ACCENT if active else (90, 100, 110), r,
                         width=2 if active else 1, border_radius=11)
        surface.blit(self.small.render(p.name, True, C.TEXT_LIGHT),
                     (r.x + 12, r.y + 5))
        if self.finished(p.index):
            pl = self.places[p.index]
            info, col = self.title_for(pl), self.title_col(pl)
        else:
            info, col = f"{n} cartes", C.TEXT_DIM
        surface.blit(self.tiny.render(info, True, col), (r.x + 12, r.y + 28))
        if p.index in self.couched and not self.finished(p.index):
            pt = self.tiny.render("COUCHÉ", True, (210, 160, 90))
            surface.blit(pt, (r.right - pt.get_width() - 10, r.y + 28))
        if p.title and not self.finished(p.index):
            b = self.tiny.render(p.title, True, (230, 210, 150))
            surface.blit(b, (r.right - b.get_width() - 10, r.y + 6))

    def _draw_human_status(self, surface, active):
        p = self.g.players[0]
        r = pygame.Rect(0, 0, 210, 40)
        r.center = (150, C.SCREEN_H - 34)
        bg = (70, 96, 120) if active else (46, 62, 78)
        pygame.draw.rect(surface, bg, r, border_radius=10)
        pygame.draw.rect(surface, C.ACCENT if active else (90, 100, 110), r,
                         width=2 if active else 1, border_radius=10)
        if self.finished(0):
            pl = self.places[0]
            surface.blit(self.tiny.render("Vous · ", True, C.TEXT_LIGHT),
                         (r.x + 12, r.centery - 8))
            w = self.tiny.size("Vous · ")[0]
            surface.blit(self.tiny.render(self.title_for(pl), True,
                                          self.title_col(pl)),
                         (r.x + 12 + w, r.centery - 8))
        else:
            label = f"Vous · {p.title}" if p.title else "Vous"
            surface.blit(self.tiny.render(label, True, C.TEXT_LIGHT),
                         (r.x + 12, r.centery - 8))
        if 0 in self.couched and not self.finished(0):
            pt = self.tiny.render("COUCHÉ", True, (210, 160, 90))
            surface.blit(pt, (r.right - pt.get_width() - 12, r.centery - 8))

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        surface.blit(self.small.render(
            f"Le Président — Manche {self.round_no}  ({self.N} joueurs)",
            True, C.TEXT_LIGHT), (24, 12))
        if self.revolution:
            rv = self.tiny.render("RÉVOLUTION — ordre inversé", True, (240, 190, 100))
            surface.blit(rv, (360, 15))

        if self.phase == "exchange":
            other = self.g.players[self.give_to].name
            if self.exchange_mode == "give_best":
                role = self.g.players[0].title or "Perdant"
                txt = (f"{role} : donnez vos {self.give_count} meilleure(s) "
                       f"carte(s) (en surbrillance) à {other} — obligatoire")
            else:
                txt = (f"Donnez {self.give_count} carte(s) à {other}, "
                       f"puis confirmez")
        elif self.g.top_combo is not None:
            rk = C.rank_label(self.g.top_combo[0].rank)
            txt = f"À battre : {COMBO_NAME[self.g.required]} {rk}"
            if self.g.required == 1 and self.g.run_len > 1:
                txt += f"  (série ×{self.g.run_len})"
        elif self.turn == 0 and self.phase == "playing":
            txt = "À vous d'ouvrir le pli"
        else:
            who = self.g.players[self.turn].name if self.turn is not None else ""
            txt = f"Au tour de {who}…" if who else ""
        if self.phase == "playing" and self.snap_idx == 0:
            txt = "À la volée — posez la carte pour fermer le pli !"
        if txt:
            surf = self.font.render(txt, True, C.ACCENT)
            surface.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, 258)))

    def _draw_roles_panel(self, surface):
        """Bandeau « CLASSEMENT » horizontal, placé dans la bande libre sous le
        tas central (entre le tas et la main) — jamais recouvert par un pod. Une
        colonne par rôle (Neutres regroupés) ; le nom remplace le « ? » dès qu'un
        joueur atteint la place correspondante."""
        if self.g is None or self.phase == "setup":
            return
        by_place = {pl: idx for idx, pl in self.places.items()}

        def name_of(place):
            idx = by_place.get(place)
            return ((self.g.players[idx].name, True) if idx is not None
                    else ("?", False))

        # colonnes : titres clés (nom) + éventuelle colonne « Neutres » (compteur)
        cols = [(self.title_for(0), self.title_col(0), name_of(0))]
        if self.N >= 4:
            cols.append((self.title_for(1), self.title_col(1), name_of(1)))
            neutres = list(range(2, self.N - 2))
            if neutres:
                done = sum(1 for p in neutres if p in by_place)
                cols.append(("Neutres", NEUTRAL_COL,
                             (f"{done} / {len(neutres)}", done > 0)))
            cols.append((self.title_for(self.N - 2), self.title_col(self.N - 2),
                         name_of(self.N - 2)))
        elif self.N == 3:                       # un seul Neutre au milieu
            cols.append((self.title_for(1), self.title_col(1), name_of(1)))
        cols.append((self.title_for(self.N - 1), self.title_col(self.N - 1),
                     name_of(self.N - 1)))

        col_w, gap = 96, 5
        head_h, line_h = 24, 22
        header_h, top = 26, 492
        body_h = 6 + head_h + line_h + 6
        total = len(cols) * col_w + (len(cols) - 1) * gap
        px = C.SCREEN_W // 2 - (total + 24) // 2
        pw = total + 24
        x_in = 12                                   # marge interne (repère local)
        anim = ui.ease_out_cubic(max(0.0, min(1.0, self.roles_anim)))
        self._roles_header = pygame.Rect(px, top, pw, header_h)

        # fond translucide (hauteur = en-tête + corps déroulé)
        ph = header_h + int(anim * body_h)
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(bg, (12, 20, 26, 120), bg.get_rect(), border_radius=13)
        pygame.draw.rect(bg, (255, 255, 255, 24), bg.get_rect(), width=1,
                         border_radius=13)
        surface.blit(bg, (px, top))
        # en-tête cliquable : titre + chevron (triangle dessiné) dérouler / replier
        lab = self.tiny.render("CLASSEMENT", True, C.ACCENT)
        gx = px + pw // 2 - (lab.get_width() + 18) // 2
        cyh = top + header_h // 2
        surface.blit(lab, (gx, cyh - lab.get_height() // 2))
        tx = gx + lab.get_width() + 10
        if self.roles_open:                          # ▾ déroulé
            tri = [(tx - 4, cyh - 3), (tx + 6, cyh - 3), (tx + 1, cyh + 3)]
        else:                                        # ▸ replié
            tri = [(tx - 3, cyh - 5), (tx - 3, cyh + 5), (tx + 3, cyh)]
        pygame.draw.polygon(surface, C.ACCENT, tri)

        # corps animé (colonnes) : dévoilé par le haut + fondu
        if anim > 0.02:
            body = pygame.Surface((pw, body_h), pygame.SRCALPHA)
            for i, (title, col, (value, filled)) in enumerate(cols):
                lx = x_in + i * (col_w + gap)
                pill = pygame.Rect(lx, 4, col_w, head_h)
                p = pygame.Surface(pill.size, pygame.SRCALPHA)
                pygame.draw.rect(p, (col[0], col[1], col[2], 50), p.get_rect(),
                                 border_radius=8)
                pygame.draw.rect(p, col, p.get_rect(), width=2, border_radius=8)
                body.blit(p, pill.topleft)
                ts = self.dfont.render(title, True, col)
                body.blit(ts, ts.get_rect(center=pill.center))
                ns = self.tiny.render(value, True,
                                      C.TEXT_LIGHT if filled else C.TEXT_DIM)
                body.blit(ns, ns.get_rect(center=(lx + col_w // 2,
                                                  4 + head_h + 13)))
            if anim < 1:                            # fondu du corps
                body.fill((255, 255, 255, int(255 * anim)),
                          special_flags=pygame.BLEND_RGBA_MULT)
            clip_h = max(1, int(anim * body_h))     # dévoilé depuis le haut
            surface.blit(body, (px, top + header_h),
                         area=pygame.Rect(0, 0, pw, clip_h))

    def _draw_toast(self, surface):
        alpha = min(1.0, self.toast_t)
        t = self.small.render(self.toast, True, C.TEXT_LIGHT)
        pad = 16
        r = pygame.Rect(0, 0, t.get_width() + pad * 2, t.get_height() + pad)
        r.center = (C.SCREEN_W // 2, C.SCREEN_H - 128)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 24, 30, int(220 * alpha)), s.get_rect(),
                         border_radius=10)
        s.blit(t, (pad, pad // 2))
        s.set_alpha(int(255 * alpha))
        surface.blit(s, r.topleft)

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 175))
        surface.blit(veil, (0, 0))
        title = self.big.render("Fin de la manche", True, C.ACCENT)
        surface.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 130)))
        step = 40
        y0 = 205
        for pl, idx in enumerate(self.ranking):
            p = self.g.players[idx]
            t1 = self.font.render(f"{pl + 1}.  {self.title_for(pl)}", True,
                                  self.title_col(pl))
            t2 = self.font.render(f"— {p.name}", True, C.TEXT_LIGHT)
            y = y0 + pl * step
            surface.blit(t1, (C.SCREEN_W // 2 - 200, y))
            surface.blit(t2, (C.SCREEN_W // 2 + 40, y))
        for b in self.over_buttons:
            b.draw(surface)
