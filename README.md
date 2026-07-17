# Cartes Classic 🃏

Un jeu de cartes classique en Python (pygame) regroupant plusieurs modes de jeu
derrière un menu commun, avec un soin particulier apporté au visuel, aux
animations et à l'UX.

## Lancer le jeu

```bash
pip install pygame
python main.py
```

Appuyez sur **F11** (ou le bouton du menu) pour passer en **plein écran**.

## Documentation

- 🛠️ [Documentation technique](docs/TECHNIQUE.md) — architecture, modules, rendu.
- 📖 [Règles des modes](docs/regles/) — une fiche détaillée par mode de jeu.

## Modes

| Mode          | État        |
|---------------|-------------|
| Solitaire     | ✅ Jouable  |
| Le Président  | ✅ Jouable  |
| Bataille      | ✅ Jouable  |
| Le Pouilleux  | ✅ Jouable  |
| FreeCell      | 🔜 À venir  |
| Spider        | 🔜 À venir  |

## Solitaire — commandes

- **Glisser-déposer** : déplacer une carte ou une séquence.
- **Double-clic** : envoyer automatiquement une carte vers sa famille (fondation).
- **Clic sur la pioche** : retourner une carte (recycle la défausse quand vide).
- **Boutons** : Nouvelle partie, Annuler, Terminer (résolution auto), Menu.
- **Clavier** : `Espace` pioche · `U` annuler · `N` nouvelle · `Échap` menu · `F11` plein écran.

## Structure

```
main.py              Point d'entrée (fenêtre, boucle, navigation)
game/
  constants.py       Dimensions, couleurs, polices
  ui.py              Easing, dégradé feutre, boutons, ombres
  cards.py           Modèle Card + rendu des cartes (cache)
  scene.py           Base de scène + gestionnaire (transitions en fondu)
  menu.py            Menu de sélection des modes
  solitaire.py       Logique Klondike, glisser-déposer, animations
  president.py       Le Président : scène (affichage/animations/saisie)
  president_game.py  Le Président : moteur pur de règles (sans pygame)
  ai.py / ai_mc.py   Bots du Président : heuristique / Monte-Carlo
  bataille.py        Bataille : duel 2 joueurs avec jokers (54 cartes)
  pouilleux.py       Le Pouilleux (Old Maid) : 2–8 joueurs, interactif
```

## Le Président — l'essentiel

**4 à 8 joueurs** (vous + 3 à 7 IA, au choix sur un écran de config, avec le
niveau d'IA **Normale** ou **Forte** — Monte-Carlo). Videz votre main avant les
autres ; l'ordre de sortie donne les titres (Président → Trou du cul). Points
clés :

- Distribution au choix (si 52 n'est pas divisible par N) : **équitable**
  (excédent retiré, Dames conservées) ou **complète** (toutes les cartes
  distribuées, les joueurs à +1 carte étant côte à côte).
- **1er tour** : la **Dame de cœur** ouvre, la **Dame de pique** fixe le sens du
  jeu (pour toute la partie).
- À 5+ joueurs, les places du milieu sont **neutres** (pas d'échange).
- Ordre des forces `3 < … < As < 2` ; **égalité** acceptée (simples et doubles).
- **Main forcée** (simples) : après 2 cartes égales de suite, posez la 3ᵉ égale
  **ou** couchez-vous.
- **4 mêmes cartes à la suite** ferment le pli (simples 1+1+1+1 ou paires 2+2),
  main au dernier qui a posé.
- Un **2** ferme le pli ; **se coucher** manuellement vous sort de tout le pli.
- **On ne joue pas sur le futur Président** : quand quelqu'un pose sa dernière
  carte et devient Président, le pli se ferme, main au joueur suivant.
- **Révolution** : un **carré posé d'un coup** inverse l'ordre pour toute la
  manche (un autre carré fait une **contre-révolution**).
- **Finir sur un 2** (un 3 en révolution) → pire place disponible.
- **Échange** entre manches, avec choix des dons pour le Président / Vice-Prés.

👉 Règles complètes : [docs/regles/president.md](docs/regles/president.md).

**Commandes :** clic pour (dé)sélectionner · **Jouer** (`Entrée`, bouton, ou
clic sur le tas central) · **Coucher** (`Espace`).

## Bataille — l'essentiel

**Duel à 2** (vous contre l'ordinateur), **sans aucune décision** : on enchaîne
les duels. **54 cartes** = 52 + **2 jokers** (les plus fortes ; ordre
`2 < … < As < Joker`). Chacun retourne sa carte du dessus, la plus forte
remporte les deux. **Égalité → Bataille** : une carte cachée puis une visible
départagent (l'enjeu grossit). Le premier à ramasser toutes les cartes gagne.

**Commandes :** clic / `Espace` avancer (ou accélérer le résultat) · `A` mode
auto · `N` nouvelle partie. 👉 [docs/regles/bataille.md](docs/regles/bataille.md).

## Le Pouilleux — l'essentiel

Version française du *Old Maid*, **interactif** à **2–8 joueurs** (vous + IA). On
retire une carte du jeu pour qu'une seule reste sans partenaire : l'**orpheline**.
Les paires (**même rang + même couleur**) sont défaussées ; à son tour, on pioche
une carte chez son voisin. Deux versions : **classique** (Valet de Trèfle retiré
→ le Valet de Pique est le pouilleux, connu) ou **mystère** (carte retirée au
hasard, orpheline inconnue). Le dernier à détenir l'orpheline est le **Pouilleux**.

**Commandes :** clic sur une carte du voisin pour piocher · `Échap` menu.
👉 [docs/regles/pouilleux.md](docs/regles/pouilleux.md).

## Ajouter un mode

L'architecture par scènes rend l'ajout d'un nouveau mode simple : créer une
`Scene` dans `game/`, l'exposer dans `main.py` (méthode `show_*`), puis passer
`available=True` + l'action dans `game/menu.py`.
