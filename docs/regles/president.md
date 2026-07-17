# Règles — Le Président (Trou du cul)

Implémentation : [`game/president.py`](../../game/president.py).
**1 joueur humain contre 3 à 7 IA** — soit **4 à 8 joueurs** au total. Le nombre
se choisit sur un **écran de configuration** (boutons − / +) avant de commencer,
ainsi que le **niveau des IA** : « Normale » (heuristique rapide) ou « Forte »
(Monte-Carlo, qui simule des fins de partie — plus redoutable), et l'option
**« À la volée »** (fermeture hors-tour, voir §7) qui peut être **activée ou
désactivée**. Quand elle est activée, deux réglages supplémentaires
apparaissent : la **réactivité des bots** (ne volent pas / 3 s / instantané) et
l'option **« Voler son propre jeu »**.

## But du jeu
Se **débarrasser de toutes ses cartes** le plus vite possible. L'ordre dans
lequel les joueurs terminent détermine leurs **titres** pour la manche
suivante.

## Matériel & distribution
- Un jeu de **52 cartes**, mélangé.
- Quand `52` n'est **pas divisible** par le nombre de joueurs, un choix est
  proposé sur l'écran de configuration (**uniquement dans ce cas**) :
  - **Équitable** _(par défaut)_ : chacun reçoit `52 ÷ N` cartes (arrondi à
    l'inférieur) et l'**excédent est retiré du jeu**, tout le monde a le même
    nombre. Les cartes retirées sont au hasard **sauf les deux Dames**
    (conservées pour l'ordre du 1er tour). Ex. : 5 j. → 10 (2 retirées) ;
    6 j. → 8 (4 retirées) ; 7 j. → 7 (3 retirées) ; 8 j. → 6 (4 retirées).
  - **Complète** : **toutes** les cartes sont distribuées ; les joueurs
    surnuméraires reçoivent **1 carte de plus**. Ces joueurs sont **côte à
    côte** (sièges voisins autour de la table). Ex. : 5 j. → deux voisins à 11,
    les autres à 10.
- À **4 joueurs**, 52 est divisible (13 chacun) : aucune option, aucune carte
  retirée.

## Ordre du premier tour (1re manche uniquement)
Quand tout le monde est encore neutre (aucun titre) :

- Le détenteur de la **Dame de cœur** ♥ **ouvre** la première partie.
- Le **sens du jeu** (fixé pour **toute la partie**) est donné par la **Dame de
  pique** ♠ : le jeu tourne vers le côté (gauche ou droite) où se trouve la Dame
  de pique **le plus proche** du détenteur de la Dame de cœur.
- Si la Dame de pique est à **distance égale** des deux côtés, ou si la **même
  personne** possède les deux Dames, le sens est **tiré au hasard**.

Les manches suivantes : c'est le **Trou du cul** (dernier) qui ouvre, et le sens
reste celui déterminé à la première manche.

## Ordre des forces (puissance des cartes)

Ordre **normal** (faible → fort) :

```
3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < V < D < R < As < 2
```

Le **2** est la carte la plus forte et sert de **carte de fermeture**.

> En **révolution** (voir plus bas), cet ordre est **inversé** : le 2 devient le
> plus faible et le **3** devient le plus fort et la carte de fermeture.

## Déroulement d'un pli

1. Le joueur qui **ouvre** pose un combo de son choix : **simple** (1 carte),
   **paire** (2), **brelan** (3) ou **carré** (4) — toutes de la **même valeur**.
2. Chaque joueur suivant doit poser un combo **du même nombre de cartes** et
   **au moins aussi fort**, ou **se coucher**.
3. Quand plus personne ne peut/veut surenchérir, le **dernier** à avoir posé
   **remporte le pli** et ouvre le suivant.

### Égalité (surenchère « pile poil »)
On peut poser un combo de **valeur égale** à celui du dessus (pas seulement
strictement supérieur). Cela vaut pour les **simples ET les doubles** (et, par
extension, toute taille — mais en pratique seuls simples et doubles permettent
une égalité, une valeur n'existant qu'en 4 exemplaires).

### Se coucher
- **Se coucher volontairement** (bouton **Coucher**) : on renonce et on **ne
  peut plus jouer de tout le pli**, même si on aurait pu surenchérir.
- **Passer par obligation** (aucune carte jouable, ou main forcée non
  satisfiable) : **ne compte pas** comme se coucher — on pourra rejouer plus
  tard dans le pli si l'occasion se présente. Ce passage est **automatique**.

## Règles spéciales

### 1. Fermeture immédiate sur un 2
Dès qu'un **2** est posé (n'importe quelle taille), le pli se **ferme
immédiatement** : celui qui l'a posé remporte le pli et ouvre le suivant.
En révolution, c'est le **3** qui joue ce rôle.

### 2. Fermeture par 4 mêmes cartes à la suite
Si les **4 dernières cartes posées** dans le pli sont de la **même valeur**, le
pli se **ferme** et la main revient au **dernier** joueur à avoir posé. Cela
vaut quelle que soit la taille des combos, tant que 4 cartes identiques se
suivent sur **plusieurs poses** :

- en **simples** : `1 + 1 + 1 + 1` (quatre joueurs posent la même valeur) ;
- en **paires** : `2 + 2` (ex. le joueur 2 pose deux Rois, vous posez deux
  Rois → 4 Rois à la suite → le pli est fermé et vous avez la main).

> ⚠️ Un **carré posé d'un seul coup** (les 4 cartes en une seule pose par la
> même personne) n'est **pas** concerné par cette règle : il déclenche une
> **révolution** (voir §4) et non une fermeture.

