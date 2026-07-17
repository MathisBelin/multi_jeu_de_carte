"""IA des bots — étape 2 : Monte-Carlo par déterminisation (imperfect info).

Pour chaque coup candidat, on tire des mains adverses **plausibles** (comptage
de cartes), on simule la fin de manche avec la politique rapide (`ai.choose`),
et on garde le coup qui donne la **meilleure place moyenne**.

Optimisations (« ne rien recalculer inutilement ») :
- **Raccourci** : aucun/one seul coup légal → décision immédiate, pas de MC.
- **Candidats dédupliqués** par (rang, taille) via `game.legal_moves`, puis
  **pré-filtrés** (on garde les plus bas + se coucher) pour borner le nombre.
- **Déterminisations partagées** : les mêmes tirages servent à TOUS les
  candidats (common random numbers) — pas de ré-échantillonnage par coup.
- **Rollouts** avec l'heuristique (rapide), profondeur naturellement bornée
  (les manches sont finies).
- **État léger** : `game.clone()` partage les objets Card (copie O(cartes)).
"""
import random

from . import ai
from . import constants as C
from .cards import Card


def _rollout(game, root):
    """Joue la manche jusqu'au bout avec l'heuristique ; renvoie la place de root."""
    guard = 0
    while game.phase != "round_over" and guard < 600:
        guard += 1
        idx = game.turn
        if game.is_forced():
            m = [c for c in game.players[idx].hand
                 if c.rank == game.top_combo[0].rank]
            if m:
                game.play(idx, [m[0]])
            else:
                game.forced_skip(idx)
        elif game.top_combo is not None and not game.has_legal(idx):
            game.couche(idx)
        else:
            cards = ai.choose(ai.build_view(game, idx))
            if cards:
                game.play(idx, cards)
            else:
                game.couche(idx)
    return game.places.get(root, game.N - 1)


def _determinize(game, root):
    """Clone `game` et redistribue des mains plausibles aux autres joueurs."""
    g = game.clone()
    own = {}
    for c in g.players[root].hand:
        own[c.rank] = own.get(c.rank, 0) + 1
    unknown = []
    for rank in range(1, 14):
        cnt = 4 - own.get(rank, 0) - g.played_counts.get(rank, 0)
        if cnt > 0:
            unknown += [rank] * cnt
    random.shuffle(unknown)
    it = iter(unknown)
    for j, p in enumerate(g.players):
        if j == root or g.finished(j):
            continue
        p.hand = [Card(C.SPADE, next(it), True) for _ in range(len(p.hand))]
    return g


def _prefilter(game, idx, cands, max_cand):
    """Limite le nombre de candidats : les plus bas + se coucher."""
    non_pass = [m for m in cands if m is not None]
    has_pass = None in cands
    if len(non_pass) <= max_cand:
        return cands
    non_pass.sort(key=lambda m: (game.power(m[0]), len(m)))
    keep = non_pass[:max_cand]
    return keep + ([None] if has_pass else [])


def choose_mc(game, idx, determinizations=32, max_cand=5):
    cands = game.legal_moves(idx)
    playable = [m for m in cands if m is not None]
    # raccourci : décision triviale
    if not playable:
        return None
    if len(cands) == 1:
        return cands[0]
    cands = _prefilter(game, idx, cands, max_cand)
    if len(cands) == 1:
        return cands[0]

    scores = [0.0] * len(cands)
    for _ in range(determinizations):
        base = _determinize(game, idx)          # tirage partagé par tous les candidats
        for i, move in enumerate(cands):
            g = base.clone()
            if move is None:
                g.couche(idx)
            else:
                g.play(idx, move)
            scores[i] += _rollout(g, idx)
    best = min(range(len(cands)), key=lambda i: scores[i])
    return cands[best]
