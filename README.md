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
| Solitaire (Klondike) | ✅ Jouable  |
| Spider Solitaire | ✅ Jouable  |
| Le Président  | ✅ Jouable  |
| Bataille      | ✅ Jouable  |
| Le Pouilleux  | ✅ Jouable  |
| Le Bouclié    | ✅ Jouable  |
| Le Barbu      | ✅ Jouable  |
| Le Dutch      | ✅ Jouable  |
| Le 98         | ✅ Jouable  |
| FreeCell      | 🔜 À venir  |

## Solitaire — l'essentiel

La tuile **Solitaire** ouvre un écran de choix entre deux variantes :

### Klondike (le classique)

- **Glisser-déposer** : déplacer une carte ou une séquence.
- **Double-clic** : envoyer automatiquement une carte vers sa famille (fondation).
- **Clic sur la pioche** : retourner une carte (recycle la défausse quand vide).
- **Boutons** : Nouvelle partie, Annuler, Terminer (résolution auto), Menu.
- **Clavier** : `Espace` pioche · `U` annuler · `N` nouvelle · `Échap` menu · `F11` plein écran.

### Spider (2 jeux, 10 colonnes)

Solitaire à **104 cartes** réparties en **10 colonnes**. But : constituer **8
suites du Roi à l'As d'une même couleur**, retirées au fur et à mesure. On empile
en ordre **décroissant, toute couleur**, mais un **bloc ne se déplace que s'il est
d'une seule couleur**. La **difficulté** (1, 2 ou 4 couleurs) se choisit au départ.
La **pioche** distribue une carte sur chaque colonne (interdit si une colonne est
vide). Accessible depuis la tuile **Solitaire** du menu (écran de choix).

- **Commandes** : glisser-déposer · double-clic → déplacement auto · clic sur la
  pioche ou `Espace` distribuer · `U` annuler · `N` nouvelle · **Difficulté**.

👉 [docs/regles/solitaire.md](docs/regles/solitaire.md) ·
[docs/regles/spider.md](docs/regles/spider.md).

## Structure

```
main.py              Point d'entrée (fenêtre, boucle, navigation)
game/
  constants.py       Dimensions, couleurs, polices
  ui.py              Easing, dégradé feutre, boutons, ombres
  cards.py           Modèle Card + rendu des cartes (cache)
  scene.py           Base de scène + gestionnaire (transitions en fondu)
  menu.py            Menu de sélection des modes
  solitaire_select.py Écran de choix Klondike / Spider (tuile « Solitaire »)
  solitaire.py       Logique Klondike, glisser-déposer, animations
  spider.py          Spider Solitaire : 2 jeux, 10 colonnes, 3 difficultés
  president.py       Le Président : scène (affichage/animations/saisie)
  president_game.py  Le Président : moteur pur de règles (sans pygame)
  ai.py / ai_mc.py   Bots du Président : heuristique / Monte-Carlo
  bataille.py        Bataille : duel 2 joueurs avec jokers (54 cartes)
  pouilleux.py       Le Pouilleux (Old Maid) : 2–10 joueurs, interactif
  bouclie.py         Le Bouclié : élimination boucliers/PV, 2–10 joueurs
  barbu.py           Le Barbu : levées à contrats, 3–10 joueurs
  dutch.py           Le Dutch : mémoire/bluff, annonce « Dutch », 2–6 joueurs
  le98.py            Le 98 : total commun ≤ 98, manche unique / survie, 2–10 joueurs
```

## Le Président — l'essentiel

