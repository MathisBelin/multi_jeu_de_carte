# Règles — Spider Solitaire

Implémentation : [`game/spider.py`](../../game/spider.py).

## But du jeu
Constituer **8 suites complètes du Roi à l'As d'une même enseigne**. Chaque suite
achevée est retirée du jeu vers une **fondation**. La partie est gagnée quand les
**8 fondations** sont remplies.

## Matériel & mise en place
- **Deux jeux mélangés = 104 cartes**, soit **8 suites complètes**. Le nombre
  d'enseignes dépend de la **difficulté** choisie sur l'écran de départ :
  - **1 couleur (facile)** : 8 paquets de ♠ uniquement ;
  - **2 couleurs (moyen)** : 4 paquets de ♠ et 4 de ♥ ;
  - **4 couleurs (difficile)** : 2 paquets de chaque enseigne.
- **10 colonnes** (tableau) : les 4 premières reçoivent **6 cartes**, les 6
  suivantes **5 cartes** (54 cartes distribuées). Seule la carte du dessus de
  chaque colonne est face visible.
- **Pioche** (stock) : les **50 cartes** restantes = **5 distributions** de 10.
- **8 fondations** : vides au départ (coin haut gauche).

## Déroulement

### Déplacements
- On pose une carte (ou un groupe) sur une carte de **rang immédiatement
  supérieur**, **quelle que soit l'enseigne** (ex. n'importe quel 6 sur
  n'importe quel 7).
- **Colonne vide** : **n'importe quelle** carte ou groupe peut y être placé.
- On ne déplace un **groupe d'un bloc** que s'il forme une **suite décroissante
  de la même enseigne** (ex. 9♠ 8♠ 7♠). Une suite d'enseignes mélangées reste
  posable une carte à la fois mais ne se déplace pas en bloc.

### La pioche
- Cliquer sur la pioche (ou `Espace`) distribue **1 carte face visible sur
  chaque colonne**.
- **Interdit** tant qu'une **colonne est vide** — chaque colonne doit contenir
  au moins une carte (un message le rappelle).

### Suites terminées
Dès qu'une colonne se termine par une suite **Roi → As de la même enseigne**,
elle est **retirée automatiquement** vers une fondation (animation), puis la
carte découverte en dessous se **retourne**.

### Retournement automatique
Quand on libère une carte face cachée en haut d'une colonne, elle se **retourne
automatiquement** (animation de flip).

## Aides à la jouabilité
- **Double-clic** sur une carte : déplacement **automatique** de la suite vers la
  meilleure colonne d'accueil (même enseigne d'abord, sinon compatible, sinon
  colonne vide).
- **Annuler** (`U`) : revient à l'état précédent (historique complet).
- **Nouvelle** (`N`) : redistribue avec la même difficulté.
- **Difficulté** : revient à l'écran de choix du nombre d'enseignes.

## Score
Départ à **500**, **−1 par déplacement**, **+100 par suite terminée**. Le temps
et le nombre de coups sont affichés en bas.

## Fin de partie
Victoire quand les **8 fondations** sont complètes → écran de félicitations
(temps, coups, score) avec confettis.

## Commandes
Glisser-déposer · double-clic → déplacement auto · clic sur la pioche ou
`Espace` distribuer · `U` annuler · `N` nouvelle · `Échap` menu · `F11` plein
écran.
