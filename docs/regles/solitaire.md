# Règles — Solitaire (Klondike)

Implémentation : [`game/solitaire.py`](../../game/solitaire.py).

## But du jeu
Reconstituer les **4 familles** (♠ ♥ ♦ ♣) dans les fondations, chacune classée
de l'**As** au **Roi**. La partie est gagnée quand les 4 fondations sont
complètes (13 cartes chacune).

## Matériel & mise en place
- Un jeu de **52 cartes**, mélangé.
- **7 colonnes** (tableau) : la colonne _i_ reçoit _i + 1_ cartes (1, 2, …, 7).
  Seule la carte du dessus de chaque colonne est face visible.
- **Pioche** (stock) : les 24 cartes restantes, face cachée.
- **Défausse** (waste) : à côté de la pioche, face visible.
- **4 fondations** : vides au départ.

## Déroulement

### La pioche
- Cliquer sur la pioche retourne **1 carte** vers la défausse.
- Quand la pioche est vide, un clic **recycle** la défausse (elle repart face
  cachée dans la pioche). Le recyclage est illimité.

### Déplacements autorisés
- **Vers une fondation** : une seule carte à la fois, même famille, dans
  l'ordre croissant (As, 2, 3, … Roi).
- **Dans le tableau** : on pose une carte (ou une séquence) sur une carte de
  **couleur opposée** et de **rang immédiatement supérieur** (ex. un 7♥ rouge
  sur un 8♠ noir).
- **Colonne vide** : seule une séquence commençant par un **Roi** peut y être
  placée.
- **Depuis la défausse ou une fondation** : la carte du dessus est jouable vers
  le tableau ou une fondation.

### Séquences
On peut déplacer un groupe de cartes déjà correctement ordonné (rangs
descendants, couleurs alternées) d'une colonne à l'autre.

### Retournement automatique
Quand on libère une carte face cachée en haut d'une colonne, elle se **retourne
automatiquement** (animation de flip).

## Aides à la jouabilité
- **Double-clic** sur une carte : l'envoie automatiquement vers sa fondation si
  le coup est légal.
- **Terminer** (auto-complétion) : disponible quand toutes les cartes du
  tableau sont face visible ; envoie automatiquement les cartes aux fondations.
- **Annuler** (`U`) : revient à l'état précédent (historique complet).
- **Nouvelle partie** (`N`) : redistribue.

## Fin de partie
Victoire quand les 4 fondations sont complètes → écran de félicitations avec le
temps et le nombre de coups, et confettis.

## Commandes
Glisser-déposer · double-clic → fondation · clic sur la pioche ·
`Espace` piocher · `U` annuler · `N` nouvelle · `Échap` menu · `F11` plein écran.