### 3. Main forcée (uniquement en simples)
Si **la même carte vient d'être posée 2 fois de suite** (deux simples égaux
consécutifs) juste avant votre tour :

- Vous **devez** poser la **3ᵉ carte égale** si vous l'avez… **ou** choisir de
  vous **coucher** (le jeu ne joue pas automatiquement à votre place).
- Si vous **n'avez pas** la carte égale, vous êtes **sauté sans être couché**
  (le tour passe au suivant, qui joue alors librement — égal ou plus fort).
- Une **4ᵉ carte égale** posée à la suite ferme le pli (§2).

### 4. Révolution & contre-révolution
- La **révolution** se déclenche **uniquement** quand **une seule personne pose
  les 4 cartes identiques d'un seul coup** (un **carré**). Elle **ne** se
  déclenche **pas** si les 4 cartes viennent de personnes différentes.
- Effet : l'**ordre des forces est inversé** — le 2 devient le plus faible, le
  **3 devient le plus fort et la carte de fermeture**.
- La révolution **dure toute la manche**.
- **Contre-révolution** : si une autre personne pose à son tour un carré d'un
  seul coup pendant une révolution, l'ordre **repasse à la normale**. La
  révolution fonctionne donc comme un interrupteur **ON/OFF** basculé à chaque
  carré posé d'un coup.

### 5. Passage automatique
Si vous n'avez **aucun coup possible**, votre tour est **passé
automatiquement** (cela ne compte pas comme vous coucher).

### 6. On ne joue pas sur le futur Président
Si un joueur pose sa/ses **dernière(s) carte(s)** (en un seul coup — simple,
paire, brelan ou carré) et devient ainsi **Président** (premier à finir), le
pli se **ferme immédiatement**, **quelle que soit la carte posée**, et la main
revient à la **personne située après lui**. Personne ne peut donc surenchérir
sur la dernière pose du futur Président.

> Exception : s'il finit sur un **2** (ou un **3** en révolution), il est
> pénalisé (voir plus bas) et n'est donc pas Président — cette règle ne
> s'applique alors pas, mais le 2 ferme quand même le pli (§1).

### 7. À la volée _(option, désactivée par défaut)_
Quand l'option est activée, on peut **fermer un pli hors de son tour** en posant
la **dernière carte qui complète un carré** — et **récupérer la main**. Tout est
affaire de **réactivité** : le premier à réagir l'emporte. Cette règle ne
s'applique **que** dans les plis en **simples** ou en **paires**, et **jamais**
avec un 2 (ni un 3 en révolution), qui ferment déjà instantanément (§1).

Trois cas :

- **Simples, hors-tour** — **3 cartes égales** sont sur le tas et vous détenez la
  **4ᵉ** : vous pouvez la poser **tout de suite**, même si ce n'est pas votre
  tour, ce qui **saute le tour de tout le monde**, ferme le carré (§2) et vous
  donne la main. _Ex. : à 8 joueurs, les joueurs 2, 3 et 4 posent un Roi ;
  détenteur du 4ᵉ Roi, vous le posez avant que le tour n'arrive au joueur 6._
- **Paires, hors-tour** — une **paire** est sur le tas et vous détenez la **paire
  égale** : vous pouvez la poser aussitôt (2 + 2 = carré → fermeture). _Ex. : le
  joueur 4 pose une paire de 5, vous répliquez immédiatement votre paire de 5._
- **Simples, à votre tour (« voler son propre jeu »)** _(sous-option, voir plus
  bas)_ — **2 cartes égales** sont sur le tas (vous êtes donc en **main forcée**)
  et vous détenez les **2 dernières** de ce rang : vous pouvez poser les **deux
  d'un coup** — la 3ᵉ (légale, car c'est votre tour) **et** la 4ᵉ qui ferme le
  carré.

