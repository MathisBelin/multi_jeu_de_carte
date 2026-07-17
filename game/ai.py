"""IA des bots du Président — étape 1 : heuristiques + comptage de cartes.

`choose(v)` reçoit une vue en lecture seule de la situation et renvoie la liste
de cartes à poser, ou `None` pour se coucher/passer.

Stratégie : dans un jeu de défausse, **jouer la plus basse carte légale** est
déjà très fort — cela conserve naturellement les cartes de fermeture (2 / 3),
qui sont rarement la carte la plus basse jouable. On y ajoute deux améliorations
sûres : **finir dès qu'on peut** (même via un carré) et, à l'ouverture, ne pas
ouvrir sur sa carte de fermeture. Le comptage de cartes (`unseen`) prépare
l'étape 2 (Monte-Carlo) et affine quelques décisions limites.

Vue `v` : `groups` (rang -> [Card]), `order`, `closer`, `top_power`, `required`,
`unseen` (rang -> nb invisibles), `hand_size`, `n_opp_active`, `revolution`.
"""


def build_view(game, idx):
    """Construit la vue (comptage de cartes) pour le joueur `idx` d'un moteur."""
    from types import SimpleNamespace
    p = game.players[idx]
    groups = {}
    for c in p.hand:
        groups.setdefault(c.rank, []).append(c)
    unseen = {r: max(0, 4 - len(groups.get(r, [])) - game.played_counts.get(r, 0))
              for r in range(1, 14)}
    n_opp = sum(1 for i in range(game.N)
                if i != idx and not game.finished(i) and i not in game.couched)
    return SimpleNamespace(
        groups=groups, order=game.order(), closer=game.closer_rank(),
        top_power=(game.power(game.top_combo[0])
                   if game.top_combo is not None else None),
        required=game.required, unseen=unseen, hand_size=len(p.hand),
        n_opp_active=n_opp, revolution=game.revolution)


def _pw(v, rank):
    return v.order.index(rank)


def _beatable(v, size, power):
    """Un adversaire peut-il encore surenchérir (cartes invisibles) ?"""
    for rank, cnt in v.unseen.items():
        if cnt >= size and v.order.index(rank) > power:
            return True
    return False


def choose(v):
    if v.top_power is None:
        return _lead(v)
    return _follow(v)


def _lead(v):
    ranks = sorted(v.groups, key=lambda r: _pw(v, r))
    # 1) finir : toute la main est d'une seule valeur (même un carré), hors fermeture
    for r in ranks:
        if len(v.groups[r]) == v.hand_size and r != v.closer:
            return list(v.groups[r])
    # 1b) fin de partie : se débarrasser de la fermeture (2 / 3) pendant qu'on
    #     ouvre, pour ne pas être forcé de FINIR dessus (pénalité de place).
    if (v.hand_size <= 3 and v.closer in v.groups
            and len(v.groups[v.closer]) < v.hand_size):
        return list(v.groups[v.closer])
    # 2) ouvrir avec la plus basse valeur non-fermeture, groupe complet
    #    (un carré n'est pas ouvert tel quel : il déclencherait une révolution)
    for r in ranks:
        if r != v.closer:
            cs = v.groups[r]
            return cs[:1] if len(cs) == 4 else list(cs)
    # 3) il ne reste que la fermeture
    cs = v.groups[ranks[0]]
    return cs[:1] if len(cs) == 4 else list(cs)


def _follow(v):
    req = v.required
    cands = [r for r in v.groups
             if len(v.groups[r]) >= req and _pw(v, r) >= v.top_power]
    if not cands:
        return None
    # 1) finir le pli en se vidant (hors fermeture)
    for r in cands:
        if len(v.groups[r]) == v.hand_size == req and r != v.closer:
            return v.groups[r][:req]
    # 2) sinon : la plus basse valeur légale (conserve naturellement les 2 / 3)
    r = min(cands, key=lambda r: _pw(v, r))
    return v.groups[r][:req]
