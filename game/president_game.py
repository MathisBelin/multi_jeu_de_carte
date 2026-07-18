"""Moteur pur du Président — toute la logique de règles, sans pygame.

Ce moteur est la **source unique de vérité** des règles. Il est utilisé par la
scène (`president.py`, pour l'affichage/animations) et par l'IA Monte-Carlo
(`ai_mc.py`, pour simuler des fins de partie). Il ne fait aucun rendu, aucune
animation, aucun minuteur.

Les actions (`play`, `couche`, `forced_skip`) mutent l'état et renvoient un
`Result` décrivant ce qui s'est passé (révolution, joueur qui finit, pli
remporté, fin de manche). L'état avance immédiatement (pas de pause : la pause
entre plis est purement visuelle, gérée par la scène).
"""
import random

from . import constants as C
from .cards import Card

ORDER = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 1, 2]      # 3 faible -> 2 fort
ORDER_REV = list(reversed(ORDER))                         # revolution
QUEEN = 12
NAMES = ["Vous", "Alice", "Bruno", "Carla", "David", "Elsa", "Hugo", "Inès",
         "Jules", "Kenza"]


class Player:
    __slots__ = ("index", "seat", "name", "human", "hand", "title")

    def __init__(self, index, name, human=False):
        self.index = index
        self.seat = index
        self.name = name
        self.human = human
        self.hand = []
        self.title = None

    def sort(self):
        self.hand.sort(key=lambda c: ORDER.index(c.rank))


class Result:
    __slots__ = ("revolution_toggled", "finished", "trick_closed",
                 "winner", "round_over")

    def __init__(self):
        self.revolution_toggled = False
        self.finished = None        # (idx, place) si un joueur vient de finir
        self.trick_closed = False
        self.winner = None          # meneur du nouveau pli
        self.round_over = False