**2 à 10 joueurs** (vous + 1 à 9 IA, au choix sur un écran de config, avec le
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

Version française du *Old Maid*, **interactif** à **2–10 joueurs** (vous + IA). On
retire une carte du jeu pour qu'une seule reste sans partenaire : l'**orpheline**.
Les paires (**même rang + même couleur**) sont défaussées ; à son tour, on pioche
une carte chez son voisin. Deux versions : **classique** (Valet de Trèfle retiré
→ le Valet de Pique est le pouilleux, connu) ou **mystère** (carte retirée au
hasard, orpheline inconnue). Le dernier à détenir l'orpheline est le **Pouilleux**.

**Format :** **manche unique** (le Pouilleux a perdu) ou **survie** (min 3
joueurs) — le Pouilleux est **éliminé** et on rejoue jusqu'au **dernier
survivant**.

**Commandes :** clic sur une carte du voisin pour piocher · `Échap` menu.
👉 [docs/regles/pouilleux.md](docs/regles/pouilleux.md).

## Le Bouclié — l'essentiel

Jeu d'**élimination** à **2–10 joueurs** (vous + IA). Paquet réduit aux rangs
**As (=1) à 10**. Chacun a des **PV** (2 cartes côte à côte) et un **bouclier**
(1 carte à l'horizontale au-dessus, façon Stonehenge). À son tour, on **tire une
carte face cachée** puis on choisit : **attaquer** un adversaire (force = carte +
charges ; le bouclier absorbe sa valeur, un bouclier plus fort renvoie les dégâts),
**changer un bouclier**, **charger** (garder la carte cachée, cumulable, dépensée
d'un coup en attaquant), ou **prendre de la vie** (risqué : >5 gagne, <5 perd). La
carte n'est **révélée qu'à l'action** (sauf charge) ; un **As en bouclier** permet
de voir la carte d'avance. Dernier survivant = vainqueur.

**Commandes :** boutons d'action puis clic sur le pod cible · `Espace`/clic pour
enchaîner · `Échap` menu. 👉 [docs/regles/bouclie.md](docs/regles/bouclie.md).

## Le Barbu — l'essentiel

Jeu de **levées à contrats**, **interactif** à **3–10 joueurs** (vous + IA). But :
avoir **le moins de points**. La partie se joue en **6 manches**, chacune avec sa
pénalité : **sans règle** (chaque pli compte), **les cœurs**, **les dames**, **le
Roi de pique (K♠)**, **le dernier pli**, puis **tout à la fois**. On **fournit le
signe demandé** si on l'a (sinon défausse libre) ; **pas d'atout**, le plus fort
du signe l'emporte et entame le pli suivant. **Distribution égale** (les cartes
basses inutiles sont retirées, en gardant toujours les cartes importantes de la
manche). Par défaut, **chaque pli ramassé coûte +5** en plus de la pénalité de la
manche (5 / 10 / 20 / 80 / 100 par défaut). Un écran **Avancé** permet de régler
ces valeurs et de choisir les manches où le +5/pli s'applique.

**Commandes :** clic sur une carte jouable (les injouables sont grisées) ·
`Espace`/clic pour enchaîner · `Échap` menu.
👉 [docs/regles/barbu.md](docs/regles/barbu.md).

## Le Dutch — l'essentiel

Jeu de **mémoire et de bluff**, **interactif** à **2–6 joueurs** (vous + IA). But :
avoir le **plus petit total** — mais **seul le joueur qui annonce « Dutch »** peut
gagner ou perdre. Chacun a **4 cartes face cachée** et n'en **regarde que 2** au
départ. **Valeurs spéciales** : As=1, figures J=11/Q=12, **Roi noir = 0** (la
meilleure), **Roi rouge = 15** (la pire). À son tour, on **pioche** puis on
**remplace** une de ses cartes ou on **défausse** la piochée pour son **pouvoir**.
**Seuls le Valet** (échanger deux cartes) **et la Dame** (regarder n'importe quelle
carte) ont un pouvoir — toutes les autres cartes n'en ont aucun. **Remplacer** une
carte à pouvoir (celle qui part à la défausse) déclenche son pouvoir pour toi.
**Défausse instantanée** permanente : dès qu'une carte tombe, tout joueur ayant la
**même valeur** peut s'en défausser, même hors tour (vous pouvez tenter **n'importe
quelle** carte — une erreur coûte une **carte de pénalité** ; la surbrillance
indique vos cartes connues sûres). C'est une question de **rapidité** : elle **ne
bloque pas** le tour suivant — si c'est **vous** le suivant, vous jouez tout de
suite pendant que les bots se défaussent en arrière-plan. On annonce **« Dutch »** quand
on se croit le plus bas : **l'annonce ne coupe pas le tour** — on joue son tour
normalement et on peut continuer à se défausser ; la partie se termine simplement
quand le **tour revient à l'annonceur**, puis on révèle.

**Difficulté** (écran de config) : **Facile** (toutes les aides + réaction lente),
**Difficile** (aucune aide + réaction éclair), **Perso** (menu d'options ci-dessous).

**Options** (mode Perso) : **Cartes connues visibles** (montre face visible ce
que vous connaissez), **Aide à la défausse** (surligne *quelle* carte défausser),
**Défausse libre** (tenter avec n'importe quelle carte, pénalité si erreur), **Temps
de réaction des bots** (durée du décompte). Le halo vert n'apparaît **que si vous**
avez une carte connue à défausser — jamais d'indice sur les autres.

**Commandes :** **Piocher** / **Annoncer « Dutch »**, puis clic sur une carte à
remplacer ou **Défausser (pouvoir)** · clic pour les pouvoirs · clic sur une carte
surlignée pendant la **défausse instantanée** · `Échap` menu.
👉 [docs/regles/dutch.md](docs/regles/dutch.md).

## Le 98 — l'essentiel

Jeu de **défausse à total commun**, **interactif** à **2–10 joueurs** (vous + IA).
Chacun a **4 cartes** ; à tour de rôle on pose une carte qui **modifie le total**
d'une pile commune, puis on repioche. Le total ne doit **jamais dépasser 98** :
celui qui ne peut plus jouer sans le dépasser **fait déborder la pile**. **Valeurs
spéciales** : **As** = +1 ou +11 (au choix), **Valet** = 0 et **inverse le sens**,
**Dame** = **−10**, **Roi** = total à **70** ; les cartes **2 à 10** ajoutent leur
valeur. Deux formats : **Manche unique** (le premier à déborder a perdu) ou
**Survie** (min 3 joueurs : chaque perdant est éliminé, on rejoue jusqu'au
**dernier survivant**).

**Commandes :** clic sur une carte jouable (les injouables sont grisées) ; pour un
**As**, choisissez **1** ou **11** · `Échap` menu.
👉 [docs/regles/le98.md](docs/regles/le98.md).

## Ajouter un mode

L'architecture par scènes rend l'ajout d'un nouveau mode simple : créer une
`Scene` dans `game/`, l'exposer dans `main.py` (méthode `show_*`), puis passer
`available=True` + l'action dans `game/menu.py`.
