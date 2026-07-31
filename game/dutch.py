"""Le Dutch — variante « maison » (2 à 6 joueurs, humain = siège 0, IA autonomes).

But : avoir le **plus faible total** de points quand on annonce « Dutch ». Seul le
joueur qui annonce peut gagner ou perdre.

Valeur des cartes (spécifique au Dutch) :
- As = 1 ; 2 à 10 = leur valeur ; Valet = 11 ; Dame = 12 ;
- **Roi noir (♠/♣) = 0** (la meilleure carte) ; **Roi rouge (♥/♦) = 15** (la pire).

Chaque joueur a **4 cartes face cachée** ; au début il en **regarde 2**. Une
**pioche** et une **défausse** sont au centre.

À son tour, un joueur **pioche** puis, soit **remplace** une de ses cartes par la
piochée, soit **défausse** la piochée pour utiliser son **pouvoir**. Seules deux
cartes ont un pouvoir (toutes les autres, sans exception, n'en ont aucun) :
- **Valet** : échanger deux cartes face cachée (n'importe lesquelles) ;
- **Dame** : regarder n'importe quelle carte (soi ou adversaire).

Remplacer une de ses cartes par une carte à pouvoir **n'active rien** ; en
revanche, si la carte **remplacée** (celle qui part à la défausse) est un Valet ou
une Dame, son pouvoir s'active pour le joueur qui remplace.

**Défausse instantanée** (permanente) : dès qu'une carte est posée sur la défausse,
tout joueur possédant une carte de **même valeur** (qu'il connaît) peut la défausser
immédiatement, même hors de son tour — la rapidité départage.

Annonce **« Dutch »** : à son tour, un joueur peut annoncer ; la manche continue
jusqu'à ce que tous les joueurs suivants aient joué un dernier tour, puis on révèle.

Présentation : joueurs disposés **en cercle** (ellipse), humain en bas ; pioche et
défausse **au centre**. La carte piochée vole vers le joueur actif.
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
PURPLE = (188, 150, 224)

SLAP_WINDOW = 2.0          # durée par défaut de la fenêtre de défausse instantanée
SLAP_PRESETS = [1.0, 1.5, 2.0, 3.0, 4.0]   # durées réglables (temps de réaction)
PEEK_SHOW = 1.5            # durée d'affichage d'une carte regardée (pouvoir)

# Espérance de la valeur Dutch d'une carte inconnue (moyenne sur 52 cartes) ≈ 6.58
UNKNOWN_EV = 6.6


def dutch_value(card):
    """Valeur d'une carte selon les règles du Dutch."""
    r = card.rank
    if r == 13:  # Roi
        return 0 if card.suit in (C.SPADE, C.CLUB) else 15
    return r     # As=1, 2..10, Valet=11, Dame=12


def power_of(card):
    """Pouvoir associé à une carte défaussée (ou None).

    Seuls le **Valet** (échanger deux cartes) et la **Dame** (regarder n'importe
    quelle carte) ont un pouvoir ; toutes les autres cartes, sans exception, n'en
    ont aucun.
    """
    r = card.rank
    if r == 11:      # Valet
        return "swap"
    if r == 12:      # Dame
        return "look_any"
    return None


POWER_LABEL = {
    "look_self": "Regarder une de vos cartes",
    "look_opp": "Regarder une carte adverse",
    "look_any": "Regarder n'importe quelle carte",
    "swap": "Échanger deux cartes",
}


class DPlayer:
    def __init__(self, idx, name, human):
        self.idx = idx
        self.name = name
        self.human = human
        self.cards = []          # cartes face cachée (objets Card)
        self.knows = set()       # cartes (objets) dont CE joueur connaît la valeur


class Fly:
    """Carte en vol (dos ou face)."""
    def __init__(self, card, start, target, dur=0.42, face_down=True):
        self.card = card
        self.start = start
        self.target = target
        self.dur = dur
        self.t = 0.0
        self.face_down = face_down


class FloatText:
    def __init__(self, text, pos, color, dur=1.4, big=True):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.t = 0.0
        self.dur = dur
        self.big = big


