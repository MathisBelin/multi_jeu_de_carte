# Le Pouilleux

Version française du *Old Maid*. Un jeu de 52 cartes amputé d'une carte, si bien
qu'une seule carte reste **sans partenaire** : la carte « orpheline ». Le joueur
qui la détient à la fin de la partie est le **Pouilleux** (le perdant).

Implémenté dans [`game/pouilleux.py`](../../game/pouilleux.py). Mode **interactif** :
l'humain occupe le siège 0, les autres sièges sont des IA (jeu automatique).

## Appariement des cartes

Deux cartes forment une paire si elles ont **le même rang ET la même couleur**
(rouge = ♥/♦, noir = ♠/♣). Chaque rang possède donc exactement une paire rouge
(♥+♦) et une paire noire (♠+♣). Une main ne conserve jamais deux cartes de même
clé : dès qu'une paire se forme, elle est défaussée.

## Deux versions (choisies à la configuration)

- **Classique** : on retire le **Valet de Trèfle**. Son partenaire de couleur,
  le **Valet de Pique**, reste orphelin — le pouilleux est donc connu d'avance.
- **Pouilleux mystère** : on retire **une carte au hasard**. Personne ne sait
  quelle carte est devenue orpheline (elle n'est révélée qu'à la fin).

Dans les deux cas il reste 51 cartes = 25 paires + 1 orpheline.

## Défausse : automatique ou manuelle (choisie à la configuration)

- **Automatique** (défaut) : les paires — de départ comme en cours de partie —
  sont écartées toutes seules. Rien à faire.
- **Manuelle** : *vous* écartez vous-même vos paires (les IA restent
  automatiques). Vos paires apparaissent **surlignées** dans votre main ; pour
  les défausser, **cliquez les deux cartes** concernées puis **cliquez la pile de
  défausse**. Deux moments :
  - **Au début** : une fois vos paires écartées, cliquez **« Prêt »** (le bouton
    ne s'active que lorsqu'il ne vous reste plus aucune paire).
  - **À votre tour, après avoir pioché** : écartez votre éventuel double,
    mélangez ou réordonnez votre main si vous le souhaitez, puis cliquez
    **« Donner »**. Comme le joueur suivant pioche toujours chez vous, ce **seul**
    clic présente votre main *et* l'autorise à piocher — pas de second « Donner »
    à cet instant.

## Mise en place

- **2 à 10 joueurs** (vous + IA), choisis sur l'écran de configuration.
- Les 51 cartes sont distribuées aussi équitablement que possible (certains
  joueurs ont une carte de plus).
- Chaque joueur **défausse ses paires** (automatiquement, ou à la main pour vous
  en mode manuel). Un joueur qui se retrouve sans carte est immédiatement
  **sauvé**.
- Le premier joueur est tiré au sort.

## Déroulement

Le jeu tourne dans un sens fixe. À son tour, un joueur **pioche une carte, face
cachée, chez son voisin** (le joueur actif précédent dans l'ordre). Si la carte
piochée complète une paire dans sa main, la paire est défaussée (aussitôt en mode
automatique ; par vous, avant de cliquer « Donner », en mode manuel).

- **Tour de l'humain** : les cartes (face cachée) du voisin **viennent se placer
  devant vous** (petite animation depuis son pod vers la zone centrale) ; vous
  **cliquez** ensuite la carte à piocher. La carte choisie **vient à vous** et les
  autres **repartent chez le voisin**.
- **Tour d'une IA** : elle pioche une carte au hasard.

Les joueurs sont disposés **en cercle** (vous en bas, les autres autour). Le
**titre** rappelle la version en cours (« Le Pouilleux — Classique » ou
« — Mystère »).

Un joueur qui vide sa main est **sauvé** et sort du tour. On continue tant qu'il
reste au moins deux joueurs avec des cartes.

## Réordonner sa main (les deux modes)

Votre main **n'est pas triée automatiquement** : c'est vous qui choisissez
l'ordre de vos cartes, pour que le voisin qui pioche chez vous ne puisse pas
deviner leur position. **Glissez-déposez** vos cartes pour les réarranger, ou
cliquez **Mélanger la main** pour un ordre aléatoire. C'est possible **hors de
votre tour** : au début, pendant que les autres jouent, et **au moment de
« Donner »** après votre pioche en mode manuel (juste avant que le voisin pioche
chez vous). Seule votre propre pioche l'interdit. Pendant que vous déplacez une
carte, l'IA attend.

Pendant le glisser, un **emplacement cible surligné** s'ouvre entre les deux
cartes voisines, qui **s'écartent** pour révéler où la carte va se poser : la
destination est ainsi clairement visible avant de lâcher.

**Les IA font de même** : elles rebattent aussi leur main autant de fois qu'elles
le veulent (notamment juste **avant qu'on pioche chez elles** et **après chaque
pioche**), pour rester tout aussi imprévisibles que vous.

**Accord avant qu'on pioche chez vous** : lorsqu'un voisin s'apprête à piocher
dans votre main, le jeu **attend que vous cliquiez « Donner »** avant de lui
laisser prendre une carte — cela vous laisse le temps de mélanger ou de
réordonner. Cela vaut dans les deux modes (automatique comme manuel). En mode
manuel, quand ce voisin est celui qui joue **juste après votre propre tour**, cet
accord est **fusionné** avec le « Donner » de votre défausse : un seul clic suffit
(inutile de cliquer « Donner » deux fois de suite).

## Format : manche unique ou survie (choisi à la configuration)

- **Manche unique** (défaut) : une seule manche. Le détenteur de l'orpheline est
  le **Pouilleux** (perdant), la partie s'arrête.
- **Survie** (min **3 joueurs**) : à la fin de chaque manche, le **Pouilleux est
  éliminé** ; on **redistribue** entre les joueurs restants et on rejoue. On
  continue ainsi jusqu'à ce qu'il ne reste **qu'un seul joueur = le grand
  gagnant**. Entre deux manches, un écran annonce l'éliminé et le bouton
  **« Manche suivante »** relance. Les joueurs éliminés sont marqués **« Éliminé »**
  sur leur plaque.

## Fin de partie

La carte orpheline ne pouvant jamais s'apparier, elle circule jusqu'à ce que
tous les autres joueurs soient sauvés. Le dernier joueur, qui détient l'orpheline,
est le **Pouilleux**. En **manche unique**, l'écran de fin révèle la carte
orpheline, affiche l'ordre dans lequel les joueurs ont été sauvés, et désigne le
perdant. En **survie**, l'écran de fin annonce le **survivant** et l'**ordre
d'élimination**.

## Commandes

- **Clic** sur une carte du voisin : piocher (à votre tour).
- **Glisser-déposer** une carte de votre main : la réordonner (hors de votre tour).
- Bouton **Mélanger la main** : ordre aléatoire (hors de votre tour).
- Bouton **Donner** (phase « on pioche chez vous ») : autoriser le voisin à piocher.
- **Défausse manuelle** : clic court sur une carte de votre main pour la
  (dé)cocher ; pour écarter la paire cochée, cliquez le bouton flottant
  **« Défausser »** qui apparaît au-dessus d'elle (ou la pile de défausse).
  Boutons **Prêt** (début) / **Donner** (après pioche).
- **Échap** : retour au menu.
- Boutons **Rejouer** (mêmes réglages) / **Menu** en fin de partie.
