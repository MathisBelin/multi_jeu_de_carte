"""Le Bouclié — jeu d'élimination à base de boucliers (façon Stonehenge).

2 à 10 joueurs (humain = siège 0, IA autonomes). Le paquet ne contient **ni
figures ni jokers** : uniquement les rangs **As (=1) à 10**, l'As étant la plus
faible et le 10 la plus forte (40 cartes, 4 enseignes).

Chaque joueur reçoit 3 cartes : les **deux premières** forment ses **points de
vie** (PV, posées côte à côte face visible), la **troisième** est son **bouclier**
(posée à l'horizontale au-dessus des PV, comme un linteau de Stonehenge).

But : **éliminer les autres**. À son tour, on tire une carte **face cachée** dans
la pioche, puis on choisit une action — la carte n'est **révélée qu'au moment de
l'action** (sauf en cas de **charge**, où elle reste cachée) :

- **Attaquer** un adversaire : force = carte tirée + toutes ses charges cumulées.
  Si force > bouclier → l'adversaire encaisse (force − bouclier) en PV, son
  bouclier reste intact. Si force = bouclier → rien (esquive). Si force < bouclier
  → **l'attaquant** encaisse (bouclier − force) en retour (riposte).
- **Changer un bouclier** (le sien ou celui d'un joueur) : la carte tirée devient
  le nouveau bouclier.
- **Charger** : garder la carte **face cachée** au-dessus de son bouclier (on peut
  en cumuler plusieurs). Toutes les charges partent **d'un coup** lors d'une
  attaque. Perdre des PV fait **perdre toutes ses charges** (sauf si 0 PV perdu).
- **Prendre de la vie** : risqué. Si la carte tirée est > 5, on gagne sa valeur en
  PV ; si elle est < 5, on **perd** ce qui manque pour atteindre 5 (tirer 3 → −2).

Bonus : avoir un **As en bouclier** au début de son tour permet de **voir** la
valeur de la carte tirée avant de choisir.

Présentation : les joueurs sont disposés **en cercle** (ellipse), l'humain en bas.
La carte piochée **vole vers le joueur actif**, un **bandeau** annonce l'action
choisie et sa cible, puis la carte **vole vers la cible** avant de résoudre.
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

SHAKE_DUR = 0.42
GLOW_DUR = 0.9


def pv_to_cards(pv):
    """Représente un total de PV par une suite de cartes (10 puis le reste),
    pour l'affichage « côte à côte » — cosmétique, la vérité reste l'entier PV."""
    cards, remaining, i = [], max(0, pv), 0
    suits = [C.HEART, C.SPADE, C.DIAMOND, C.CLUB]
    while remaining > 0:
        v = min(10, remaining)
        cards.append(Card(suits[i % 4], v))
        remaining -= v
        i += 1
    return cards


class BPlayer:
    def __init__(self, idx, name, human):
        self.idx = idx
        self.name = name
        self.human = human
        self.pv = 0
        self.pv_cards = []
        self.shield = None
        self.charges = []
        self.alive = True


class Fly:
    """Carte en vol (dos ou face)."""
    def __init__(self, card, start, target, dur=0.42, face_down=False):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0
        self.face_down = face_down


class FloatText:
    """Texte flottant (dégâts, soin, « Bloqué », « Riposte »…)."""
    def __init__(self, text, pos, color, dur=1.5, big=True):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.t = 0.0
        self.dur = dur
        self.big = big


class BouclieScene(Scene):
    MAX_STEPS = 20000

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(88, 126)     # pioche / défausse
        self.mid = CardRenderer(62, 88)           # cartes du joueur + en vol
        self.mini = CardRenderer(34, 48)          # cartes des adversaires (compactes)
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)
        self.big = pygame.font.SysFont(C.FONT_UI, 52, bold=True)
        self.dmg_font = pygame.font.SysFont(C.FONT_UI, 34, bold=True)
        self.banner_font = pygame.font.SysFont(C.FONT_UI, 20, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 44, bold=True)

        self.cx = C.SCREEN_W // 2
        # pioche / défausse dans les coins bas (assez basses pour que leur
        # libellé, dessiné au-dessus, ne soit pas recouvert par les pods du bas)
        self.PILE = (46, 638)
        self.DISCARD = (C.SCREEN_W - 46 - 88, 638)
        # cercle (ellipse) des joueurs, humain en bas ; sommet sous le bandeau HUD
        self.EC = (self.cx, 396)
        self.RX, self.RY = 552, 290

        self.N = 4
        self.phase = "setup"
        self.deck = []
        self.discard = []
        self.players = []
        self.cur = 0
        self.direction = 1
        self.drawn = None
        self.peek = False
        self.pending_action = None
        self.think_t = 0.0
        self.hold_t = 0.0
        self.flies = []
        self._after = None
        # animation d'action
        self.timeline = []
        self.tl_i = 0
        self.tl_t = 0.0
        self.stage = []                 # cartes révélées (près de l'acteur)
        self.reveal_c = (self.cx, 300)  # centre de la zone de révélation
        self.force_show = None
        self.proj = None                # carte « projectile » (acteur → cible)
        self.banner = None              # (texte, couleur, seat) de l'action choisie
        self.floats = []
        self.shakes = {}
        self.glow = {}
        self.toast = ""
        self.winner = None
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
        self.btn_minus = ui.Button((cx - 176, 338, 64, 64), "−", self._dec,
                                   self.num_font, fill=(96, 120, 150),
                                   text_col=C.TEXT_LIGHT)
        self.btn_plus = ui.Button((cx + 112, 338, 64, 64), "+", self._inc,
                                  self.num_font, fill=(96, 120, 150),
                                  text_col=C.TEXT_LIGHT)
        self.btn_start = ui.Button((cx - 130, 470, 260, 54), "Commencer",
                                   self.new_game, self.font)
        w, h, y, g = 214, 46, 598, 12
        total = 4 * w + 3 * g
        x0 = cx - total // 2
        self.btn_attack = ui.Button((x0, y, w, h), "Attaquer",
                                    lambda: self._choose("attack"), self.small,
                                    fill=(170, 84, 84), text_col=C.TEXT_LIGHT)
        self.btn_shield = ui.Button((x0 + (w + g), y, w, h), "Changer bouclier",
                                    lambda: self._choose("shield"), self.small,
                                    fill=(84, 116, 160), text_col=C.TEXT_LIGHT)
        self.btn_charge = ui.Button((x0 + 2 * (w + g), y, w, h), "Charger",
                                    lambda: self._choose("charge"), self.small,
                                    fill=(150, 120, 72), text_col=C.TEXT_LIGHT)
        self.btn_heal = ui.Button((x0 + 3 * (w + g), y, w, h), "Prendre de la vie",
                                  lambda: self._choose("heal"), self.small,
                                  fill=(86, 148, 104), text_col=C.TEXT_LIGHT)
        self.btn_cancel = ui.Button((cx - 90, 598, 180, 46), "Annuler",
                                    self._cancel_target, self.small,
                                    fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        self.over_buttons = [
            ui.Button((cx - 230, 596, 210, 52), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 596, 210, 52), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _dec(self):
        self.N = max(2, self.N - 1)

    def _inc(self):
        self.N = min(10, self.N + 1)

    def _action_buttons(self):
        return [self.btn_attack, self.btn_shield, self.btn_charge, self.btn_heal]

    def _cur_buttons(self):
        if self.phase == "setup":
            return [self.btn_minus, self.btn_plus, self.btn_start, self.btn_menu]
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        if self.phase == "choose":
            return list(self._action_buttons()) + [self.btn_menu]
        if self.phase in ("target_attack", "target_shield"):
            return [self.btn_cancel, self.btn_menu]
        return [self.btn_menu]

    # ------------------------------------------------------------------
    # Mise en place
    # ------------------------------------------------------------------
    def _fresh_deck(self):
        deck = [Card(s, r) for s in C.SUITS for r in range(1, 11)]
        random.shuffle(deck)
        return deck

    def _draw_card(self):
        if not self.deck:
            self.deck = self.discard
            self.discard = []
            random.shuffle(self.deck)
        if not self.deck:
            self.deck = self._fresh_deck()
        return self.deck.pop()

    def new_game(self):
        self.deck = self._fresh_deck()
        self.discard = []
        self.players = [BPlayer(i, self._name(i), human=(i == 0))
                        for i in range(self.N)]
        for p in self.players:
            a, b, sh = self._draw_card(), self._draw_card(), self._draw_card()
            p.pv = a.rank + b.rank
            p.pv_cards = [a, b]
            p.shield = sh
            p.charges = []
            p.alive = True
        self.drawn = None
        self.peek = False
        self.pending_action = None
        self.flies = []
        self._after = None
        self.timeline = []
        self.stage = []
        self.force_show = None
        self.proj = None
        self.banner = None
        self.floats = []
        self.shakes = {}
        self.glow = {}
        self.toast = ""
        self.winner = None
        self.direction = random.choice([1, -1])
        self._layout_seats()
        self._start_turn(random.randrange(self.N))

    def _name(self, i):
        return NAMES[i] if i < len(NAMES) else f"Joueur {i}"

    def _layout_seats(self):
        """Disposition en cercle : humain en bas, adversaires sur l'arc supérieur
        de l'ellipse (de bas-gauche à bas-droite en passant par le haut)."""
        self.pod = {0: (self.cx, C.SCREEN_H - 168)}
        opp = list(range(1, self.N))
        m = len(opp)
        for j, seat in enumerate(opp):
            if m == 1:
                ang = 90.0
            else:
                ang = 206.0 - 232.0 * (j / (m - 1))   # 206° (bas-g.) → -26° (bas-d.)
            rad = math.radians(ang)
            x = self.EC[0] + self.RX * math.cos(rad)
            y = self.EC[1] - self.RY * math.sin(rad)
            self.pod[seat] = (int(x), int(y))

    def _inward(self, seat, d):
        """Point à distance d du pod, vers le centre du cercle."""
        px, py = self.pod[seat]
        dx, dy = self.EC[0] - px, self.EC[1] - py
        L = math.hypot(dx, dy) or 1.0
        return (px + dx / L * d, py + dy / L * d)

    # ------------------------------------------------------------------
    # Tours
    # ------------------------------------------------------------------
    def _alive_seats(self):
        return [i for i in range(self.N) if self.players[i].alive]

    def _next_alive(self, frm):
        for k in range(1, self.N + 1):
            j = (frm + k * self.direction) % self.N
            if self.players[j].alive:
                return j
        return frm

    def _start_turn(self, seat):
        alive = self._alive_seats()
        if len(alive) <= 1:
            self.winner = alive[0] if alive else None
            self.phase = "over"
            return
        if not self.players[seat].alive:
            seat = self._next_alive(seat)
        self.cur = seat
        self.drawn = self._draw_card()
        p = self.players[seat]
        self.peek = (p.shield.rank == 1)
        self.pending_action = None
        self.stage = []
        self.force_show = None
        self.proj = None
        self.banner = None
        # la carte piochée vole vers le joueur actif
        self.flies = [Fly(self.drawn, (self.PILE[0], self.PILE[1]),
                          self._held_pos(seat), face_down=True)]
        self._after = self._after_draw
        self.phase = "draw"

    def _after_draw(self):
        if self.players[self.cur].human:
            self.phase = "choose"
        else:
            self.phase = "ai_think"
            self.think_t = 0.7

    def _advance_turn(self):
        self.stage = []
        self.proj = None
        self.banner = None
        alive = self._alive_seats()
        if len(alive) <= 1:
            self.winner = alive[0] if alive else None
            self.phase = "over"
            return
        self._start_turn(self._next_alive(self.cur))

    def _go_hold(self, t):
        self.proj = None
        self.phase = "hold"
        self.hold_t = t

    # ---- choix humain ----
    def _choose(self, action):
        if self.phase != "choose":
            return
        if action == "charge":
            self._perform(self.cur, "charge", None)
        elif action == "heal":
            self._perform(self.cur, "heal", None)
        elif action == "attack":
            if self._attack_targets():
                self.pending_action = "attack"
                self.phase = "target_attack"
        elif action == "shield":
            self.pending_action = "shield"
            self.phase = "target_shield"

    def _cancel_target(self):
        if self.phase in ("target_attack", "target_shield"):
            self.pending_action = None
            self.phase = "choose"

    def _attack_targets(self):
        return [i for i in self._alive_seats() if i != self.cur]

    def _shield_targets(self):
        return list(self._alive_seats())

    # ------------------------------------------------------------------
    # Positions d'animation
    # ------------------------------------------------------------------
    def _held_pos(self, seat):
        if seat == 0:      # humain : au-dessus de la rangée de boutons d'action
            return (self.cx - self.mid.w // 2, C.SCREEN_H - 320)
        ix, iy = self._inward(seat, 62)
        return (int(ix - self.mid.w // 2), int(iy - self.mid.h // 2))

    def _reveal_center(self, seat):
        ix, iy = self._inward(seat, 150)
        ix = max(210, min(C.SCREEN_W - 210, ix))
        iy = max(150, min(C.SCREEN_H - 300, iy))
        return (ix, iy)

    def _pod_target(self, seat):
        cx, cy = self.pod[seat]
        return (cx - self.mid.w // 2, cy - self.mid.h // 2)

    def _charge_pos(self, seat):
        cx, cy = self.pod[seat]
        off = 44 if seat != 0 else 130
        return (cx + off, cy - self.mid.h // 2 - 8)

    def _pod_anchor(self, seat):
        cx, cy = self.pod[seat]
        return (cx, cy)

    def _banner_pos(self, seat):
        cx, cy = self.pod[seat]
        if seat == 0:
            return (cx, cy - 118)
        return (cx, max(70, cy - 92))

    # ------------------------------------------------------------------
    # Effets visuels
    # ------------------------------------------------------------------
    def _float(self, seat, text, color, big=True):
        self.floats.append(FloatText(text, self._pod_anchor(seat), color, big=big))

    def _shake(self, seat):
        self.shakes[seat] = SHAKE_DUR

    def _glow_shield(self, seat):
        self.glow[seat] = GLOW_DUR

    def _shake_offset(self, seat):
        t = self.shakes.get(seat, 0.0)
        if t <= 0:
            return 0
        return int(math.sin(t * 55) * 9 * (t / SHAKE_DUR))

    def _set_banner(self, seat, text, color):
        self.banner = (text, color, seat)

    def _change_pv(self, p, delta):
        p.pv += delta
        if delta < 0 and p.charges:
            self.discard.extend(p.charges)
            p.charges = []
        p.pv_cards = pv_to_cards(p.pv)
        if p.pv <= 0:
            p.alive = False
            self.discard.append(p.shield)
            self.discard.extend(p.charges)
            p.charges = []

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------
    def _stage_layout(self, cards, center):
        cw = self.mid.w
        n = len(cards)
        gap = 12
        total = n * cw + (n - 1) * gap
        x0 = center[0] - total // 2
        y = center[1] - self.mid.h // 2
        return [{"card": c, "x": x0 + i * (cw + gap), "y": y,
                 "flip": 0.0, "rev": False} for i, c in enumerate(cards)]

    def _reveal_stage(self, i, add=None):
        if 0 <= i < len(self.stage):
            self.stage[i]["rev"] = True
        if add is not None:
            self.force_show = (self.force_show or 0) + add

    def _cast(self, actor, target):
        """Lance la carte tirée (face visible) de la zone de révélation vers la
        cible ; les cartes de révélation disparaissent dans le projectile."""
        start = (self.reveal_c[0] - self.mid.w // 2,
                 self.reveal_c[1] - self.mid.h // 2)
        self.stage = []
        self.proj = {"card": self.drawn, "start": start,
                     "target": self._pod_target(target), "t": 0.0, "dur": 0.42,
                     "face_down": False}

    def _start_timeline(self):
        self.tl_i = 0
        self.tl_t = 0.0
        self.phase = "anim"
        if self.timeline:
            self.timeline[0]["fn"]()

    def _advance_timeline(self, dt):
        step = self.timeline[self.tl_i]
        self.tl_t += dt
        if self.tl_t >= step["dur"]:
            self.tl_i += 1
            self.tl_t = 0.0
            if self.tl_i >= len(self.timeline):
                self.timeline = []
                self._go_hold(1.15)
            else:
                self.timeline[self.tl_i]["fn"]()

    # ------------------------------------------------------------------
    # Exécution d'une action
    # ------------------------------------------------------------------
    def _perform(self, actor, action, target):
        self.pending_action = None
        a = self.players[actor]
        if action == "attack":
            self._set_banner(actor, f"ATTAQUE  >  {self.players[target].name}", RED)
            self._anim_attack(actor, target)
        elif action == "shield":
            who = "(sur soi)" if target == actor else f">  {self.players[target].name}"
            self._set_banner(actor, f"BOUCLIER  {who}", BLUE)
            self._anim_single(actor, target, self._apply_shield)
        elif action == "heal":
            self._set_banner(actor, "SOIN", GREEN)
            self._anim_single(actor, actor, self._apply_heal)
        else:
            self._set_banner(actor, f"CHARGE  ×{len(a.charges) + 1}", GOLD)
            self._anim_charge(actor)

    def _anim_attack(self, actor, target):
        a = self.players[actor]
        seq = list(a.charges) + [self.drawn]
        self.reveal_c = self._reveal_center(actor)
        self.stage = self._stage_layout(seq, self.reveal_c)
        self.force_show = 0
        self.toast = f"{a.name} attaque {self.players[target].name}…"
        tl = []
        for i, c in enumerate(seq):
            tl.append({"dur": 0.5, "fn": (lambda i=i, v=c.rank: self._reveal_stage(i, v))})
        tl.append({"dur": 0.42, "fn": (lambda: self._cast(actor, target))})
        tl.append({"dur": 0.35, "fn": (lambda: self._strike(actor, target))})
        self.timeline = tl
        self._start_timeline()

    def _anim_single(self, actor, target, apply_fn):
        self.reveal_c = self._reveal_center(actor)
        self.stage = self._stage_layout([self.drawn], self.reveal_c)
        self.force_show = None
        self.timeline = [
            {"dur": 0.5, "fn": (lambda: self._reveal_stage(0))},
            {"dur": 0.42, "fn": (lambda: self._cast(actor, target))},
            {"dur": 0.35, "fn": (lambda: apply_fn(actor, target))},
        ]
        self._start_timeline()

    def _anim_charge(self, actor):
        a = self.players[actor]
        card = self.drawn
        self.drawn = None
        a.charges.append(card)
        self.proj = {"card": card, "start": self._held_pos(actor),
                     "target": self._charge_pos(actor), "t": 0.0, "dur": 0.45,
                     "face_down": True}
        self.toast = f"{a.name} charge — {len(a.charges)} carte(s) en réserve"
        self._float(actor, f"Charge ×{len(a.charges)}", GOLD, big=False)
        self.timeline = [{"dur": 0.5, "fn": (lambda: None)}]
        self._start_timeline()

    # ---- résolutions ----
    def _strike(self, actor, target):
        a, t = self.players[actor], self.players[target]
        atk = self.force_show or 0
        n_ch = len(a.charges)
        self.discard.append(self.drawn)
        self.discard.extend(a.charges)
        a.charges = []
        self.drawn = None
        self.proj = None
        sh = t.shield.rank
        extra = f" (+{n_ch} charge{'s' if n_ch > 1 else ''})" if n_ch else ""
        if atk > sh:
            dmg = atk - sh
            self._change_pv(t, -dmg)
            self._shake(target)
            self._float(target, f"−{dmg} PV", RED)
            self.toast = f"{a.name} touche {t.name} : {atk}{extra} vs bouclier {sh} → −{dmg} PV"
        elif atk == sh:
            self._glow_shield(target)
            self._float(target, "Bloqué !", BLUE)
            self.toast = f"{a.name} : {atk}{extra} = bouclier {sh} → esquive, aucun dégât"
        else:
            recoil = sh - atk
            self._change_pv(a, -recoil)
            self._shake(actor)
            self._glow_shield(target)
            self._float(target, "Riposte !", GOLD, big=False)
            self._float(actor, f"−{recoil} PV", RED)
            self.toast = f"Bouclier {sh} > {atk}{extra} : riposte, {a.name} perd {recoil} PV"
        self.stage = []
        self.force_show = None

    def _apply_shield(self, actor, target):
        t = self.players[target]
        old = t.shield.rank
        self.discard.append(t.shield)
        t.shield = self.drawn
        self.drawn = None
        self.proj = None
        self._glow_shield(target)
        self._float(target, f"Bouclier {old}→{t.shield.rank}", BLUE, big=False)
        who = "son bouclier" if target == actor else f"le bouclier de {t.name}"
        self.toast = f"{self.players[actor].name} change {who} : {old} → {t.shield.rank}"
        self.stage = []

    def _apply_heal(self, actor, target):
        a = self.players[actor]
        v = self.drawn.rank
        self.discard.append(self.drawn)
        self.drawn = None
        self.proj = None
        if v <= 5:
            self._change_pv(a, v)
            self._float(actor, f"+{v} PV", GREEN)
            self.toast = f"{a.name} se soigne : tire {v} (≤5) → +{v} PV"
        else:
            loss = v - 5
            self._change_pv(a, -loss)
            self._float(actor, f"−{loss} PV (raté)", RED)
            self.toast = f"{a.name} rate son soin : tire {v} (>5) → −{loss} PV"
        self.stage = []

    # ---- IA : choisit la meilleure décision (scoring, joue à l'aveugle) ----
    # Volontairement AGRESSIVE : privilégie l'attaque, charge pour percer les
    # gros boucliers, et ne se soigne / renforce que si vraiment bas — sinon les
    # bots joueraient trop en défense et la partie ne se terminerait jamais.
    def _ai_decide(self, seat):
        me = self.players[seat]
        opps = [self.players[i] for i in self._attack_targets()]
        E = 5.5
        val = self.drawn.rank if self.peek else E   # As en bouclier → carte connue
        charges = sum(c.rank for c in me.charges)
        force = val + charges
        cands = []

        best_dmg = 0
        if opps:
            t = min(opps, key=lambda o: (o.shield.rank, o.pv))
            dmg = force - t.shield.rank
            best_dmg = dmg
            s = dmg + 1.5                      # biais d'agression
            if force <= t.shield.rank:
                s -= 3.5                       # risque de riposte
            if dmg >= t.pv:
                s += 8.0                       # met à mort
            if me.charges:
                s += 3.0                       # dépenser les charges avant de les perdre
            cands.append((s, "attack", t.idx))

        # charger pour percer si une attaque directe ne passerait pas
        if me.pv >= 6 and best_dmg < 2 and len(me.charges) < 3:
            cands.append((2.5, "charge", None))

        # ne renforcer son bouclier que s'il est vraiment faible
        if me.shield.rank <= 3:
            cands.append(((4 - me.shield.rank) * 1.2, "shield", seat))

        # saboter : baisser le bouclier d'un adversaire très protégé
        if opps:
            strong = max(opps, key=lambda o: (o.shield.rank, o.pv))
            if strong.shield.rank >= 8:
                cands.append(((strong.shield.rank - 6) * 0.9, "shield", strong.idx))

        # ne se soigner qu'en danger réel ; le soin rend +v si v≤5, sinon −(v−5)
        # (espérance nulle à l'aveugle) → on évite si la carte connue (peek) est >5
        heal_gain = (val if val <= 5 else -(val - 5)) if self.peek else 0.0
        if me.pv <= 4 and heal_gain >= 0:
            cands.append(((5 - me.pv) * 1.3 + 1.0 + heal_gain, "heal", None))

        best = max(cands, key=lambda c: c[0] + random.uniform(0.0, 0.5))
        return best[1], best[2]

    # ------------------------------------------------------------------
    # Événements
    # ------------------------------------------------------------------
    def handle_event(self, event):
        for b in self._cur_buttons():
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.show_menu()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN) and self.phase == "hold":
                self._advance_turn()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.phase == "hold":
                self._advance_turn()
                return
            if self.phase in ("target_attack", "target_shield"):
                valid = (self._attack_targets() if self.phase == "target_attack"
                         else self._shield_targets())
                for seat in valid:
                    if self._pod_hitbox(seat).collidepoint(event.pos):
                        self._perform(self.cur, self.pending_action, seat)
                        return
            return

    def _pod_hitbox(self, seat):
        cx, cy = self.pod[seat]
        if seat == 0:      # zone humaine (bas), sous la rangée de boutons
            return pygame.Rect(cx - 160, 648, 320, 160)
        return pygame.Rect(cx - 82, cy - 58, 164, 130)

    # ------------------------------------------------------------------
    # Boucle
    # ------------------------------------------------------------------
    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        for b in self._cur_buttons():
            b.update(dt, mouse)
        if self.phase in ("setup", "over"):
            return
        self._animate_fx(dt)

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
        if self.timeline:
            self._advance_timeline(dt)
            return
        if self.phase == "ai_think":
            self.think_t -= dt
            if self.think_t <= 0:
                action, target = self._ai_decide(self.cur)
                self._perform(self.cur, action, target)
        elif self.phase == "hold":
            self.hold_t -= dt
            if self.hold_t <= 0:
                self._advance_turn()

    def _animate_fx(self, dt):
        for f in self.floats:
            f.t += dt
        self.floats = [f for f in self.floats if f.t < f.dur]
        for s in list(self.shakes):
            self.shakes[s] -= dt
            if self.shakes[s] <= 0:
                del self.shakes[s]
        for s in list(self.glow):
            self.glow[s] -= dt
            if self.glow[s] <= 0:
                del self.glow[s]
        for c in self.stage:
            if c["rev"] and c["flip"] < 1.0:
                c["flip"] = min(1.0, c["flip"] + dt / 0.3)
        if self.proj and self.proj["t"] < 1.0:
            self.proj["t"] = min(1.0, self.proj["t"] + dt / self.proj["dur"])

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
        self._draw_piles(surface)
        self._draw_opponents(surface)
        self._draw_human(surface)
        self._draw_held(surface)
        self._draw_stage(surface)
        for f in self.flies:
            img = self.mid.back if f.face_down else self.mid.face(f.card)
            x = ui.lerp(f.start[0], f.target[0], ui.ease_out_cubic(min(1, f.t)))
            y = ui.lerp(f.start[1], f.target[1], ui.ease_out_cubic(min(1, f.t)))
            surface.blit(img, (int(x), int(y)))
        if self.proj:
            p = self.proj
            img = self.mid.back if p["face_down"] else self.mid.face(p["card"])
            t = ui.ease_out_cubic(min(1, p["t"]))
            x = ui.lerp(p["start"][0], p["target"][0], t)
            y = ui.lerp(p["start"][1], p["target"][1], t)
            surface.blit(img, (int(x), int(y)))
        self._draw_banner(surface)
        self._draw_floats(surface)
        for b in self._cur_buttons():
            b.draw(surface)
        if self.phase == "over":
            self._draw_over(surface)

    def _draw_setup(self, surface):
        cx = self.cx
        t = self.big.render("Le Bouclié", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 120)))
        s = self.small.render("Éliminez les autres — chacun a des PV et un bouclier",
                              True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 170)))
        pw, ph = 560, 150
        px, py = cx - pw // 2, 250
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 20, 26, 120), panel.get_rect(),
                         border_radius=16)
        pygame.draw.rect(panel, (255, 255, 255, 26), panel.get_rect(),
                         width=1, border_radius=16)
        surface.blit(panel, (px, py))
        hs = self.tiny.render("RÉGLAGES DE LA PARTIE", True, C.ACCENT)
        surface.blit(hs, (px + 22, py + 16))
        pad = 22
        self.btn_minus.rect.update(px + pw - pad - 180, py + 58, 56, 56)
        self.btn_plus.rect.update(px + pw - pad - 56, py + 58, 56, 56)
        surface.blit(self.small.render("Nombre de joueurs", True, C.TEXT_LIGHT),
                     (px + pad, py + 62))
        surface.blit(self.dfont.render("Vous + IA (2 à 10)", True, C.TEXT_DIM),
                     (px + pad, py + 88))
        num = self.num_font.render(str(self.N), True, C.TEXT_LIGHT)
        surface.blit(num, num.get_rect(center=(px + pw - pad - 90, py + 86)))
        self.btn_start.rect.update(cx - 130, py + 180, 260, 54)

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        surface.blit(self.title_font.render("Le Bouclié", True, C.TEXT_LIGHT),
                     (24, 10))
        arrow = "sens >>" if self.direction == 1 else "sens <<"
        surface.blit(self.small.render(arrow, True, C.TEXT_DIM), (200, 15))
        if self.phase == "choose":
            msg = ("À vous : choisissez une action"
                   if not self.peek else
                   f"À vous — As en bouclier : la carte tirée vaut {self.drawn.rank}")
            col = C.ACCENT
        elif self.phase == "target_attack":
            msg, col = "Cliquez l'adversaire à attaquer (ou Annuler)", C.ACCENT
        elif self.phase == "target_shield":
            msg, col = "Cliquez le bouclier à changer — le vôtre ou un autre", C.ACCENT
        elif self.phase == "draw":
            msg, col = f"{self.players[self.cur].name} pioche…", C.TEXT_DIM
        elif self.phase == "ai_think":
            msg, col = f"{self.players[self.cur].name} réfléchit…", C.TEXT_DIM
        else:
            msg, col = self.toast, C.TEXT_LIGHT
        if msg:
            s = self.small.render(msg, True, col)
            surface.blit(s, s.get_rect(center=(self.cx, 24)))

    def _draw_pile(self, surface, pos, label, top_card=None):
        # même présence / taille pour les deux piles : un dos plein, avec
        # éventuellement la carte du dessus (défausse) posée par-dessus.
        surface.blit(self.renderer.back, pos)
        if top_card is not None:
            surface.blit(self.renderer.face(top_card), pos)
        l = self.tiny.render(label, True, C.TEXT_DIM)
        surface.blit(l, l.get_rect(center=(pos[0] + self.renderer.w // 2,
                                           pos[1] - 12)))

    def _draw_piles(self, surface):
        self._draw_pile(surface, self.PILE, "Pioche")
        self._draw_pile(surface, self.DISCARD, "Défausse",
                        top_card=self.discard[-1] if self.discard else None)

    def _draw_shield(self, surface, card, center, rend, glow_t=0.0):
        img = pygame.transform.rotate(rend.face(card), 90)
        r = img.get_rect(center=center)
        if glow_t > 0:
            a = int(200 * (glow_t / GLOW_DUR))
            halo = pygame.Surface((r.w + 20, r.h + 20), pygame.SRCALPHA)
            pygame.draw.rect(halo, (*BLUE, a), halo.get_rect(), width=5,
                             border_radius=12)
            surface.blit(halo, (r.x - 10, r.y - 10))
        surface.blit(img, r)
        return r

    def _shield_shape(self, cx, cy, w, h):
        top = cy - h // 2
        return [(cx - w // 2, top), (cx + w // 2, top),
                (cx + w // 2, int(top + h * 0.42)), (cx, cy + h // 2),
                (cx - w // 2, int(top + h * 0.42))]

    def _draw_shield_badge(self, surface, center, value, glow_t=0.0, big=False):
        """Écusson « bouclier + valeur » : logo clair de la force du bouclier."""
        cx, cy = int(center[0]), int(center[1])
        w, h = (44, 50) if big else (34, 40)
        font = self.font if big else self.tiny
        if glow_t > 0:
            a = int(220 * (glow_t / GLOW_DUR))
            pygame.draw.polygon(surface, (*BLUE, a),
                                self._shield_shape(cx, cy, w + 10, h + 10), 4)
        pygame.draw.polygon(surface, (26, 44, 66), self._shield_shape(cx, cy, w, h))
        pygame.draw.polygon(surface, BLUE, self._shield_shape(cx, cy, w, h), 2)
        t = font.render(str(value), True, (236, 242, 248))
        surface.blit(t, t.get_rect(center=(cx, cy - 1)))

    def _draw_pv_row(self, surface, cards, center_x, top_y, rend):
        cw, gap = rend.w, 6
        n = max(1, len(cards))
        total = n * cw + (n - 1) * gap
        x0 = center_x - total // 2
        for i, c in enumerate(cards):
            surface.blit(rend.face(c), (x0 + i * (cw + gap), top_y))

    def _draw_opponents(self, surface):
        valid = []
        if self.phase == "target_attack":
            valid = self._attack_targets()
        elif self.phase == "target_shield":
            valid = self._shield_targets()
        for seat in range(1, self.N):
            p = self.players[seat]
            ox = self._shake_offset(seat)
            cx, cy = self.pod[seat][0] + ox, self.pod[seat][1]
            if seat in valid:
                pygame.draw.rect(surface, GOLD, self._pod_hitbox(seat).move(ox, 0),
                                 width=3, border_radius=12)
            if not p.alive:
                plate = pygame.Rect(0, 0, 150, 40)
                plate.center = (cx, cy)
                pygame.draw.rect(surface, (40, 46, 52), plate, border_radius=10)
                pygame.draw.rect(surface, (90, 96, 102), plate, width=1,
                                 border_radius=10)
                s = self.tiny.render(f"{p.name} · éliminé", True, RED)
                surface.blit(s, s.get_rect(center=plate.center))
                continue
            # bouclier en CARTE (Stonehenge) au-dessus, + charges éventuelles
            self._draw_shield(surface, p.shield, (cx, cy - 40), self.mini,
                              glow_t=self.glow.get(seat, 0.0))
            if not (seat == self.cur and self.stage):
                for k in range(len(p.charges)):
                    surface.blit(pygame.transform.rotate(self.mini.back, 90),
                                 (cx + 30 + k * 5, cy - 40 - self.mini.w // 2))
            # PV en cartes
            self._draw_pv_row(surface, p.pv_cards, cx, cy - 20, self.mini)
            # plaque : écusson bouclier (logo + valeur) + nom + PV
            drawer = (seat == self.cur)
            plate = pygame.Rect(0, 0, 158, 44)
            plate.center = (cx, cy + 48)
            bg = (70, 96, 120) if drawer else (46, 62, 78)
            pygame.draw.rect(surface, bg, plate, border_radius=10)
            edge = C.ACCENT if drawer else (90, 100, 110)
            pygame.draw.rect(surface, edge, plate, width=2 if drawer else 1,
                             border_radius=10)
            self._draw_shield_badge(surface, (plate.x + 28, plate.centery),
                                    p.shield.rank, glow_t=self.glow.get(seat, 0.0))
            surface.blit(self.tiny.render(p.name, True, C.TEXT_LIGHT),
                         (plate.x + 54, plate.y + 6))
            surface.blit(self.tiny.render(f"{p.pv} PV", True, GREEN),
                         (plate.x + 54, plate.y + 26))
            if p.charges:
                ch = self.tiny.render(f"Ch {len(p.charges)}", True, GOLD)
                surface.blit(ch, ch.get_rect(topright=(plate.right - 10,
                                                       plate.y + 26)))

    def _draw_human(self, surface):
        p = self.players[0]
        cx = self.cx + self._shake_offset(0)
        valid = self._shield_targets() if self.phase == "target_shield" else []
        if 0 in valid:
            pygame.draw.rect(surface, GOLD, self._pod_hitbox(0), width=3,
                             border_radius=12)
        if not p.alive:
            s = self.font.render("Vous êtes éliminé", True, RED)
            surface.blit(s, s.get_rect(center=(self.cx, C.SCREEN_H - 120)))
            return
        pv_top = C.SCREEN_H - 96
        self._draw_pv_row(surface, p.pv_cards, cx, pv_top, self.mid)
        self._draw_shield(surface, p.shield, (cx, pv_top - 40), self.mid,
                          glow_t=self.glow.get(0, 0.0))
        # écusson bouclier (logo + valeur) à gauche de la carte-bouclier
        self._draw_shield_badge(surface, (cx - 96, pv_top - 40), p.shield.rank,
                                glow_t=self.glow.get(0, 0.0), big=True)
        if not (self.cur == 0 and self.stage):
            for k in range(len(p.charges)):
                surface.blit(pygame.transform.rotate(self.mid.back, 90),
                             (cx + 120 + k * 8, pv_top - 40 - self.mid.w // 2))
        drawer = (self.cur == 0 and self.phase != "over")
        plate = pygame.Rect(0, 0, 210, 40)
        plate.center = (150, C.SCREEN_H - 28)
        bg = (70, 96, 120) if drawer else (46, 62, 78)
        pygame.draw.rect(surface, bg, plate, border_radius=10)
        pygame.draw.rect(surface, C.ACCENT if drawer else (90, 100, 110), plate,
                         width=2 if drawer else 1, border_radius=10)
        lab = f"Vous · {p.pv} PV"
        if p.charges:
            lab += f" · Ch {len(p.charges)}"
        surface.blit(self.tiny.render(lab, True, C.TEXT_LIGHT),
                     (plate.x + 12, plate.centery - 8))

    def _draw_held(self, surface):
        """Carte piochée tenue par le joueur actif pendant qu'il choisit."""
        if self.phase not in ("choose", "target_attack", "target_shield", "ai_think"):
            return
        if self.drawn is None:
            return
        pos = self._held_pos(self.cur)
        show_face = self.peek and self.players[self.cur].human
        img = self.mid.face(self.drawn) if show_face else self.mid.back
        surface.blit(img, pos)
        r = pygame.Rect(pos[0], pos[1], self.mid.w, self.mid.h)
        pygame.draw.rect(surface, C.ACCENT, r.inflate(6, 6), width=2,
                         border_radius=10)

    def _draw_stage(self, surface):
        if not self.stage:
            return
        cw, ch = self.mid.w, self.mid.h
        for c in self.stage:
            x, y = c["x"], c["y"]
            if not c["rev"]:
                surface.blit(self.mid.back, (x, y))
                continue
            fl = c["flip"]
            if fl < 0.5:
                base, s = self.mid.back, 1 - 2 * fl
            else:
                base, s = self.mid.face(c["card"]), 2 * fl - 1
            w = max(2, int(cw * s))
            img = pygame.transform.smoothscale(base, (w, ch))
            surface.blit(img, (int(x + (cw - w) / 2), int(y)))
        if self.force_show is not None:
            f = self.dmg_font.render(f"Force : {self.force_show}", True, GOLD)
            bottom = self.stage[0]["y"] + ch + 6
            surface.blit(f, f.get_rect(center=(self.reveal_c[0], bottom + 14)))

    def _draw_banner(self, surface):
        if not self.banner:
            return
        text, color, seat = self.banner
        pos = self._banner_pos(seat)
        surf = self.banner_font.render(text, True, color)
        box = surf.get_rect(center=pos).inflate(26, 14)
        chip = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(chip, (14, 20, 26, 210), chip.get_rect(),
                         border_radius=12)
        pygame.draw.rect(chip, color, chip.get_rect(), width=2, border_radius=12)
        surface.blit(chip, box.topleft)
        surface.blit(surf, surf.get_rect(center=box.center))

    def _draw_floats(self, surface):
        for f in self.floats:
            k = f.t / f.dur
            y = f.y - int(46 * ui.ease_out_cubic(min(1, k)))
            alpha = 255 if k < 0.7 else int(255 * (1 - (k - 0.7) / 0.3))
            font = self.dmg_font if f.big else self.small
            surf = font.render(f.text, True, f.color)
            surf.set_alpha(max(0, alpha))
            surface.blit(surf, surf.get_rect(center=(f.x, y)))

    def _draw_over(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 185))
        surface.blit(veil, (0, 0))
        cx = self.cx
        if self.winner is None:
            txt, col = "Personne ne survit !", C.ACCENT
        elif self.winner == 0:
            txt, col = "Victoire ! Vous êtes le dernier debout", GOLD
        else:
            txt, col = f"{self.players[self.winner].name} remporte la partie", C.ACCENT
        t = self.big.render(txt, True, col)
        surface.blit(t, t.get_rect(center=(cx, 220)))
        for b in self.over_buttons:
            b.draw(surface)