class DutchScene(Scene):
    MAX_STEPS = 40000

    def __init__(self, app):
        super().__init__(app)
        self.renderer = CardRenderer(80, 114)     # pioche / défausse
        self.hand = CardRenderer(72, 102)         # cartes de l'humain + en vol
        self.mini = CardRenderer(46, 64)          # cartes des adversaires
        self.title_font = pygame.font.SysFont(C.FONT_UI, 26, bold=True)
        self.font = pygame.font.SysFont(C.FONT_UI, 22, bold=True)
        self.small = pygame.font.SysFont(C.FONT_UI, 18)
        self.tiny = pygame.font.SysFont(C.FONT_UI, 15, bold=True)
        self.dfont = pygame.font.SysFont(C.FONT_UI, 14)
        self.big = pygame.font.SysFont(C.FONT_UI, 52, bold=True)
        self.banner_font = pygame.font.SysFont(C.FONT_UI, 20, bold=True)
        self.num_font = pygame.font.SysFont(C.FONT_UI, 44, bold=True)
        self.badge_font = pygame.font.SysFont(C.FONT_UI, 20, bold=True)

        self.cx = C.SCREEN_W // 2
        # cercle des joueurs, humain en bas
        self.EC = (self.cx, 356)
        self.RX, self.RY = 548, 232
        self.HUMAN_Y = C.SCREEN_H - 196
        # pioche / défausse au centre
        self.PILE = (self.cx - 128, 300)
        self.DISCARD = (self.cx + 48, 300)

        self.N = 4
        # options (réglées sur l'écran de config, conservées entre les parties)
        self.opt_show_known = False   # afficher face visible les cartes connues
        self.opt_slap_highlight = True  # surligner QUELLE carte connue défausser
        self.opt_free_slap = False    # tenter avec n'importe quelle carte (pénalité)
        self.slap_window = SLAP_WINDOW  # durée du décompte (temps de réaction bots)
        self.difficulty = "perso"     # "facile" / "difficile" / "perso" (menu options)
        self.phase = "setup"
        self.deck = []
        self.discard = []
        self.players = []
        self.cur = 0
        self.direction = 1
        self.drawn = None            # carte piochée en main de décision
        self.from_discard = False    # la carte en main vient de la défausse
        self.think_t = 0.0
        self.hold_t = 0.0
        self.flies = []
        self._after = None

        # défausse instantanée
        self.slap_value = None
        self.slap_t = 0.0
        self.slap_queue = []         # [(temps, seat, card)] réactions IA
        self.slap_cont = None
        self.slap_active = False     # une fenêtre de défausse est ouverte
        self.slap_bg = False         # fenêtre en ARRIÈRE-PLAN (tour humain en cours)
        self.slap_flies = []         # animations de slap (indép. de self.flies)
        self.slapped_any = False

        # pouvoirs
        self.power = None            # pouvoir en cours (str)
        self.power_actor = None      # siège qui utilise le pouvoir en cours
        self.power_queue = []         # sièges devant encore utiliser le pouvoir
        self.slap_power = None        # pouvoir associé à la valeur défaussée (ou None)
        self.final_cont = None        # à appeler quand tous les pouvoirs sont résolus
        self.power_sel = []          # [(seat, card)] cartes sélectionnées (pouvoir)
        self.peek_show = None        # {"card", "t", "pos"} carte regardée
        self.peek_cont = None

        # annonce Dutch
        self.dutch_caller = None
        self.dutch_turns_left = 0

        # mise en place (peek initial de l'humain)
        self.human_peeked = []       # cartes choisies par l'humain pour être vues
        self.hide_slot = None        # (seat, slot) masqué pendant une animation

        self.floats = []
        self.toast = ""
        self.result = None           # ("win"/"lose", caller, totals, counts)
        self.pod = {}
        self.step_count = 0
        self.anim_t = 0.0            # horloge d'animation (pulse du focus)

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
        # bascules d'options (repositionnées/recolorées par frame dans _draw_setup)
        self.btn_opt_known = ui.Button((0, 0, 120, 40), "Non",
                                       self._toggle_known, self.small)
        self.btn_opt_hl = ui.Button((0, 0, 120, 40), "Oui",
                                     self._toggle_hl, self.small)
        self.btn_opt_free = ui.Button((0, 0, 120, 40), "Non",
                                      self._toggle_free, self.small)
        self.btn_react = ui.Button((0, 0, 120, 40), "2,0 s",
                                   self._cycle_react, self.small,
                                   fill=(96, 120, 150), text_col=C.TEXT_LIGHT)
        # sélecteur de difficulté (segmenté)
        self.btn_diff_easy = ui.Button((0, 0, 86, 40), "Facile",
                                       self._diff_easy, self.small)
        self.btn_diff_hard = ui.Button((0, 0, 86, 40), "Difficile",
                                       self._diff_hard, self.small)
        self.btn_diff_custom = ui.Button((0, 0, 86, 40), "Perso",
                                         self._diff_custom, self.small)
        # phase « peek » initial
        self.btn_ready = ui.Button((cx - 140, 754, 280, 46), "Mémoriser et jouer",
                                   self._finish_peek, self.small)
        # phase « turn » (avant de piocher) — 3 boutons + Menu
        self.btn_draw = ui.Button((cx - 336, 754, 206, 46), "Piocher",
                                  self._human_draw, self.small)
        self.btn_take = ui.Button((cx - 118, 754, 236, 46), "Prendre la défausse",
                                  self._human_take_discard, self.small,
                                  fill=(84, 116, 160), text_col=C.TEXT_LIGHT)
        self.btn_dutch = ui.Button((cx + 130, 754, 206, 46), "Annoncer « Dutch »",
                                   self._human_dutch, self.small,
                                   fill=(150, 120, 72), text_col=C.TEXT_LIGHT)
        # phase « choose » (après avoir pioché)
        self.btn_discard = ui.Button((cx - 130, 754, 260, 46),
                                     "Défausser (pouvoir)", self._human_discard,
                                     self.small, fill=(84, 116, 160),
                                     text_col=C.TEXT_LIGHT)
        # pouvoirs : valider la sélection / annuler (renoncer au pouvoir)
        self.btn_validate = ui.Button((cx - 226, 754, 210, 46), "Valider",
                                      self._validate_power, self.small)
        self.btn_cancel = ui.Button((cx + 16, 754, 210, 46), "Annuler",
                                    self._cancel_power, self.small,
                                    fill=(150, 92, 92), text_col=C.TEXT_LIGHT)
        self.over_buttons = [
            ui.Button((cx - 230, 388, 210, 52), "Rejouer", self.new_game,
                      self.small),
            ui.Button((cx + 20, 388, 210, 52), "Menu", self.app.show_menu,
                      self.small, fill=(150, 92, 92), text_col=C.TEXT_LIGHT),
        ]

    def _dec(self):
        self.N = max(2, self.N - 1)

    def _inc(self):
        self.N = min(6, self.N + 1)

    def _toggle_known(self):
        self.opt_show_known = not self.opt_show_known

    def _toggle_hl(self):
        self.opt_slap_highlight = not self.opt_slap_highlight

    def _toggle_free(self):
        self.opt_free_slap = not self.opt_free_slap

    def _cycle_react(self):
        try:
            i = SLAP_PRESETS.index(self.slap_window)
        except ValueError:
            i = SLAP_PRESETS.index(SLAP_WINDOW)
        self.slap_window = SLAP_PRESETS[(i + 1) % len(SLAP_PRESETS)]

    def _bot_react_delay(self):
        """Délai avant qu'un bot slappe, proportionnel à la fenêtre courante."""
        return random.uniform(0.2, 0.75) * self.slap_window

    def _diff_easy(self):
        # facile : toutes les aides + réaction la plus longue
        self.difficulty = "facile"
        self.opt_show_known = True
        self.opt_slap_highlight = True
        self.opt_free_slap = True
        self.slap_window = SLAP_PRESETS[-1]

    def _diff_hard(self):
        # difficile : aucune aide + réaction la plus courte
        self.difficulty = "difficile"
        self.opt_show_known = False
        self.opt_slap_highlight = False
        self.opt_free_slap = False
        self.slap_window = SLAP_PRESETS[0]

    def _diff_custom(self):
        # perso : on garde les réglages actuels et on affiche le menu d'options
        self.difficulty = "perso"

    def _cur_buttons(self):
        if self.phase == "setup":
            b = [self.btn_minus, self.btn_plus, self.btn_diff_easy,
                 self.btn_diff_hard, self.btn_diff_custom]
            if self.difficulty == "perso":
                b += [self.btn_opt_known, self.btn_opt_hl, self.btn_opt_free,
                      self.btn_react]
            b += [self.btn_start, self.btn_menu]
            return b
        if self.phase == "over":
            return self.over_buttons + [self.btn_menu]
        if self.phase == "peek":
            b = [self.btn_menu]
            self.btn_ready.enabled = (len(self.human_peeked) == 2)
            b.append(self.btn_ready)
            return b
        if self.phase == "turn":
            self.btn_dutch.enabled = (self.dutch_caller is None)
            self.btn_take.enabled = bool(self.discard) and \
                len(self.players[self.cur].cards) >= 1
            return [self.btn_draw, self.btn_take, self.btn_dutch, self.btn_menu]
        if self.phase == "choose":
            # une carte prise dans la défausse doit être échangée (pas re-défaussée)
            if self.from_discard:
                return [self.btn_menu]
            # « (pouvoir) » seulement si la carte piochée en a un
            self.btn_discard.label = ("Défausser (pouvoir)"
                                      if power_of(self.drawn) else "Défausser")
            return [self.btn_discard, self.btn_menu]
        if self.phase in ("p_look_self", "p_look_opp", "p_look_any", "p_swap"):
            self.btn_validate.enabled = (len(self.power_sel) == self._power_need())
            return [self.btn_validate, self.btn_cancel, self.btn_menu]
        return [self.btn_menu]

    # ------------------------------------------------------------------
    # Paquet
    # ------------------------------------------------------------------
    def _fresh_deck(self):
        deck = [Card(s, r) for s in C.SUITS for r in range(1, 14)]
        random.shuffle(deck)
        return deck

    def _draw_pile_card(self):
        if not self.deck:
            # recomposer la pioche depuis la défausse (on garde la carte du dessus)
            if len(self.discard) > 1:
                top = self.discard.pop()
                self.deck = self.discard
                self.discard = [top]
                random.shuffle(self.deck)
        if not self.deck:
            self.deck = self._fresh_deck()
        return self.deck.pop()

    def new_game(self):
        self.deck = self._fresh_deck()
        self.discard = []
        self.players = [DPlayer(i, self._name(i), human=(i == 0))
                        for i in range(self.N)]
        for p in self.players:
            p.cards = [self._draw_pile_card() for _ in range(4)]
            p.knows = set()
        # les IA regardent 2 de leurs 4 cartes ; l'humain choisit lors du peek
        for p in self.players[1:]:
            for c in random.sample(p.cards, 2):
                p.knows.add(c)
        # première carte de la défausse
        self.discard.append(self._draw_pile_card())
        self.drawn = None
        self.flies = []
        self._after = None
        self.slap_value = None
        self.slap_queue = []
        self.slap_cont = None
        self.slap_active = False
        self.slap_bg = False
        self.slap_flies = []
        self.slap_power = None
        self.power = None
        self.power_actor = None
        self.power_queue = []
        self.final_cont = None
        self.power_sel = []
        self.peek_show = None
        self.dutch_caller = None
        self.dutch_turns_left = 0
        self.human_peeked = []
        self.hide_slot = None
        self.floats = []
        self.toast = ""
        self.result = None
        self.step_count = 0
        self.direction = random.choice([1, -1])
        self.first_seat = random.randrange(self.N)
        self._layout_seats()
        self.phase = "peek"
        self.toast = ("Cliquez 2 de vos cartes pour les regarder (définitif), "
                      "puis mémorisez-les.")

    def _name(self, i):
        return NAMES[i] if i < len(NAMES) else f"Joueur {i}"

    def _layout_seats(self):
        self.pod = {0: (self.cx, self.HUMAN_Y)}
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
        px, py = self.pod[seat]
        dx, dy = self.EC[0] - px, self.EC[1] - py
        L = math.hypot(dx, dy) or 1.0
        return (px + dx / L * d, py + dy / L * d)

    # ------------------------------------------------------------------
    # Mise en place — peek initial de l'humain
    # ------------------------------------------------------------------
    def _finish_peek(self):
        if len(self.human_peeked) != 2:
            return
        # l'humain connaît ces 2 cartes (mémoire) — mais rien ne reste affiché
        # face visible une fois la partie lancée (jeu de mémoire total)
        self.players[0].knows = set(self.human_peeked)
        self.human_peeked = []
        self._start_turn(self.first_seat)

    # ------------------------------------------------------------------
    # Tours
    # ------------------------------------------------------------------
    def _next_seat(self, frm):
        return (frm + self.direction) % self.N

    def _opponents(self, seat):
        return [i for i in range(self.N) if i != seat]

    def _start_turn(self, seat):
        # la partie se termine dès que le tour revient à l'annonceur de « Dutch »
        # (tous les autres — et lui — ont joué un tour complet entre-temps).
        if self.dutch_caller is not None and seat == self.dutch_caller:
            self._do_reveal()
            return
        self.cur = seat
        self.drawn = None
        self.from_discard = False
        self.hide_slot = None
        self.power = None
        self.power_actor = None
        self.power_queue = []
        self.final_cont = None
        self.power_sel = []
        p = self.players[seat]
        if p.human:
            self.phase = "turn"
            self.toast = ("À vous : piochez, prenez la défausse, ou annoncez "
                          "« Dutch ».")
        else:
            self.phase = "ai_turn"
            self.think_t = 0.55

    def _finish_turn(self):
        self.drawn = None
        self.power = None
        self.power_sel = []
        self._start_turn(self._next_seat(self.cur))

    # ---- piocher ----
    def _human_draw(self):
        if self.phase == "turn":
            self._begin_draw()

    def _begin_draw(self):
        self.from_discard = False
        self.drawn = self._draw_pile_card()
        seat = self.cur
        self.flies = [Fly(self.drawn, (self.PILE[0], self.PILE[1]),
                          self._held_pos(seat), face_down=True)]
        self._after = self._after_draw
        self.phase = "anim"

    def _human_take_discard(self):
        if self.phase == "turn" and self.discard \
                and len(self.players[self.cur].cards) >= 1:
            self._begin_take_discard()

    def _begin_take_discard(self):
        """Prendre la carte du dessus de la défausse : elle devra être échangée
        contre une de ses cartes (pas de pouvoir, pas de re-défausse)."""
        self.from_discard = True
        self.drawn = self.discard.pop()
        seat = self.cur
        self.flies = [Fly(self.drawn, (self.DISCARD[0], self.DISCARD[1]),
                          self._held_pos(seat), face_down=False)]
        self._after = self._after_draw
        self.phase = "anim"

    def _after_draw(self):
        if self.players[self.cur].human:
            self.phase = "choose"
            if self.from_discard:
                self.toast = ("Carte prise dans la défausse : cliquez une de vos "
                              "cartes pour l'échanger.")
            else:
                pw = power_of(self.drawn)
                hint = (f" — pouvoir : {POWER_LABEL[pw]}" if pw
                        else " (aucun pouvoir)")
                self.toast = ("Cliquez une carte à remplacer, ou la défausse pour "
                              "vous défausser" + hint + ".")
        else:
            self.phase = "ai_think"
            self.think_t = 0.6

    # ---- annonce Dutch ----
    def _human_dutch(self):
        if self.phase == "turn" and self.dutch_caller is None:
            self._announce_dutch(self.cur)
            self.toast = "« Dutch » annoncé — jouez votre tour normalement."

    def _announce_dutch(self, seat):
        """Annonce « Dutch ». N'interrompt PAS le tour : le joueur termine son
        tour normalement (piocher/défausser) et peut continuer à se défausser
        instantanément comme d'habitude. La partie se termine simplement lorsque
        le tour **revient** à l'annonceur (`_start_turn`)."""
        self.dutch_caller = seat
        self._float(seat, "DUTCH !", GOLD)
        self.toast = (f"{self.players[seat].name} annonce « Dutch » ! "
                      "La partie se terminera à son prochain tour.")

    # ------------------------------------------------------------------
    # Remplacer / défausser
    # ------------------------------------------------------------------
    def _human_replace(self, slot):
        if self.phase != "choose" or self.drawn is None:
            return
        self._do_replace(self.cur, slot)

    def _do_replace(self, seat, slot):
        """Anime le remplacement : la carte piochée vole vers l'emplacement, et
        l'ancienne vole vers la défausse. Le modèle est muté à l'atterrissage
        (`_finish_replace`) pour éviter tout double affichage. La carte piochée
        reste dans `self.drawn` (comptée) pendant le vol."""
        p = self.players[seat]
        old = p.cards[slot]
        new = self.drawn
        slot_rect = self._hand_positions(seat)[slot]
        held = self._held_pos(seat)
        self.hide_slot = (seat, slot)     # masque l'emplacement pendant le vol
        self.toast = f"{p.name} remplace une carte."
        self.flies = [
            # l'humain voit sa carte entrer (face visible en vol), puis mémoire
            Fly(new, held, slot_rect.topleft, face_down=(seat != 0), dur=0.42),
            Fly(old, slot_rect.topleft, (self.DISCARD[0], self.DISCARD[1]),
                face_down=False, dur=0.42),
        ]
        self._after = (lambda s=seat, k=slot, o=old, n=new:
                       self._finish_replace(s, k, o, n))
        self.phase = "anim"

    def _finish_replace(self, seat, slot, old, new):
        p = self.players[seat]
        self.drawn = None
        self.hide_slot = None
        # robustesse : la main a pu changer pendant l'animation (slot périmé) ;
        # on repère l'ancienne carte par identité, sinon on retombe sur le slot borné
        if 0 <= slot < len(p.cards) and p.cards[slot] is old:
            p.cards[slot] = new
        elif old in p.cards:
            p.cards[p.cards.index(old)] = new
        else:
            p.cards.append(new)       # l'ancienne a disparu (slappée) → on ajoute
        p.knows.discard(old)
        p.knows.add(new)          # on connaît la carte qu'on vient de poser
        self.discard.append(old)
        # défausse instantanée sur l'ancienne carte ; si celle-ci a un pouvoir
        # (Valet/Dame), le joueur qui remplace l'active (elle part à la défausse),
        # puis fin du tour
        self._open_slap(dutch_value(old), seat, self._finish_turn,
                        source_card=old, discarder_power=True)

    def _human_discard(self):
        if self.phase != "choose" or self.drawn is None or self.from_discard:
            return
        self._do_discard(self.cur)

    def _do_discard(self, seat):
        """Anime la défausse : la carte piochée vole (face visible) vers la
        défausse ; le modèle est muté à l'atterrissage (`_finish_discard`)."""
        card = self.drawn
        held = self._held_pos(seat)
        p = self.players[seat]
        self.toast = f"{p.name} défausse {card!r}."
        self.flies = [Fly(card, held, (self.DISCARD[0], self.DISCARD[1]),
                          face_down=False, dur=0.42)]
        self._after = lambda s=seat, c=card: self._finish_discard(s, c)
        self.phase = "anim"

    def _finish_discard(self, seat, card):
        self.drawn = None
        self.discard.append(card)
        # défausse instantanée puis pouvoir(s) — celui qui défausse la carte
        # pour son pouvoir l'utilise, ainsi que ceux qui la défaussent en instant
        self._open_slap(dutch_value(card), seat, self._finish_turn,
                        source_card=card, discarder_power=True)

    # ------------------------------------------------------------------
    # Défausse instantanée
    # ------------------------------------------------------------------
    def _known_matching(self, seat, value):
        """Cartes de `seat` connues de lui et valant `value`."""
        p = self.players[seat]
        return [c for c in p.cards if c in p.knows and dutch_value(c) == value]

    def _open_slap(self, value, source, cont, source_card=None,
                   discarder_power=False):
        # si une fenêtre d'ARRIÈRE-PLAN est encore ouverte (l'humain a rejoué très
        # vite), on la termine d'abord pour ne pas perdre les slaps IA en attente
        if self.slap_active and self.slap_bg:
            self._flush_bg_slap()
        # pouvoir associé à cette valeur (J/Q) — même valeur ⇒ même rang ⇒ même
        # pouvoir pour toutes les cartes défaussées dans la fenêtre
        self.slap_power = power_of(source_card) if source_card else None
        self.power_queue = []
        if discarder_power and self.slap_power:
            self.power_queue.append(source)
        bot_slappers = [seat for seat in range(1, self.N)
                        if self._known_matching(seat, value)]
        human_slap = bool(self._known_matching(0, value))
        next_human = (self._next_seat(self.cur) == 0)
        # le DÉFAUSSEUR a-t-il un pouvoir que l'HUMAIN doit utiliser (UI) ?
        human_power = (bool(self.power_queue)
                       and self.players[self.power_queue[0]].human)
        # l'humain peut tenter une défausse (option libre → toujours ; sinon s'il
        # connaît une carte de la bonne valeur)
        human_may = self.opt_free_slap or human_slap
        want_window = bool(bot_slappers) or human_may
        if not want_window:
            # rien à slapper → on résout un éventuel pouvoir (humain OU IA) du
            # défausseur via le circuit normal (phases pour l'humain), puis on suit
            self.slap_active = False
            self._begin_power_resolution(cont)
            return
        self.slap_value = value
        self.slap_t = self.slap_window
        self.slapped_any = False
        self.slap_active = True
        # réactions des IA qui connaissent une carte de même valeur
        self.slap_queue = [[self._bot_react_delay(), seat] for seat in bot_slappers]
        # BLOQUANT si le prochain est une IA ET que (l'humain peut se défausser — il
        # a droit au décompte — OU le défausseur humain doit utiliser son pouvoir).
        # Sinon ARRIÈRE-PLAN : le jeu continue tout de suite (aucune attente).
        if (not next_human) and (human_slap or human_power):
            self.slap_bg = False
            self.slap_cont = cont
            self.phase = "slap"
            self.toast = ("Défausse instantanée : cliquez une carte de même valeur "
                          "(erreur = pénalité).")
        else:
            # ARRIÈRE-PLAN : on enchaîne le tour. Un pouvoir du DÉFAUSSEUR ne peut
            # être qu'une IA ici (un pouvoir humain force le mode bloquant ci-dessus)
            # → on le résout maintenant, car `cont()`→`_start_turn` réinitialise
            # `power_queue`.
            if self.power_queue:
                self._apply_bot_powers(self.power_queue, self.slap_power)
                self.power_queue = []
            self.slap_bg = True
            self.slap_cont = None
            cont()                                  # _finish_turn → tour suivant

    def _do_slap(self, seat, card):
        p = self.players[seat]
        if card not in p.cards:
            return
        idx = p.cards.index(card)
        pos = self._hand_positions(seat)[idx]
        p.cards.remove(card)
        p.knows.discard(card)
        self.discard.append(card)
        self.slapped_any = True
        # défausser une carte à pouvoir en instantané → ce joueur utilisera aussi
        # son pouvoir (chacun son tour, après la fenêtre)
        if self.slap_power:
            self.power_queue.append(seat)
        fly = Fly(card, pos, (self.DISCARD[0], self.DISCARD[1]),
                  face_down=False, dur=0.3)
        # en arrière-plan, les slaps IA ont leur propre liste d'animations pour ne
        # pas se coupler aux animations du tour humain en cours
        (self.slap_flies if self.slap_bg else self.flies).append(fly)
        self._float(seat, "Défausse !", GREEN, big=False)
        if not self.slap_bg:                         # ne pas écraser le toast du tour
            self.toast = f"{p.name} défausse instantanément {card!r} !"

    def _slap_click_allowed(self):
        """L'humain peut-il tenter une défausse instantanée en cliquant une carte ?
        Toujours pendant une fenêtre bloquante (phase 'slap'). En arrière-plan (son
        tour ou celui d'une IA), s'il connaît une carte de la bonne valeur, ou —
        avec « défausse libre » — dans tous les cas. Uniquement dans une phase où le
        clic sur une carte n'a pas déjà un autre sens."""
        if not self.slap_active:
            return False
        if self.phase == "slap":
            return True
        if self.phase in ("turn", "ai_turn", "ai_think", "anim", "hold"):
            return (self.opt_free_slap
                    or (self.slap_value is not None
                        and bool(self._known_matching(0, self.slap_value))))
        return False

    def _human_slap_click(self, pos):
        # on peut tenter N'IMPORTE QUELLE carte (la surbrillance n'est qu'une
        # indication : cartes connues de même valeur). Si la carte cliquée est de
        # la bonne valeur, elle part ; sinon c'est raté → pénalité (on pioche).
        # Renvoie True si le clic a touché une de ses cartes (donc consommé).
        if self.slap_value is None or self.flies or self.slap_flies:
            return False
        for idx, r in enumerate(self._hand_positions(0)):
            if r.collidepoint(pos):
                card = self.players[0].cards[idx]
                if dutch_value(card) == self.slap_value:
                    self._do_slap(0, card)      # bonne valeur → défaussée
                else:
                    self._slap_penalty(0)       # mauvaise valeur → pénalité
                return True
        return False

    def _slap_penalty(self, seat):
        """Défausse instantanée ratée : le joueur pioche une carte de pénalité
        (carte inconnue ajoutée à sa main, animée depuis la pioche)."""
        p = self.players[seat]
        # s'il ne reste réellement aucune carte à piocher (pioche vide et défausse
        # non recomposable), pas de pénalité matérielle — on préserve les 52 cartes
        if not self.deck and len(self.discard) <= 1:
            self._float(seat, "Raté !", RED, big=False)
            self.toast = f"{p.name} se trompe de carte."
            return
        pen = self._draw_pile_card()
        p.cards.append(pen)                     # carte inconnue (pas dans `knows`)
        slot = len(p.cards) - 1
        target = self._hand_positions(seat)[slot].topleft
        self.hide_slot = (seat, slot)
        self._after = lambda: setattr(self, "hide_slot", None)
        self.flies.append(Fly(pen, (self.PILE[0], self.PILE[1]), target,
                              face_down=True, dur=0.35))
        self._float(seat, "Raté ! +1 carte", RED, big=False)
        self.toast = f"{p.name} se trompe de carte — pioche une pénalité."

    def _tick_slap(self, dt):
        """Fait avancer la fenêtre de défausse : timer + réactions IA. Utilisé en
        mode bloquant (phase 'slap') comme en arrière-plan (tour humain)."""
        self.slap_t -= dt
        for entry in self.slap_queue:
            entry[0] -= dt
            if entry[0] <= 0 and entry[1] is not None:
                seat = entry[1]
                entry[1] = None
                card = self._ai_slap_ready(seat)
                if card is not None:
                    self._do_slap(seat, card)
        if self.slap_t <= 0:
            if self.slap_bg:
                if not self.slap_flies:
                    self._finish_bg_slap()
            elif not self.flies:
                self._close_slap()

    def _close_slap(self):
        # fenêtre BLOQUANTE terminée → résolution des pouvoirs puis suite du jeu
        self.slap_active = False
        cont = self.slap_cont
        self.slap_value = None
        self.slap_cont = None
        self.slap_queue = []
        self._begin_power_resolution(cont)

    def _finish_bg_slap(self):
        """Ferme une fenêtre d'ARRIÈRE-PLAN : le tour humain continue ; les
        pouvoirs éventuels (tous des IA) sont résolus instantanément, sans phase."""
        self.slap_active = False
        self.slap_bg = False
        self.slap_value = None
        self.slap_queue = []
        self._resolve_bg_powers()

    def _flush_bg_slap(self):
        """Termine sur-le-champ une fenêtre d'arrière-plan encore ouverte (avant
        d'en ouvrir une nouvelle) : les IA en attente slappent d'un coup."""
        for entry in self.slap_queue:
            if entry[1] is not None:
                seat = entry[1]
                entry[1] = None
                card = self._ai_slap_ready(seat)
                if card is not None:
                    self._do_slap(seat, card)
        self._finish_bg_slap()

    def _resolve_bg_powers(self):
        """Applique instantanément les pouvoirs des IA ayant slappé une carte à
        pouvoir en arrière-plan (aucune UI, pas de changement de phase)."""
        self._apply_bot_powers(self.power_queue, self.slap_power)
        self.power_queue = []
        self.slap_power = None

    def _apply_bot_powers(self, seats, pw):
        """Applique le pouvoir `pw` à chaque siège IA de `seats` (ordre du jeu)."""
        for seat in self._order_power_seats(seats):
            if pw and not self.players[seat].human:
                self._apply_bot_power(seat, pw)

    def _apply_bot_power(self, seat, pw):
        p = self.players[seat]
        if pw in ("look_self", "look_any"):
            unk = [c for c in p.cards if c not in p.knows]
            if unk:
                p.knows.add(unk[0])
            elif pw == "look_any":
                t = self._ai_unknown_opp_card(seat)
                if t:
                    p.knows.add(t)
        elif pw == "look_opp":
            t = self._ai_unknown_opp_card(seat)
            if t:
                p.knows.add(t)
        elif pw == "swap":
            self._bot_swap_instant(seat)

    def _bot_swap_instant(self, seat):
        me = self.players[seat]
        mine = [(dutch_value(c), c) for c in me.cards if c in me.knows]
        if not mine:
            return
        hv, hc = max(mine, key=lambda x: x[0])
        if hv <= 6:
            return
        best = None
        for o in self._opponents(seat):
            for c in self.players[o].cards:
                val = dutch_value(c) if c in me.knows else UNKNOWN_EV
                if best is None or val < best[0]:
                    best = (val, o, c)
        if best and best[0] < hv:
            _, o, oc = best
            po = self.players[o]
            ia, ib = me.cards.index(hc), po.cards.index(oc)
            me.cards[ia], po.cards[ib] = oc, hc

    # ------------------------------------------------------------------
    # Pouvoirs — résolution en file (chacun son tour)
    # ------------------------------------------------------------------
    def _order_power_seats(self, seats):
        """Ordonne les sièges dans l'ordre du jeu à partir du joueur actif
        (l'auteur du tour d'abord), sans doublon."""
        seats = list(dict.fromkeys(seats))
        return sorted(seats, key=lambda s: (s - self.cur) * self.direction % self.N)

    def _begin_power_resolution(self, cont):
        self.final_cont = cont or self._finish_turn
        self.power_queue = self._order_power_seats(self.power_queue)
        self._process_next_power()

    def _process_next_power(self):
        if not self.power_queue:
            self.power = None
            self.power_actor = None
            c = self.final_cont
            self.final_cont = None
            (c or self._finish_turn)()
            return
        seat = self.power_queue.pop(0)
        self._enter_power(seat, self.slap_power)

    def _enter_power(self, seat, pw):
        self.power = pw
        self.power_actor = seat
        self.power_sel = []
        if pw is None:
            self._process_next_power()
            return
        actor = self.players[seat]
        phase = {"look_self": "p_look_self", "look_opp": "p_look_opp",
                 "look_any": "p_look_any", "swap": "p_swap"}[pw]
        if actor.human:
            self.phase = phase
            self.toast = self._power_prompt()
        else:
            self.toast = f"{actor.name} utilise son pouvoir ({POWER_LABEL[pw]})…"
            self.think_t = 0.5
            self.phase = "ai_power"

    def _power_need(self):
        """Nombre de cartes à sélectionner pour valider le pouvoir courant."""
        return 2 if self.phase == "p_swap" else 1

    def _power_prompt(self):
        """Texte d'aide selon le pouvoir et l'état de la sélection."""
        if self.phase == "p_swap":
            n = len(self.power_sel)
            if n == 0:
                return "Échange : cliquez 2 cartes à échanger."
            if n == 1:
                return "Échange : cliquez la 2ᵉ carte, puis Valider."
            return "Échange : 2 cartes choisies — Valider (croix pour retirer)."
        if self.power_sel:
            return "Valider pour regarder (croix pour retirer, ou autre carte)."
        return "Regarder : cliquez la carte à regarder, puis Valider."

    def _cancel_power(self):
        """« Annuler » : renoncer au pouvoir en cours (comme passer)."""
        if self.phase in ("p_look_self", "p_look_opp", "p_look_any", "p_swap"):
            self.power_sel = []
            self._process_next_power()

    def _validate_power(self):
        """« Valider » : applique le pouvoir avec les cartes sélectionnées."""
        if self.phase not in ("p_look_self", "p_look_opp", "p_look_any", "p_swap"):
            return
        if len(self.power_sel) != self._power_need():
            return
        act = self.power_actor if self.power_actor is not None else 0
        if self.phase == "p_swap":
            (sa, ca), (sb, cb) = self.power_sel
            self.power_sel = []
            self._do_swap(sa, ca, sb, cb)
        else:
            seat, card = self.power_sel[0]
            self.power_sel = []
            self.players[act].knows.add(card)
            idx = (self.players[seat].cards.index(card)
                   if card in self.players[seat].cards else 0)
            self._show_peek(card, self._pod_card_pos(seat, idx),
                            self._process_next_power)

    def _card_at(self, pos):
        """Renvoie (seat, slot, card) de la carte sous le curseur, ou None."""
        for seat in range(self.N):
            for idx, r in enumerate(self._hand_positions(seat)):
                if r.collidepoint(pos):
                    return (seat, idx, self.players[seat].cards[idx])
        return None

    def _human_power_click(self, pos):
        """Clic sur une carte pendant un pouvoir : (dé)sélectionne la carte.
        La validation se fait ensuite par le bouton « Valider »."""
        hit = self._card_at(pos)
        if hit is None:
            return
        seat, slot, card = hit
        act = self.power_actor if self.power_actor is not None else 0
        # contraintes de cible (look_self/look_opp ne sont plus atteints, gardés
        # par sûreté)
        if self.phase == "p_look_self" and seat != act:
            return
        if self.phase == "p_look_opp" and seat == act:
            return
        key = (seat, card)
        if key in self.power_sel:
            self.power_sel.remove(key)          # re-clic = désélection
        elif self._power_need() == 1:
            self.power_sel = [key]              # regarder : une seule carte
        elif len(self.power_sel) < self._power_need():
            self.power_sel.append(key)          # échange : jusqu'à 2 cartes
        self.toast = self._power_prompt()

    def _power_x_rects(self):
        """Rects des petites croix ✕ (au-dessus de chaque carte sélectionnée)
        permettant de retirer cette carte de la sélection."""
        out = []
        for seat, card in self.power_sel:
            p = self.players[seat]
            if card in p.cards:
                idx = p.cards.index(card)
                r = self._hand_positions(seat)[idx]
                out.append((pygame.Rect(r.centerx - 13, r.top - 30, 26, 26),
                            (seat, card)))
        return out

    def _do_swap(self, sa, ca, sb, cb):
        pa, pb = self.players[sa], self.players[sb]
        ia, ib = pa.cards.index(ca), pb.cards.index(cb)
        posa = self._hand_positions(sa)[ia]
        posb = self._hand_positions(sb)[ib]
        pa.cards[ia], pb.cards[ib] = cb, ca
        # la connaissance suit l'objet carte : rien à mettre à jour ici
        self.flies = [
            Fly(ca, posa, posb, face_down=True, dur=0.4),
            Fly(cb, posb, posa, face_down=True, dur=0.4),
        ]
        self._after = self._process_next_power
        self.phase = "anim"
        self.toast = "Échange effectué."

    def _show_peek(self, card, pos, cont):
        self.peek_show = {"card": card, "t": 0.0, "pos": pos}
        self.peek_cont = cont
        self.phase = "showpeek"

    def _dismiss_peek(self):
        cont = self.peek_cont
        self.peek_show = None
        self.peek_cont = None
        if cont:
            cont()

    # ------------------------------------------------------------------
    # IA
    # ------------------------------------------------------------------
    def _est_total(self, seat):
        """Estimation du total d'un joueur du point de vue de `seat` (ce qu'il
        connaît + espérance sur ce qu'il ignore)."""
        p = self.players[seat]
        tot = 0.0
        for c in p.cards:
            tot += dutch_value(c) if c in p.knows else UNKNOWN_EV
        return tot

    def _ai_turn_start(self, seat):
        p = self.players[seat]
        est = self._est_total(seat)
        n_unknown = sum(1 for c in p.cards if c not in p.knows)
        # pression croissante : plus la partie dure, plus l'IA ose annoncer
        pressure = min(6.0, self.step_count / 900.0)
        threshold = 7.5 + pressure
        confident = (n_unknown <= 1)
        want_dutch = (self.dutch_caller is None and
                      (est <= threshold and (confident or est <= 5.0)))
        # avec 0 ou 1 carte et un petit total, on annonce
        if self.dutch_caller is None and len(p.cards) <= 1 and est <= 12:
            want_dutch = True
        if want_dutch:
            self._announce_dutch(seat)      # n'interrompt pas le tour
        # l'annonce ne remplace pas le tour : le joueur joue quand même
        if self._ai_discard_take_gain(seat) >= 3.0:
            self._begin_take_discard()      # la défausse offre une bonne carte
        else:
            self._begin_draw()

    def _ai_discard_take_gain(self, seat):
        """Gain de remplacement si l'IA prenait la carte du dessus de la défausse
        (0 si ce n'est pas intéressant)."""
        if not self.discard or len(self.players[seat].cards) < 1:
            return 0.0
        dv = dutch_value(self.discard[-1])
        if dv > 6:                          # ne prendre qu'une carte basse
            return 0.0
        p = self.players[seat]
        best = 0.0
        for c in p.cards:
            cur_val = dutch_value(c) if c in p.knows else UNKNOWN_EV
            best = max(best, cur_val - dv)
        return best

    def _ai_choose(self, seat):
        p = self.players[seat]
        dv = dutch_value(self.drawn)
        pw = power_of(self.drawn)
        # meilleur remplacement : max (valeur connue|EV) − dv, positif
        best_gain, best_slot = 0.0, None
        for i, c in enumerate(p.cards):
            cur_val = dutch_value(c) if c in p.knows else UNKNOWN_EV
            gain = cur_val - dv
            if gain > best_gain:
                best_gain, best_slot = gain, i
        # carte prise dans la défausse : on DOIT l'échanger (pas de pouvoir)
        if self.from_discard:
            if best_slot is None:
                best_slot = max(range(len(p.cards)),
                                key=lambda i: (dutch_value(p.cards[i])
                                               if p.cards[i] in p.knows
                                               else UNKNOWN_EV))
            self._do_replace(seat, best_slot)
            return
        # valeur estimée d'un pouvoir défaussé
        power_score = self._ai_power_score(seat, pw)
        if best_slot is not None and best_gain >= power_score and best_gain > 0.5:
            self._do_replace(seat, best_slot)
        elif power_score > 0.5:
            self._do_discard(seat)          # défausser pour le pouvoir
        elif best_slot is not None and best_gain > 0:
            self._do_replace(seat, best_slot)
        else:
            self._do_discard(seat)          # carte haute sans pouvoir : on la jette

    def _ai_power_score(self, seat, pw):
        p = self.players[seat]
        if pw is None:
            return 0.0
        n_unknown_self = sum(1 for c in p.cards if c not in p.knows)
        if pw == "look_self":
            return 2.0 if n_unknown_self else 0.0
        if pw == "look_opp":
            return 1.3
        if pw == "look_any":
            return 2.0 if n_unknown_self else 1.3
        if pw == "swap":
            # utile si on connaît une carte haute chez soi
            known_self = [dutch_value(c) for c in p.cards if c in p.knows]
            hi = max(known_self) if known_self else 0
            return max(0.0, hi - 6.0)
        return 0.0

    def _ai_power(self, seat):
        p = self.players[seat]
        pw = self.power
        if pw in ("look_self", "look_any"):
            unk = [c for c in p.cards if c not in p.knows]
            if not unk and pw == "look_any":
                unk = self._ai_unknown_opp_card(seat)
            if unk:
                target = unk[0] if isinstance(unk, list) else unk
                p.knows.add(target)
            self._process_next_power()
        elif pw == "look_opp":
            target = self._ai_unknown_opp_card(seat)
            if target:
                p.knows.add(target)
            self._process_next_power()
        elif pw == "swap":
            self._ai_swap(seat)
        else:
            self._process_next_power()

    def _ai_unknown_opp_card(self, seat):
        for o in self._opponents(seat):
            for c in self.players[o].cards:
                if c not in self.players[seat].knows:
                    return c
        return None

    def _ai_swap(self, seat):
        me = self.players[seat]
        # ma carte connue la plus haute
        mine = [(dutch_value(c), c) for c in me.cards if c in me.knows]
        if not mine:
            self._process_next_power()
            return
        hv, hc = max(mine, key=lambda x: x[0])
        if hv <= 6:
            self._process_next_power()
            return
        # cible : carte adverse connue basse, sinon carte adverse inconnue (EV)
        best = None      # (valeur estimée, seat, card)
        for o in self._opponents(seat):
            po = self.players[o]
            for c in po.cards:
                val = dutch_value(c) if c in me.knows else UNKNOWN_EV
                if best is None or val < best[0]:
                    best = (val, o, c)
        if best and best[0] < hv:
            _, o, oc = best
            self._do_swap(seat, hc, o, oc)
        else:
            self._process_next_power()

    def _ai_slap_ready(self, seat):
        """L'IA choisit une carte connue de même valeur à défausser (ou None)."""
        m = self._known_matching(seat, self.slap_value)
        return m[0] if m else None

    # ------------------------------------------------------------------
    # Révélation & score
    # ------------------------------------------------------------------
    def _do_reveal(self):
        totals = [sum(dutch_value(c) for c in p.cards) for p in self.players]
        counts = [len(p.cards) for p in self.players]
        caller = self.dutch_caller
        mn = min(totals)
        tied = [i for i in range(self.N) if totals[i] == mn]
        caller_wins = False
        if totals[caller] == mn:
            if len(tied) == 1:
                caller_wins = True
            else:
                others = [i for i in tied if i != caller]
                # gagne seulement si strictement moins de cartes que tous les
                # ex æquo (égalité parfaite de cartes ⇒ le donneur perd)
                caller_wins = all(counts[caller] < counts[i] for i in others)
        self.result = ("win" if caller_wins else "lose", caller, totals, counts)
        for p in self.players:
            for c in p.cards:
                c.face_up = True
        self.phase = "over"

    # ------------------------------------------------------------------
    # Effets visuels
    # ------------------------------------------------------------------
    def _float(self, seat, text, color, big=True):
        px, py = self.pod[seat]
        self.floats.append(FloatText(text, (px, py - 70), color, big=big))

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------
    def _hand_positions(self, seat):
        """Rects des cartes d'un joueur (pour dessin et clic)."""
        p = self.players[seat]
        n = len(p.cards)
        rend = self.hand if seat == 0 else self.mini
        cw, ch = rend.w, rend.h
        gap = 10 if seat == 0 else 6
        total = n * cw + (n - 1) * gap if n else 0
        px, py = self.pod[seat]
        x0 = px - total // 2
        y = py - ch // 2
        return [pygame.Rect(x0 + i * (cw + gap), y, cw, ch) for i in range(n)]

    def _pod_card_pos(self, seat, slot):
        rects = self._hand_positions(seat)
        if 0 <= slot < len(rects):
            return rects[slot].center
        return self.pod[seat]

    def _held_pos(self, seat):
        if seat == 0:
            return (self.cx + 250, self.HUMAN_Y - self.hand.h // 2)
        ix, iy = self._inward(seat, 70)
        return (int(ix - self.hand.w // 2), int(iy - self.hand.h // 2))

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
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.phase == "showpeek":
                    self._dismiss_peek()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # défausse instantanée : tenter en cliquant une de ses cartes (fenêtre
            # bloquante, ou n'importe quand avec l'option « défausse libre »)
            if self._slap_click_allowed() and self._human_slap_click(pos):
                return
            if self.phase == "turn":
                # clic sur la pioche = piocher ; clic sur la défausse = la prendre
                pr = pygame.Rect(self.PILE[0], self.PILE[1],
                                 self.renderer.w, self.renderer.h)
                dr = pygame.Rect(self.DISCARD[0], self.DISCARD[1],
                                 self.renderer.w, self.renderer.h)
                if pr.collidepoint(pos):
                    self._human_draw()
                elif dr.collidepoint(pos):
                    self._human_take_discard()
            elif self.phase == "peek":
                self._peek_click(pos)
            elif self.phase == "choose":
                # clic sur la défausse = se défausser de la carte piochée
                if not self.from_discard:
                    dr = pygame.Rect(self.DISCARD[0], self.DISCARD[1],
                                     self.renderer.w, self.renderer.h)
                    if dr.collidepoint(pos):
                        self._human_discard()
                        return
                # clic sur une de ses cartes = remplacer
                for idx, r in enumerate(self._hand_positions(0)):
                    if r.collidepoint(pos):
                        self._human_replace(idx)
                        return
            elif self.phase in ("p_look_self", "p_look_opp", "p_look_any", "p_swap"):
                # clic sur une croix ✕ = retirer cette carte de la sélection
                for rect, key in self._power_x_rects():
                    if rect.collidepoint(pos):
                        if key in self.power_sel:
                            self.power_sel.remove(key)
                            self.toast = self._power_prompt()
                        return
                self._human_power_click(pos)
            elif self.phase == "showpeek":
                self._dismiss_peek()

    def _peek_click(self, pos):
        # une carte regardée ne peut plus être « dé-regardée » : pas de bascule
        for idx, r in enumerate(self._hand_positions(0)):
            if r.collidepoint(pos):
                card = self.players[0].cards[idx]
                if card not in self.human_peeked and len(self.human_peeked) < 2:
                    self.human_peeked.append(card)
                return

    # ------------------------------------------------------------------
    # Boucle
    # ------------------------------------------------------------------
    def update(self, dt):
        mouse = pygame.mouse.get_pos()
        self.anim_t += dt
        for b in self._cur_buttons():
            b.update(dt, mouse)
        if self.phase in ("setup", "over"):
            return
        self.step_count += 1
        self._animate_fx(dt)

        # animations des slaps IA en arrière-plan (indépendantes du tour)
        if self.slap_flies:
            for f in self.slap_flies:
                f.t += dt / f.dur
            self.slap_flies = [f for f in self.slap_flies if f.t < 1]
        # fenêtre de défausse en ARRIÈRE-PLAN : tourne pendant le tour humain, mais
        # PAS pendant une animation de premier plan (`self.flies`) — un slap retire
        # une carte et invaliderait un remplacement/défausse en cours (slot périmé).
        if self.slap_active and self.slap_bg and not self.flies:
            self._tick_slap(dt)

        if self.flies:
            done = all(f.t >= 1 for f in self.flies)
            for f in self.flies:
                f.t += dt / f.dur
            if done:
                cb, self._after, self.flies = self._after, None, []
                if cb:
                    cb()
            return

        if self.phase == "showpeek":
            self.peek_show["t"] += dt
            if self.peek_show["t"] >= PEEK_SHOW:
                self._dismiss_peek()
            return

        if self.phase == "slap":                 # fenêtre BLOQUANTE (prochain = IA)
            self._tick_slap(dt)
            return

        if self.phase == "ai_turn":
            self.think_t -= dt
            if self.think_t <= 0:
                self._ai_turn_start(self.cur)
        elif self.phase == "ai_think":
            self.think_t -= dt
            if self.think_t <= 0:
                self._ai_choose(self.cur)
        elif self.phase == "ai_power":
            self.think_t -= dt
            if self.think_t <= 0:
                self._ai_power(self.power_actor)
        elif self.phase == "hold":
            self.hold_t -= dt
            if self.hold_t <= 0:
                self._finish_turn()

    def _animate_fx(self, dt):
        for f in self.floats:
            f.t += dt
        self.floats = [f for f in self.floats if f.t < f.dur]

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
        if self.phase != "over":
            self._draw_piles(surface)      # centre libéré pour l'écran de fin
        self._draw_players(surface)
        self._draw_drawn(surface)
        for f in self.flies + self.slap_flies:
            img = (self.hand.back if f.face_down else self.hand.face(f.card))
            t = ui.ease_out_cubic(min(1, f.t))
            x = ui.lerp(f.start[0], f.target[0], t)
            y = ui.lerp(f.start[1], f.target[1], t)
            surface.blit(img, (int(x), int(y)))
        self._draw_floats(surface)
        if self.phase in ("p_look_self", "p_look_opp", "p_look_any", "p_swap"):
            self._draw_power_x(surface)
        if self.phase == "showpeek":
            self._draw_peek(surface)
        for b in self._cur_buttons():
            b.draw(surface)
        if self.phase == "over":
            self._draw_over(surface)

    def _draw_setup(self, surface):
        cx = self.cx
        t = self.big.render("Le Dutch", True, C.ACCENT)
        surface.blit(t, t.get_rect(center=(cx, 120)))
        s = self.small.render("Le plus petit total gagne — mais seul celui qui "
                              "annonce « Dutch » peut gagner ou perdre",
                              True, C.TEXT_DIM)
        surface.blit(s, s.get_rect(center=(cx, 170)))
        pad = 24
        pw = 620
        perso = (self.difficulty == "perso")
        # hauteur du panneau : compacte en facile/difficile, haute en perso
        ph = (162 + 4 * 62 + 14) if perso else 182
        px, py = cx - pw // 2, 192
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 20, 26, 120), panel.get_rect(),
                         border_radius=16)
        pygame.draw.rect(panel, (255, 255, 255, 26), panel.get_rect(),
                         width=1, border_radius=16)
        surface.blit(panel, (px, py))
        hs = self.tiny.render("RÉGLAGES DE LA PARTIE", True, C.ACCENT)
        surface.blit(hs, (px + 24, py + 14))
        # -- nombre de joueurs --
        y0 = py + 44
        self.btn_minus.rect.update(px + pw - pad - 176, y0, 52, 52)
        self.btn_plus.rect.update(px + pw - pad - 52, y0, 52, 52)
        surface.blit(self.small.render("Nombre de joueurs", True, C.TEXT_LIGHT),
                     (px + pad, y0 + 2))
        surface.blit(self.dfont.render("Vous + IA (2 à 6)", True, C.TEXT_DIM),
                     (px + pad, y0 + 26))
        num = self.num_font.render(str(self.N), True, C.TEXT_LIGHT)
        surface.blit(num, num.get_rect(center=(px + pw - pad - 88, y0 + 24)))
        # -- difficulté (segmenté Facile / Difficile / Perso) --
        yd = py + 108
        surface.blit(self.small.render("Difficulté", True, C.TEXT_LIGHT),
                     (px + pad, yd + 10))
        diffs = [(self.btn_diff_easy, "facile"), (self.btn_diff_hard, "difficile"),
                 (self.btn_diff_custom, "perso")]
        bw, gap = 92, 6
        x = px + pw - pad - (bw * 3 + gap * 2)
        for btn, mode in diffs:
            sel = (self.difficulty == mode)
            btn.rect.update(x, yd, bw, 42)
            btn.fill = C.ACCENT if sel else (70, 84, 98)
            btn.fill_hover = tuple(min(255, c + 22) for c in btn.fill)
            btn.text_col = (30, 34, 40) if sel else C.TEXT_LIGHT
            x += bw + gap
        # -- options détaillées (mode perso uniquement) --
        if perso:
            rows = [
                (self.btn_opt_known, self.opt_show_known, True,
                 "Cartes connues visibles",
                 "Affiche face visible les cartes que vous connaissez"),
                (self.btn_opt_hl, self.opt_slap_highlight, True,
                 "Aide à la défausse",
                 "Surligne QUELLE carte connue défausser (le halo reste toujours là)"),
                (self.btn_opt_free, self.opt_free_slap, True,
                 "Défausse libre",
                 "Tenter avec n'importe quelle carte (une erreur coûte une carte)"),
                (self.btn_react, None, False,
                 "Temps de réaction des bots",
                 "Durée du décompte où vous pouvez défausser (le bot attend)"),
            ]
            ry = py + 162
            for btn, on, toggle, title, desc in rows:
                surface.blit(self.small.render(title, True, C.TEXT_LIGHT),
                             (px + pad, ry))
                surface.blit(self.dfont.render(desc, True, C.TEXT_DIM),
                             (px + pad, ry + 23))
                btn.rect.update(px + pw - pad - 116, ry + 2, 116, 40)
                if toggle:
                    btn.label = "Oui" if on else "Non"
                    btn.fill = (86, 150, 96) if on else (96, 108, 118)
                    btn.fill_hover = tuple(min(255, c + 22) for c in btn.fill)
                    btn.text_col = C.TEXT_LIGHT
                else:
                    btn.label = f"{self.slap_window:.1f} s".replace(".", ",")
                ry += 62
        else:
            summ = ("Toutes les aides activées, réaction lente (max)."
                    if self.difficulty == "facile"
                    else "Aucune aide, réaction éclair (min).")
            surface.blit(self.dfont.render(summ, True, C.TEXT_DIM),
                         (px + pad, yd + 52))
        self.btn_start.rect.update(cx - 130, py + ph + 16, 260, 54)

    def _draw_hud(self, surface):
        bar = pygame.Surface((C.SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 60))
        surface.blit(bar, (0, 0))
        surface.blit(self.title_font.render("Le Dutch", True, C.TEXT_LIGHT),
                     (24, 10))
        arrow = "sens >>" if self.direction == 1 else "sens <<"
        surface.blit(self.small.render(arrow, True, C.TEXT_DIM), (200, 15))
        if self.dutch_caller is not None:
            d = self.small.render(
                f"« Dutch » annoncé par {self.players[self.dutch_caller].name}",
                True, GOLD)
            surface.blit(d, d.get_rect(midright=(C.SCREEN_W - 180, 24)))
        if self.toast:
            s = self.small.render(self.toast, True, C.ACCENT)
            surface.blit(s, s.get_rect(center=(self.cx, 24)))

    def _focus_rect(self, pos):
        return pygame.Rect(pos[0], pos[1], self.renderer.w, self.renderer.h)

    def _draw_focus(self, surface, rect, hovered):
        """Halo pulsant autour d'une pile cliquable (pioche / défausse)."""
        pulse = 0.5 + 0.5 * math.sin(self.anim_t * 4.5)
        col = C.HILITE if hovered else C.ACCENT
        alpha = int((150 if hovered else 105) + 95 * pulse)
        lift = 6 if hovered else 0
        pad = 12
        glow = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2),
                              pygame.SRCALPHA)
        pygame.draw.rect(glow, (*col, alpha // 3), glow.get_rect(),
                         border_radius=16)
        pygame.draw.rect(glow, (*col, alpha), glow.get_rect(),
                         width=5 if hovered else 4, border_radius=16)
        surface.blit(glow, (rect.x - pad, rect.y - pad - lift))

    def _draw_piles(self, surface):
        r = self.renderer
        mouse = pygame.mouse.get_pos()
        human_turn = (self.cur == 0)
        pile_focus = (self.phase == "turn" and human_turn)
        # défausse cliquable : « prendre » à son tour, « défausser » après pioche
        disc_take = (self.phase == "turn" and human_turn and bool(self.discard))
        disc_drop = (self.phase == "choose" and human_turn
                     and not self.from_discard)
        disc_focus = disc_take or disc_drop
        # -- pioche --
        if pile_focus:
            self._draw_focus(surface, self._focus_rect(self.PILE),
                             self._focus_rect(self.PILE).collidepoint(mouse))
        surface.blit(r.back, self.PILE)
        lp_txt = "Cliquez pour piocher" if pile_focus else "Pioche"
        lp = self.tiny.render(lp_txt, True, C.ACCENT if pile_focus else C.TEXT_DIM)
        surface.blit(lp, lp.get_rect(center=(self.PILE[0] + r.w // 2,
                                             self.PILE[1] - 12)))
        # -- défausse --
        if disc_focus:
            self._draw_focus(surface, self._focus_rect(self.DISCARD),
                             self._focus_rect(self.DISCARD).collidepoint(mouse))
        surface.blit(r.back, self.DISCARD)
        if self.discard:
            surface.blit(r.face(self.discard[-1]), self.DISCARD)
        if disc_drop:
            ld_txt = "Cliquez pour défausser"
        elif disc_take:
            ld_txt = "Cliquez pour prendre"
        else:
            ld_txt = "Défausse"
        ld = self.tiny.render(ld_txt, True,
                              C.ACCENT if disc_focus else C.TEXT_DIM)
        surface.blit(ld, ld.get_rect(center=(self.DISCARD[0] + r.w // 2,
                                             self.DISCARD[1] - 12)))
        # halo + minuterie autour de la défausse. Le joueur ne doit savoir QUE s'il
        # peut LUI-MÊME se défausser : le halo n'apparaît donc que si l'humain a une
        # carte CONNUE de la valeur en cours (jamais d'indication sur les autres).
        show_slap = (self.slap_active and self.slap_value is not None
                     and bool(self._known_matching(0, self.slap_value)))
        if show_slap:
            ratio = max(0.0, self.slap_t / self.slap_window)
            box = pygame.Rect(self.DISCARD[0] - 6, self.DISCARD[1] - 6,
                              r.w + 12, r.h + 12)
            pygame.draw.rect(surface, GREEN, box, width=3, border_radius=12)
            bar = pygame.Rect(self.DISCARD[0], self.DISCARD[1] + r.h + 6,
                              int(r.w * ratio), 6)
            pygame.draw.rect(surface, GREEN, bar, border_radius=3)

    def _draw_players(self, surface):
        for seat in range(self.N):
            self._draw_hand(surface, seat)

    def _clickable_slots(self, seat):
        """Indices de cartes mises en évidence pour le clic humain."""
        if seat == 0 and self.phase == "choose":
            return set(range(len(self.players[0].cards)))
        # surbrillance « aide à la défausse » : cartes connues de même valeur, tant
        # que l'humain peut tenter (fenêtre bloquante ou défausse libre) et que
        # l'option d'aide est active
        if self._slap_click_allowed():
            hl = set()
            if seat == 0 and self.opt_slap_highlight and self.slap_value is not None:
                p = self.players[0]
                for i, c in enumerate(p.cards):
                    if c in p.knows and dutch_value(c) == self.slap_value:
                        hl.add(i)
            return hl
        if self.phase == "peek" and seat == 0:
            return set(range(len(self.players[0].cards)))
        if self.phase in ("p_look_self",) and seat == 0:
            return set(range(len(self.players[0].cards)))
        if self.phase in ("p_look_opp",) and seat != 0:
            return set(range(len(self.players[seat].cards)))
        if self.phase in ("p_look_any", "p_swap"):
            return set(range(len(self.players[seat].cards)))
        return set()

    def _draw_hand(self, surface, seat):
        p = self.players[seat]
        rend = self.hand if seat == 0 else self.mini
        rects = self._hand_positions(seat)
        highlight = self._clickable_slots(seat)
        reveal_all = (self.phase == "over")
        active = (seat == self.cur and self.phase not in ("over", "peek"))
        for i, r in enumerate(rects):
            if self.hide_slot == (seat, i):
                surface.blit(rend.slot, r)      # emplacement vide pendant l'anim
                continue
            card = p.cards[i]
            # MÉMOIRE TOTALE : l'humain ne voit ses 2 cartes QUE pendant la phase
            # de mémorisation initiale ; ensuite TOUT est face cachée (ses cartes
            # comme celles des adversaires) jusqu'à la révélation finale — SAUF si
            # l'option « cartes connues visibles » est active (montre alors face
            # visible toutes les cartes que l'humain connaît, où qu'elles soient).
            show_face = reveal_all or \
                (self.phase == "peek" and seat == 0 and card in self.human_peeked) or \
                (self.opt_show_known and self.phase != "peek"
                 and card in self.players[0].knows)
            img = rend.face(card) if show_face else rend.back
            surface.blit(img, r)
            if i in highlight:
                col = GREEN if self.slap_active else C.ACCENT
                sel = any(c is card for _, c in self.power_sel)
                pygame.draw.rect(surface, GOLD if sel else col, r.inflate(6, 6),
                                 width=4 if sel else 3, border_radius=10)
        # plaque nom + infos
        self._draw_plate(surface, seat, active)

    def _draw_plate(self, surface, seat, active):
        p = self.players[seat]
        px, py = self.pod[seat]
        rend = self.hand if seat == 0 else self.mini
        plate = pygame.Rect(0, 0, 150, 34)
        plate.center = (px, py + rend.h // 2 + 26)
        bg = (70, 96, 120) if active else (46, 62, 78)
        pygame.draw.rect(surface, bg, plate, border_radius=9)
        edge = C.ACCENT if active else (90, 100, 110)
        if seat == self.dutch_caller:
            edge = GOLD
        pygame.draw.rect(surface, edge, plate, width=2 if active else 1,
                         border_radius=9)
        label = p.name
        if seat == self.dutch_caller and self.phase != "over":
            label += " · DUTCH"
        surface.blit(self.tiny.render(label, True, C.TEXT_LIGHT),
                     (plate.x + 10, plate.centery - 8))
        if self.phase == "over":
            tot = self.result[2][seat]
            best = (tot == min(self.result[2]))
            info = self.tiny.render(f"{tot} pts", True, GREEN if best else C.TEXT_DIM)
        else:
            info = self.tiny.render(f"{len(p.cards)}", True, C.TEXT_DIM)
        surface.blit(info, info.get_rect(midright=(plate.right - 10, plate.centery)))

    def _draw_drawn(self, surface):
        """Carte piochée tenue par le joueur actif pendant qu'il décide."""
        if self.drawn is None:
            return
        if self.phase not in ("choose", "ai_think", "p_look_self", "p_look_opp",
                              "p_look_any", "p_swap", "slap", "ai_power"):
            return
        pos = self._held_pos(self.cur)
        # l'humain voit sa carte ; une carte prise dans la défausse est publique
        show_face = self.players[self.cur].human or self.from_discard
        img = self.hand.face(self.drawn) if show_face else self.hand.back
        surface.blit(img, pos)
        r = pygame.Rect(pos[0], pos[1], self.hand.w, self.hand.h)
        pygame.draw.rect(surface, C.ACCENT, r.inflate(6, 6), width=2,
                         border_radius=10)
        if show_face:
            lab = self.tiny.render("Piochée", True, C.ACCENT)
            surface.blit(lab, lab.get_rect(center=(r.centerx, r.top - 12)))

    def _draw_peek(self, surface):
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 120))
        surface.blit(veil, (0, 0))
        card = self.peek_show["card"]
        big = pygame.transform.smoothscale(self.hand.face(card),
                                           (self.hand.w * 2, self.hand.h * 2))
        r = big.get_rect(center=(self.cx, C.SCREEN_H // 2 - 20))
        surface.blit(big, r)
        t = self.small.render("Mémorisez cette carte — cliquez pour continuer",
                              True, C.TEXT_LIGHT)
        surface.blit(t, t.get_rect(center=(self.cx, r.bottom + 30)))

    def _draw_floats(self, surface):
        for f in self.floats:
            k = f.t / f.dur
            y = f.y - int(42 * ui.ease_out_cubic(min(1, k)))
            alpha = 255 if k < 0.7 else int(255 * (1 - (k - 0.7) / 0.3))
            font = self.num_font if f.big else self.small
            surf = font.render(f.text, True, f.color)
            surf.set_alpha(max(0, alpha))
            surface.blit(surf, surf.get_rect(center=(f.x, y)))

    def _draw_power_x(self, surface):
        """Petites croix ✕ au-dessus des cartes sélectionnées (pouvoir en cours)
        pour retirer une carte de la sélection d'un clic."""
        for rect, _ in self._power_x_rects():
            cx, cy = rect.center
            pygame.draw.circle(surface, RED, (cx, cy), 13)
            pygame.draw.circle(surface, (250, 250, 250), (cx, cy), 13, 2)
            off = 5
            pygame.draw.line(surface, (250, 250, 250), (cx - off, cy - off),
                             (cx + off, cy + off), 3)
            pygame.draw.line(surface, (250, 250, 250), (cx - off, cy + off),
                             (cx + off, cy - off), 3)

    def _draw_over(self, surface):
        # voile léger : on garde les mains révélées et les totaux visibles autour
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 96))
        surface.blit(veil, (0, 0))
        cx = self.cx
        outcome, caller, totals, counts = self.result
        name = self.players[caller].name
        if outcome == "win":
            txt, col = f"{name} gagne son Dutch !", GOLD
        else:
            txt, col = f"{name} perd son Dutch…", RED
        # bandeau haut (sous le HUD)
        surf = self.big.render(txt, True, col)
        box = surf.get_rect(center=(cx, 100)).inflate(48, 22)
        chip = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(chip, (12, 18, 24, 225), chip.get_rect(), border_radius=16)
        pygame.draw.rect(chip, col, chip.get_rect(), width=3, border_radius=16)
        surface.blit(chip, box.topleft)
        surface.blit(surf, surf.get_rect(center=box.center))
        mn = min(totals)
        sub = self.small.render(
            f"{name} : {totals[caller]} pts en {counts[caller]} cartes"
            f"  ·  meilleur total de la table : {mn} pts", True, C.TEXT_LIGHT)
        surface.blit(sub, sub.get_rect(center=(cx, 148)))
        # boutons au centre (zone libérée : pas de pioche/défausse dessinée)
        for b in self.over_buttons:
            b.draw(surface)