class PresidentGame:
    def __init__(self, n=4, equitable=True, direction=1, prev_ranking=None,
                 round_no=0, small_roles="ends"):
        self.N = n
        self.equitable = equitable
        # À moins de 4 joueurs, il n'y a pas la place pour les 4 titres : on
        # garde soit les EXTRÊMES ("ends" → Président / Trou du cul), soit les
        # VICES ("vices" → Vice-Président / Vice-Trou). Sans effet à N >= 4.
        self.small_roles = small_roles
        self.direction = direction
        self.prev_ranking = prev_ranking
        self.round_no = round_no
        self._exchange_pending = None
        self.extra_block = []
        self.phase = "playing"

    # ------------------------------------------------------------------
    # Mise en place d'une manche
    # ------------------------------------------------------------------
    def new_round(self):
        """Distribue et prépare la manche. Renvoie ('play', start) ou
        ('exchange', give_to, n) si l'humain (siège 0) doit choisir ses dons."""
        self.round_no += 1
        self.players = [Player(i, NAMES[i], human=(i == 0)) for i in range(self.N)]

        deck = [Card(s, r, True) for s in C.SUITS for r in range(1, 14)]
        random.shuffle(deck)
        per = 52 // self.N
        rem = 52 % self.N
        counts = [per] * self.N
        self.extra_block = []
        if rem and self.equitable:
            protected = {(C.HEART, QUEEN), (C.SPADE, QUEEN)}
            removable = [c for c in deck if (c.suit, c.rank) not in protected]
            for c in removable[:rem]:
                deck.remove(c)
        elif rem:
            start = random.randrange(self.N)
            self.extra_block = [(start + k) % self.N for k in range(rem)]
            for s in self.extra_block:
                counts[s] += 1
        it = iter(deck)
        for i in range(self.N):
            for _ in range(counts[i]):
                self.players[i].hand.append(next(it))
        for p in self.players:
            p.sort()

        self.played_counts = {}
        self.top_combo = None
        self.required = None
        self.run_len = 0
        self.run_cards = 0
        self.forcing_lifted = False
        self.revolution = False
        self.couched = set()
        self.leader = None
        self.places = {}
        self.avail = set(range(self.N))
        self.ranking = None
        self.phase = "playing"
        self.turn = None
        self._exchange_pending = None

        if self.prev_ranking:
            for place, idx in enumerate(self.prev_ranking):
                self.players[idx].title = self.title_for(place)
            human_action = self._setup_exchange()
            if human_action:
                self._exchange_pending = human_action
                return ("exchange",) + human_action
            start = self.prev_ranking[self.N - 1]
        else:
            start = self._first_round_order()
        self.start_trick(start)
        return ("play", start)

    def apply_human_gift(self, cards):
        """L'humain GAGNANT (Président / Vice-Président) rend `cards` de son choix
        au perdant, puis la manche démarre."""
        _, give_to, _ = self._exchange_pending
        for c in cards:
            self.players[0].hand.remove(c)
            self.players[give_to].hand.append(c)
        self.players[0].sort()
        self.players[give_to].sort()
        start = self.prev_ranking[self.N - 1]
        self.start_trick(start)
        return start

    def human_best_gift(self):
        """Les n meilleures cartes que l'humain PERDANT doit donner (pour la
        surbrillance). Vide si l'échange courant n'est pas de ce type."""
        if not self._exchange_pending or self._exchange_pending[0] != "give_best":
            return []
        n = self._exchange_pending[2]
        return sorted(self.players[0].hand, key=lambda c: ORDER.index(c.rank))[-n:]

    def apply_human_give_best(self):
        """L'humain PERDANT (Trou / Vice-Trou) donne lui-même ses n MEILLEURES
        cartes (imposées) au gagnant ; le gagnant (IA) rend ses n plus basses,
        puis la manche démarre."""
        _, winner, n = self._exchange_pending
        for c in self.human_best_gift():
            self.players[0].hand.remove(c)
            self.players[winner].hand.append(c)
        self._give_lowest(winner, 0, n)
        self.players[0].sort()
        self.players[winner].sort()
        start = self.prev_ranking[self.N - 1]
        self.start_trick(start)
        return start

    def _seat_of(self, suit, rank):
        for p in self.players:
            if any(c.suit == suit and c.rank == rank for c in p.hand):
                return p.index
        return None

    def _first_round_order(self):
        qh = self._seat_of(C.HEART, QUEEN)
        qs = self._seat_of(C.SPADE, QUEEN)
        if qh is None or qs is None or qh == qs:
            self.direction = random.choice([1, -1])
        else:
            d_plus = (qs - qh) % self.N
            d_minus = (qh - qs) % self.N
            if d_plus < d_minus:
                self.direction = 1
            elif d_minus < d_plus:
                self.direction = -1
            else:
                self.direction = random.choice([1, -1])
        return qh if qh is not None else 0

    # ---- echange ----
    def _setup_exchange(self):
        """Prépare l'échange entre manches. Renvoie l'action interactive de
        l'humain, ou None :
        - ("give_back", loser, n) : l'humain GAGNANT choisit n cartes à rendre
          (ses meilleures ont déjà été prises au perdant IA) ;
        - ("give_best", winner, n) : l'humain PERDANT doit donner lui-même ses n
          MEILLEURES cartes — le prélèvement est DIFFÉRÉ jusqu'à sa confirmation
          (impossible de tricher : les cartes sont imposées)."""
        r = self.prev_ranking
        if self.N >= 4:
            pairs = ((r[0], r[self.N - 1], 2), (r[1], r[self.N - 2], 1))
        elif self.small_roles == "vices":
            # Vice-Président ↔ Vice-Trou : un seul échange, 1 carte.
            pairs = ((r[0], r[self.N - 1], 1),)
        else:
            # Président ↔ Trou du cul : un seul échange, 2 cartes.
            pairs = ((r[0], r[self.N - 1], 2),)
        human_action = None
        for winner, loser, n in pairs:
            if self.players[loser].human:
                human_action = ("give_best", winner, n)     # différé (confirmation)
            elif self.players[winner].human:
                self._take_best(loser, winner, n)
                human_action = ("give_back", loser, n)
            else:
                self._take_best(loser, winner, n)
                self._give_lowest(winner, loser, n)
        for p in self.players:
            p.sort()
        return human_action

    def _take_best(self, src, dst, n):
        cs = sorted(self.players[src].hand, key=lambda c: ORDER.index(c.rank))[-n:]
        for c in cs:
            self.players[src].hand.remove(c)
            self.players[dst].hand.append(c)

    def _give_lowest(self, src, dst, n):
        cs = sorted(self.players[src].hand, key=lambda c: ORDER.index(c.rank))[:n]
        for c in cs:
            self.players[src].hand.remove(c)
            self.players[dst].hand.append(c)

    # ------------------------------------------------------------------
    # Règles
    # ------------------------------------------------------------------
    def order(self):
        return ORDER_REV if self.revolution else ORDER

    def power(self, card):
        return self.order().index(card.rank)

    def prank(self, rank):
        return self.order().index(rank)

    def closer_rank(self):
        return 3 if self.revolution else 2

    def is_forced(self):
        return (self.required == 1 and self.top_combo is not None
                and self.run_len >= 2 and not self.forcing_lifted)

    def can_beat(self, cards):
        if not cards:
            return False
        rank = cards[0].rank
        if any(c.rank != rank for c in cards):
            return False
        if self.top_combo is None:
            return True
        if len(cards) != self.required:
            return False
        return self.power(cards[0]) >= self.power(self.top_combo[0])

    def has_legal(self, idx):
        p = self.players[idx]
        if self.top_combo is None:
            return bool(p.hand)
        r = self.required
        tp = self.power(self.top_combo[0])
        groups = {}
        for c in p.hand:
            groups.setdefault(c.rank, []).append(c)
        for cs in groups.values():
            if len(cs) >= r and self.power(cs[0]) >= tp:
                return True
        return False

    def finished(self, idx):
        return idx in self.places

    def next_actor(self, frm):
        for k in range(1, self.N + 1):
            idx = (frm + k * self.direction) % self.N
            if idx == frm:
                # revenu à soi-même : plus aucun autre joueur ne peut répondre
                # (les autres sont finis / couchés / meneur) → le pli se ferme.
                continue
            if self.finished(idx) or idx in self.couched or idx == self.leader:
                continue
            return idx
        return None

    def first_active_after(self, frm):
        for k in range(1, self.N + 1):
            idx = (frm + k * self.direction) % self.N
            if not self.finished(idx):
                return idx
        return None

    def title_for(self, place):
        if self.N >= 4:
            if place == 0:
                return "Président"
            if place == 1:
                return "Vice-Président"
            if place == self.N - 1:
                return "Trou du cul"
            if place == self.N - 2:
                return "Vice-Trou"
            return "Neutre"
        # Moins de 4 joueurs : deux titres seulement (au choix), Neutre au milieu.
        top, bottom = (("Vice-Président", "Vice-Trou")
                       if self.small_roles == "vices"
                       else ("Président", "Trou du cul"))
        if place == 0:
            return top
        if place == self.N - 1:
            return bottom
        return "Neutre"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def start_trick(self, idx):
        self.top_combo = None
        self.required = None
        self.run_len = 0
        self.run_cards = 0
        self.forcing_lifted = False
        self.couched = set()
        self.leader = None
        self.turn = idx

    def play(self, idx, cards):
        p = self.players[idx]
        for c in cards:
            p.hand.remove(c)
            self.played_counts[c.rank] = self.played_counts.get(c.rank, 0) + 1
        old = self.top_combo
        size = len(cards)
        if old is None or self.power(cards[0]) > self.power(old[0]):
            self.run_len = 1
            self.run_cards = size
        else:
            self.run_len += 1
            self.run_cards += size
        self.top_combo = list(cards)
        self.required = size
        self.leader = idx
        self.forcing_lifted = False

        rank = cards[0].rank
        chain4 = (self.run_cards >= 4 and self.run_len >= 2)
        closer = (rank == self.closer_rank())
        closed = chain4 or closer
        toggle = (size == 4)
        bad = (len(p.hand) == 0) and (rank == self.closer_rank())
        will_finish = (len(p.hand) == 0)

        res = Result()
        if toggle:
            self.revolution = not self.revolution
            res.revolution_toggled = True
        if will_finish:
            place = self._assign_place(idx, bad)
            res.finished = (idx, place)
            if self.phase == "round_over":
                res.round_over = True
                return res
            if self.places.get(idx) == 0:      # on ne joue pas sur le futur Président
                closed = True
        if closed:
            winner = idx if not self.finished(idx) else self.first_active_after(idx)
            self._close_trick(res, winner)
        else:
            nxt = self.next_actor(idx)
            if nxt is None:
                self._close_trick(res, self._winner_from_leader())
            else:
                self.turn = nxt
        return res

    def couche(self, idx):
        self.couched.add(idx)
        return self._resolve_nonplay(idx)

    def forced_skip(self, idx):
        self.forcing_lifted = True
        return self._resolve_nonplay(idx)

    def _resolve_nonplay(self, idx):
        res = Result()
        nxt = self.next_actor(idx)
        if nxt is None:
            self._close_trick(res, self._winner_from_leader())
        else:
            self.turn = nxt
        return res

    def _close_trick(self, res, winner):
        res.trick_closed = True
        res.winner = winner
        if winner is not None:
            self.start_trick(winner)

    def _winner_from_leader(self):
        if self.leader is None:
            return self.first_active_after(self.turn)
        return (self.leader if not self.finished(self.leader)
                else self.first_active_after(self.leader))

    def _assign_place(self, idx, bad):
        place = max(self.avail) if bad else min(self.avail)
        self.places[idx] = place
        self.avail.discard(place)
        not_fin = [i for i in range(self.N) if i not in self.places]
        if len(not_fin) == 1:
            last = not_fin[0]
            lp = min(self.avail)
            self.places[last] = lp
            self.avail.discard(lp)
            self._end_round()
        return place

    def _end_round(self):
        self.phase = "round_over"
        self.ranking = [None] * self.N
        for idx, pl in self.places.items():
            self.ranking[pl] = idx
        for pl, idx in enumerate(self.ranking):
            self.players[idx].title = self.title_for(pl)
        self.prev_ranking = list(self.ranking)

    # ------------------------------------------------------------------
    # Utilitaires IA
    # ------------------------------------------------------------------
    def legal_moves(self, idx):
        """Coups légaux dédupliqués par (rang, taille) ; None = se coucher.
        Ne gère pas la main forcée (l'appelant utilise is_forced/forced_skip)."""
        p = self.players[idx]
        groups = {}
        for c in p.hand:
            groups.setdefault(c.rank, []).append(c)
        moves = []
        if self.top_combo is None:
            for cs in groups.values():
                for size in range(1, len(cs) + 1):
                    moves.append(cs[:size])
            return moves
        r = self.required
        tp = self.power(self.top_combo[0])
        for cs in groups.values():
            if len(cs) >= r and self.power(cs[0]) >= tp:
                moves.append(cs[:r])
        moves.append(None)
        return moves

    # ---- « à la volée » (option) : fermeture d'un carré hors-tour ----
    def snap_moves(self, idx):
        """Coups « à la volée » HORS-TOUR pour fermer le pli (complètent un
        carré). Renvoie la liste des combos possibles (au plus un ; il n'existe
        que 4 cartes par rang) ; combo = liste de Card.

        - Simples : 3 cartes égales au sommet + le joueur détient la 4e.
        - Doubles : une paire au sommet + le joueur détient la paire égale.

        Exclut le meneur courant (on ne « snappe » pas son propre coup), les
        joueurs finis/couchés et le rang de fermeture (2, ou 3 en révolution :
        il ferme déjà instantanément)."""
        if self.top_combo is None or idx == self.leader:
            return []
        if self.finished(idx) or idx in self.couched:
            return []
        rank = self.top_combo[0].rank
        if rank == self.closer_rank():
            return []
        same = [c for c in self.players[idx].hand if c.rank == rank]
        if self.required == 1 and self.run_cards == 3 and len(same) >= 1:
            return [[same[0]]]
        if self.required == 2 and self.run_cards == 2 and len(same) >= 2:
            return [same[:2]]
        return []

    def self_complete_move(self, idx):
        """Cas « je vole mon propre jeu » : À SON TOUR, 2 simples égaux au
        sommet (main forcée) et le joueur détient les 2 dernières cartes de ce
        rang → il peut poser les deux d'un coup (3e + 4e) pour fermer le carré.
        Renvoie les 2 cartes, ou None."""
        if self.top_combo is None or self.required != 1 or self.run_cards != 2:
            return None
        rank = self.top_combo[0].rank
        if rank == self.closer_rank():
            return None
        same = [c for c in self.players[idx].hand if c.rank == rank]
        if len(same) >= 2:
            return same[:2]
        return None

    def clone(self):
        g = PresidentGame.__new__(PresidentGame)
        g.N = self.N
        g.equitable = self.equitable
        g.small_roles = self.small_roles
        g.direction = self.direction
        g.prev_ranking = list(self.prev_ranking) if self.prev_ranking else None
        g.round_no = self.round_no
        g._exchange_pending = None
        g.extra_block = []
        g.phase = self.phase
        g.revolution = self.revolution
        g.top_combo = list(self.top_combo) if self.top_combo else None
        g.required = self.required
        g.run_len = self.run_len
        g.run_cards = self.run_cards
        g.forcing_lifted = self.forcing_lifted
        g.leader = self.leader
        g.turn = self.turn
        g.couched = set(self.couched)
        g.places = dict(self.places)
        g.avail = set(self.avail)
        g.played_counts = dict(self.played_counts)
        g.ranking = list(self.ranking) if self.ranking else None
        g.players = []
        for p in self.players:
            np = Player(p.index, p.name, p.human)
            np.seat = p.seat
            np.title = p.title
            np.hand = list(p.hand)
            g.players.append(np)
        return g
