# Règles — Bataille

Implémentation : [`game/bataille.py`](../../game/bataille.py).
Le jeu de cartes le plus simple, à **2 joueurs** : **vous contre l'ordinateur**.
Il n'y a **aucune décision** — tout est déterminé par le hasard ; vous ne faites
qu'enchaîner les duels (clic / `Espace`) ou activer le mode **Auto**.

## Matériel & distribution
- Un jeu de **54 cartes** : les 52 classiques **+ 2 jokers** (un rouge, un noir).
- Le paquet est mélangé puis **partagé en deux** : **27 cartes** chacun, en
  pioche **face cachée**.

## Ordre des forces
```
2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < V < D < R < As < JOKER
```
- L'**As** est fort (juste sous le joker).
- Les **jokers** sont les cartes les plus fortes ; les **deux jokers sont de
  force égale** (joker contre joker ⇒ bataille).

## Déroulement d'un duel
1. Chaque joueur **retourne** sa carte du dessus au centre.
2. La **plus forte** remporte les deux cartes, placées dans les **gains** du
   vainqueur.
3. Les cartes restent visibles un court instant (le **résultat** s'affiche) ;
   un clic / `Espace` accélère le ramassage.

## Bataille (égalité)
Quand les deux cartes retournées ont la **même valeur** :
- chaque joueur pose **1 carte face cachée** (l'enjeu),
- puis **1 carte face visible** qui **départage**.
- Nouvelle égalité ⇒ la bataille **recommence** (l'enjeu grossit).
- Le vainqueur ramasse **tout l'enjeu** accumulé.

## Recomposition de la pioche
Quand une pioche est **vide**, elle est **reconstituée** à partir des cartes
gagnées (**mélangées**) — ce mélange évite les boucles sans fin.

## Fin de partie
- Un joueur gagne dès qu'il **possède les 54 cartes** (l'autre n'a plus rien).
- Si un joueur ne peut **pas fournir la carte visible** d'une bataille, il
  **perd** cette bataille (et la partie s'il n'a plus de cartes du tout).
- Une **borne de sécurité** (4000 duels) tranche par le **nombre de cartes** si
  la partie s'éternise.

## Commandes
- **Clic** (n'importe où) ou `Espace` / `Entrée` : lancer le duel suivant, ou
  **accélérer** l'affichage du résultat.
- **Auto** : bouton (ou touche `A`) pour enchaîner les duels automatiquement.
- **Nouvelle partie** : bouton ou touche `N`.
- `Échap` menu · `F11` plein écran.
