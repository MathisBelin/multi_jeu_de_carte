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
  - **À votre tour, après avoir pioché** : écartez votre éventuel double, puis
    cliquez **« Donner »** pour présenter votre main au joueur suivant.

## Mise en place

- **2 à 8 joueurs** (vous + IA), choisis sur l'écran de configuration.
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

- **Tour de l'humain** : l'éventail (face cachée) du voisin s'affiche au centre ;
  vous **cliquez** la carte à piocher.
- **Tour d'une IA** : elle pioche une carte au hasard.

Un joueur qui vide sa main est **sauvé** et sort du tour. On continue tant qu'il
reste au moins deux joueurs avec des cartes.

## Réordonner sa main (les deux modes)

Votre main **n'est pas triée automatiquement** : c'est vous qui choisissez
l'ordre de vos cartes, pour que le voisin qui pioche chez vous ne puisse pas
deviner leur position. **Glissez-déposez** vos cartes pour les réarranger, ou
cliquez **Mélanger la main** pour un ordre aléatoire. C'est possible **hors de
votre tour** (au début, et pendant que les autres jouent), mais pas pendant votre
pioche ni au moment de « Donner » votre défausse. Pendant que vous déplacez une
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
réordonner. Cela vaut dans les deux modes (automatique comme manuel).

## Fin de partie

La carte orpheline ne pouvant jamais s'apparier, elle circule jusqu'à ce que
tous les autres joueurs soient sauvés. Le dernier joueur, qui détient l'orpheline,
est le **Pouilleux**. L'écran de fin révèle la carte orpheline, affiche l'ordre
dans lequel les joueurs ont été sauvés, et désigne le perdant.

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
