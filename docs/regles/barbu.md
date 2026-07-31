# Le Barbu

Jeu de **levées à contrats multiples**. Implémenté dans
[`game/barbu.py`](../../game/barbu.py). **3 à 10 joueurs** (vous = siège 0, les
autres sont des IA autonomes). Le but est d'avoir **le moins de points** possible
(les points sont des **pénalités**).

## Le paquet & la distribution

On joue avec le **jeu de 52 cartes**. La distribution est **égale** : quand 52
n'est pas divisible par le nombre de joueurs, on **retire les cartes basses
inutiles** pour que chacun ait exactement `52 // N` cartes (ex. 5 j. → 50 cartes,
10 chacun ; 6 j. → 48, 8 chacun ; 3 j. → 51, 17 chacun).

En retirant, on **garde toujours les cartes importantes de la manche en cours** :

- manche des **cœurs** → **tous les cœurs** sont présents ;
- manche des **dames** → **les 4 dames** sont présentes ;
- manche du **Roi de pique** → le **K♠** est présent ;
- manche **« Tout »** → **cœurs + dames + K♠** sont tous présents.

## Un pli (commun à toutes les manches)

- Le premier joueur pose une carte ; chacun à son tour doit **fournir le signe
  demandé** (♠ ♥ ♦ ♣). Si on n'a pas ce signe, on **se défausse** d'une carte de
  son choix.
- **Pas d'atout** : le pli est remporté par la **plus forte carte du signe
  demandé** (ordre **2 < 3 < … < 10 < Valet < Dame < Roi < As**).
- Le **vainqueur du pli entame** le pli suivant.

## Les 6 manches

Une partie se joue en **6 manches**, dans cet ordre :

| # | Manche | Pénalité |
|---|--------|----------|
| 1 | **Sans règle** | seul le nombre de plis compte |
| 2 | **Les cœurs** | chaque **cœur** ramassé coûte des points |
| 3 | **Les dames** | chaque **dame** ramassée coûte des points |
| 4 | **Le Roi de pique** | ramasser le **K♠** coûte des points |
| 5 | **Le dernier pli** | ramasser le **dernier pli** coûte des points |
| 6 | **Tout à la fois** | cœurs + dames + K♠ + dernier pli, **cumulés** |

**Par défaut, à chaque manche, chaque pli ramassé rapporte aussi +5 points de
pénalité** (en plus de la pénalité propre à la manche). Ainsi, par défaut :

| Manche | Décompte (valeurs par défaut) |
|--------|-------------------------------|
| Sans règle | **+5** par pli |
| Les cœurs | +5 par pli · **+10** par cœur |
| Les dames | +5 par pli · **+20** par dame |
| Le Roi de pique | +5 par pli · **+80** pour le K♠ |
| Le dernier pli | +5 par pli · **+100** pour le dernier pli |
| Tout à la fois | +5 par pli · +10/cœur · +20/dame · +80 K♠ · +100 dernier pli |

Le **premier joueur** est **tiré au sort** au début de la partie, puis **tourne**
d'un siège à chaque manche (il n'est donc pas toujours le même qui commence).

## Fin de partie

À la fin des 6 manches, on additionne les pénalités de chacun : **le joueur avec
le moins de points gagne**.

## Réglages

Sur l'écran de configuration :

- **Nombre de joueurs** (3 à 10).
- **Réglages avancés** (sous-écran dédié) :
  - **Valeurs de pénalité** réglables : chaque pli (défaut **5**), chaque cœur
    (**10**), chaque dame (**20**), Roi de pique (**80**), dernier pli (**100**).
    Chaque valeur a un **champ de saisie** : on la modifie avec les boutons
    **−/+** ou en **cliquant le nombre pour le taper au clavier** (Entrée pour
    valider) ;
  - **Plis comptés (+5 / pli) par manche** : pour chaque manche, on peut activer
    ou désactiver le décompte des plis (tous activés par défaut).

## Commandes

- À votre tour, **cliquez une carte jouable** de votre main (les cartes jouables
  sont **surlignées** ; les injouables — mauvais signe — sont **grisées**).
- **Espace / clic** pour enchaîner après un pli remporté et entre les manches.
- **Échap** : retour au menu.

## Lecture du jeu (présentation)

Les joueurs sont disposés **en cercle**, vous en bas. Chaque **pod** affiche le
nom, le nombre de cartes restantes et le **score courant**. Les cartes jouées
**volent vers le centre** et s'y disposent en couronne (une par joueur). Le
vainqueur du pli est **surligné**, un **`+N`** rouge indique les points encaissés,
puis les cartes du pli **volent vers le vainqueur** avant le pli suivant. Une
**fenêtre d'intro** annonce chaque manche et sa règle ; un **tableau des scores**
s'affiche entre les manches et à la fin.

## Notes d'implémentation

- La force d'une carte est son rang, l'**As** étant la plus forte (`rank_val`).
- La distribution retire les cartes de plus bas rang **hors** cartes importantes
  du contrat (voir plus haut), puis distribue à parts égales.
- L'**IA** est **heuristique** (pas de Monte-Carlo) mais joue plutôt finement.
  Elle cherche à **ne jamais prendre un pli** si elle peut l'éviter :
  - **En suivant**, elle **passe sous** la carte maîtresse quand elle le peut, et
    en profite pour **se débarrasser de sa carte la plus dangereuse** (glisser un
    cœur, une dame ou le K♠ sous une carte plus forte = s'en défausser sans risque).
  - Quand la prise est **inévitable** (elle joue en dernier et ne peut pas passer
    sous), elle évite d'**ajouter** une carte à pénalité au pli et lâche plutôt une
    haute carte **sûre**.
  - **Défaussée** (mauvais signe), elle **jette la carte la plus dangereuse** du
    contrat.
  - **À l'entame**, elle utilise une **mémoire des cartes jouées** pour mener une
    couleur qu'elle **ne remportera pas** (des cartes plus fortes restent en jeu),
    la plus basse possible. En manche « dernier pli », elle jette ses hautes cartes
    tôt pour **garder des basses** pour la fin.