**Réactivité des bots** — un réglage (visible quand l'option est activée) décide
comment les IA réagissent aux occasions à la volée :

- **Ne volent pas** : les bots ne ferment **jamais** hors-tour. Quand **vous**
  pouvez fermer, le jeu **attend** (vous avez tout votre temps) : posez la carte,
  ou cliquez sur **« Ne pas voler »** pour laisser le pli suivre son cours.
- **Réaction 3 s** : les bots réagissent lentement (~3 s) — faciles à devancer.
- **Instantané** : les bots ferment aussitôt qu'ils le peuvent — soyez rapide.

**« Voler son propre jeu »** — sous-option (visible quand l'option est activée,
**désactivée par défaut**) qui autorise le **3ᵉ cas** ci-dessus (poser ses 2
dernières cartes d'un coup à son tour).

> Détails d'équité : comme il n'existe que 4 cartes par rang, **un seul joueur**
> peut saisir une occasion donnée — pas de course à plusieurs. Les fermetures à
> la volée des IA ne s'ouvrent que **pendant le tour d'une autre IA** (jamais
> pendant que vous réfléchissez). Quand **vous** pouvez fermer, le bandeau
> l'annonce, votre carte est mise en avant, et vous la posez avec **Jouer**,
> `Entrée`, ou un **clic sur le tas central**.

## Fin de manche, titres et pénalités

Les joueurs terminent les uns après les autres. Les titres dépendent du nombre
de joueurs :

| Place | Titre |
|------:|-------|
| 1ʳᵉ | **Président** |
| 2ᵉ | **Vice-Président** |
| … | **Neutre** _(uniquement à 5 joueurs ou plus)_ |
| avant-dernière | **Vice-Trou** |
| dernière | **Trou du cul** |

À **4 joueurs**, il n'y a pas de neutre (Président, Vice-Président, Vice-Trou,
Trou du cul). À **5+ joueurs**, les places du milieu sont **neutres** : elles ne
donnent ni ne reçoivent de carte lors de l'échange.

### Pénalité : finir sur une carte de fermeture
Si vous **terminez la manche** en posant en **dernière carte** un **2** (simple,
paire, brelan ou carré), vous êtes relégué à la **pire place disponible** au
lieu de votre rang naturel.

- Si un second joueur commet la même erreur ensuite, il prend la **2ᵉ pire
  place** disponible (la pire étant déjà réservée au premier fautif).
- En **révolution**, la carte pénalisante est le **3** (et il est alors permis
  de finir sur un 2, devenu la plus faible).

## Échange entre les manches

Avant chaque nouvelle manche (à partir de la 2ᵉ) :

- Le **Trou du cul** donne ses **2 meilleures** cartes au **Président**.
- Le **Vice-Trou** donne sa **meilleure** carte au **Vice-Président**.
- En échange, le **Président** rend **2 cartes de son choix** au Trou, et le
  **Vice-Président** rend **1 carte de son choix** au Vice-Trou.
- Les joueurs **neutres** (places du milieu, à 5+ joueurs) **n'échangent pas**.

> Quand **vous** êtes Président ou Vice-Président, un écran dédié vous laisse
> **choisir** les cartes à rendre au perdant (sélection puis « Confirmer le don »).
>
> Quand **vous** êtes un perdant (Trou du cul ou Vice-Trou), vous devez **donner
> vous-même** vos meilleures cartes : elles sont **imposées** et apparaissent en
> **surbrillance** (impossible d'en choisir de moins bonnes — pas de triche) ; il
> ne reste qu'à cliquer **« Donner mes meilleures cartes »**. Pour les IA
> perdantes, le don reste automatique.

## Interface
- **Bandeau** : manche en cours, nombre de joueurs, indicateur « RÉVOLUTION —
  ordre inversé », combo à battre et taille de la série (`×2`, `×3`…).
- **Tableau « CLASSEMENT »** (à gauche) : une ligne par place, du **Président** au
  **Trou du cul** (avec les **Neutres** au milieu à 5+ joueurs), chacune de sa
  couleur. Le nom du joueur **remplace le « ? »** dès qu'il atteint la place
  correspondante — les rôles se remplissent donc **au fur et à mesure** que les
  joueurs terminent.
- **Table** : les adversaires sont disposés **en cercle** autour du tapis ;
  chacun a un panneau (nom, nombre de cartes, titre, état « COUCHÉ ») et un
  petit éventail de dos. Le joueur actif est surligné.
- **Main** : les cartes injouables sont **grisées** automatiquement ; sous main
  forcée, seule la carte égale reste jouable. Quand une **fermeture à la volée**
  est possible (option activée), seule la carte qui ferme est mise en avant et le
  bandeau affiche « À la volée — posez la carte pour fermer le pli ! ».
- **Sélection** : un petit bouton **« Poser »** apparaît **juste au-dessus** des
  cartes choisies (centré). Les cartes que vous **pouvez encore jouer** restent
  nettes ; seules les **injouables** sont grisées. À l'**écran d'échange**, ce
  bouton devient **« Donner »** et les cartes non concernées deviennent
  transparentes (mise au point sur le don obligatoire).

## Commandes
- **Clic** sur une carte : la (dé)sélectionner (même valeur).
- **Jouer** : bouton **« Poser »** flottant au-dessus de la sélection, bouton
  **Jouer** en bas, touche `Entrée`, **ou clic sur le tas de cartes au centre**.
- **Coucher** : bouton ou touche `Espace`.
- `Échap` menu · `F11` plein écran.
