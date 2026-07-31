# Le Dutch

Variante **maison** du Dutch (aussi appelé Cambio / Dutch Blitz selon les
régions). Implémenté dans [`game/dutch.py`](../../game/dutch.py). **2 à 6
joueurs** (vous = siège 0, les autres sont des IA autonomes).

But : avoir le **plus faible total de points** quand on annonce « Dutch ».
Particularité de cette variante : **seul le joueur qui annonce « Dutch » peut
gagner ou perdre** ; les autres ne font ni l'un ni l'autre lors de la révélation.

## Le paquet et la valeur des cartes

Un jeu de **52 cartes**. La valeur (en points) d'une carte est spécifique au
Dutch :

| Carte | Points |
|-------|--------|
| As | 1 |
| 2 à 10 | leur valeur |
| Valet | 11 |
| Dame | 12 |
| **Roi noir** (♠ / ♣) | **0** |
| **Roi rouge** (♥ / ♦) | **15** |

Le **roi noir est donc la meilleure carte** (0 point) et le **roi rouge la pire**
(15 points).

## Mise en place

1. Chaque joueur reçoit **4 cartes face cachée** devant lui.
2. Chaque joueur **regarde 2** de ses 4 cartes, puis les repose. Le choix est
   **définitif** : une carte que l'on a retournée pour la regarder **ne peut plus
   être « dé-regardée »** (on ne peut pas changer d'avis pour en voir une autre).
3. Ensuite, les cartes ne peuvent plus être regardées — sauf grâce aux
   **pouvoirs**.

C'est un jeu de **mémoire totale** : vous voyez vos 2 cartes **uniquement**
pendant cette phase de mémorisation initiale. Dès que la partie démarre, **toutes
les cartes sont face cachée** — les vôtres **comme** celles des adversaires — et
elles le restent jusqu'à la révélation finale. Les cartes que vous **piochez** ou
que vous voyez grâce à un **pouvoir** ne sont montrées qu'**un bref instant**, puis
reposées : c'est à vous de vous en **souvenir**. Aucun repère permanent à l'écran.

Une **pioche** et une **défausse** sont placées au centre. La première carte de la
pioche est retournée pour amorcer la défausse.

## Un tour

À son tour, un joueur **pioche une carte** — soit dans la **pioche**, soit en
**prenant la carte du dessus de la défausse** —, puis choisit :

- soit de **remplacer** une de ses cartes par la carte piochée (l'ancienne carte
  part à la défausse) ;
- soit de **défausser** la carte piochée pour utiliser son **pouvoir**, s'il en a
  un.

> **Piocher dans la défausse.** On peut prendre la carte visible du dessus de la
> défausse au lieu de la pioche. Comme sa valeur est connue, on **doit alors
> l'échanger** contre une de ses cartes (la carte remplacée part à la défausse) :
> pas de pouvoir et pas de re-défausse dans ce cas.

### Pouvoirs

**Seules deux cartes ont un pouvoir** ; toutes les autres, **sans exception**, n'en
ont aucun.

| Carte défaussée | Pouvoir |
|-----------------|---------|
| **Valet** | **Échanger** deux cartes face cachée : une des siennes avec une adverse, deux de deux adversaires, ou deux des siennes. Les cartes restent face cachée. |
| **Dame** | Regarder **n'importe quelle** carte (la sienne ou celle d'un adversaire) |

Les cartes sans pouvoir (As, 2–10, Rois) ne servent qu'à être conservées (par
remplacement) ou défaussées sans effet.

Quand on **défausse une carte à pouvoir** (peu importe le moyen : bouton ou clic
sur la défausse), on **sélectionne** la ou les cartes concernées (surbrillance dorée,
avec une **croix** pour retirer une sélection) puis **Valider** — la **Dame** demande
1 carte, le **Valet** en demande 2 ; **Annuler** renonce au pouvoir.

> **Remplacer une carte à pouvoir.** Si la carte que vous **remplacez** (celle qui
> part à la défausse) est un **Valet** ou une **Dame**, son pouvoir **s'active pour
> vous** (le joueur qui remplace). En revanche, garder une carte à pouvoir en la
> mettant dans sa main n'active rien : c'est la carte **défaussée** qui compte.

## Défausse instantanée

Règle **permanente**. Dès qu'une carte est posée sur la défausse, **tout joueur**
possédant une carte de **même valeur** peut **immédiatement la défausser** — même
si ce n'est pas son tour, et même le joueur qui vient de poser la carte. La
**rapidité** départage si plusieurs joueurs tentent en même temps.

Se défausser d'une carte **réduit** son nombre de cartes (et donc son total de
points) : c'est un moyen puissant de « vider » sa main.

Par défaut vous défaussez une carte que vous **connaissez** et qui est de la bonne
valeur (repérée par le **halo** et, si l'aide est active, **surlignée**). Avec
l'option **Défausse libre**, vous pouvez **tenter n'importe laquelle** de vos cartes :
bonne valeur → elle part ; **sinon, c'est raté** → **carte de pénalité** (+1).

La défausse instantanée est un mécanisme de **rapidité** qui **ne bloque pas** le
tour suivant en permanence. Le **décompte** (pendant lequel le prochain joueur — un
bot — patiente) ne se déclenche que **si vous pouvez vous défausser** (carte connue
de la bonne valeur) : c'est votre temps pour réagir. Si vous ne pouvez pas, **aucune
attente** — le jeu enchaîne, et les bots qui le peuvent se défaussent en
**arrière-plan**. De même, si **c'est vous le joueur suivant**, votre tour démarre
tout de suite et la fenêtre tourne en arrière-plan. La durée du décompte est réglable
(**Temps de réaction des bots**).

Si la carte défaussée est une **carte à pouvoir**, alors **chaque joueur** qui
s'en défausse (celui qui l'a posée le premier **et** ceux qui la défaussent en
instantané) **utilise son pouvoir**, **chacun son tour** — dans l'ordre du jeu, en
commençant par le joueur actif.

> **Précisions de cette implémentation (règle maison).** Une carte **prise dans la
> défausse** compte comme **connue**. Le **halo vert** + minuterie n'apparaît **que
> si vous** avez une carte **connue** de la bonne valeur (jamais d'indice sur les
> autres) ; la **surbrillance** de la carte à défausser dépend de l'option *Aide à la
> défausse*. Aucun décompte n'est marqué si personne ne peut se défausser (rythme).
> **Plusieurs** joueurs peuvent se défausser sur une même pose.

## Annonce « Dutch »

Au **début de son tour**, un joueur peut annoncer **« Dutch »**. **L'annonce
n'interrompt pas le tour** : après avoir annoncé, on **joue son tour normalement**
(piocher / prendre la défausse, puis remplacer / défausser). On continue aussi à
pouvoir se **défausser instantanément** à tout moment, comme si de rien n'était.

La **seule** conséquence de l'annonce : la partie s'arrête dès que **le tour revient
à l'annonceur** (tous les autres joueurs ont donc joué un tour complet entre-temps),
puis **toutes les cartes sont révélées**. On ne peut annoncer « Dutch » qu'**une
seule fois** par manche (le premier qui annonce fige l'échéance).

## Conditions de victoire

Le joueur ayant annoncé « Dutch » :

- **gagne** immédiatement s'il possède le **plus petit total** de points ;
- **perd** immédiatement si un autre joueur a un total **strictement inférieur**.

Les autres joueurs ne peuvent ni gagner ni perdre lors de cette révélation.

### Gestion des égalités

Si l'annonceur est **à égalité de points** avec un autre joueur :

1. celui qui possède le **moins de cartes** est considéré comme ayant le
   **meilleur score** ;
2. si l'égalité est **parfaite** (même total **et** même nombre de cartes), le
   joueur ayant annoncé « Dutch » **perd** automatiquement.

Autrement dit, l'annonceur gagne seulement si son total est le plus bas **et**,
en cas d'égalité de points, s'il a **strictement moins de cartes** que tous les
ex æquo.

## Options (écran de configuration)

Un sélecteur de **difficulté** propose trois modes :

- **Facile** — toutes les aides **activées** + temps de réaction des bots au **maximum**
  (4 s). Idéal pour découvrir.
- **Difficile** — toutes les aides **désactivées** + réaction au **minimum** (1 s).
- **Perso** — fait apparaître le **menu détaillé** ci-dessous, pour régler chaque
  option individuellement.

> **Règle permanente (sans option).** Le **halo/minuterie** vert autour de la
> défausse n'apparaît **que si vous** avez une carte **connue** de la valeur en cours
> (c'est votre seul moyen de savoir qu'**une défausse vous est possible**). Il ne
> révèle **jamais** ce que peuvent faire les autres.

Réglages ajustables :

- **Cartes connues visibles** (défaut : Non) — affiche **face visible** toutes les
  cartes que **vous connaissez** (les vôtres comme celles d'un adversaire vues via un
  pouvoir), au lieu de tout garder face cachée. Aide-mémoire : plus besoin de retenir.
- **Aide à la défausse** (défaut : Oui) — pendant une fenêtre, **surligne quelle**
  carte connue vous pouvez défausser. Le halo, lui, reste toujours affiché (voir
  ci-dessus) : sans cette aide, vous savez que vous pouvez défausser, mais pas laquelle.
- **Défausse libre** (défaut : Non) — permet de **tenter** avec **n'importe laquelle**
  de vos cartes (pas seulement les connues) ; une erreur coûte une **carte de
  pénalité**.
- **Temps de réaction des bots** (défaut : 2 s ; 1 / 1,5 / 2 / 3 / 4 s) — durée du
  **décompte**. Quand **vous** pouvez vous défausser (carte connue), le bot dont c'est
  le tour **attend ce décompte** avant de jouer, vous laissant le temps de réagir.
  Quand vous ne pouvez pas, aucun temps mort : le jeu enchaîne.

## Commandes

- **Piocher** (bouton ou **clic sur la pioche**) / **Prendre la défausse** (bouton
  ou clic sur la pile de défausse) / **Annoncer « Dutch »** au début de votre tour.
  Pendant votre tour, les deux piles sont **mises en évidence** (halo doré).
- Après avoir pioché : **cliquez une de vos cartes** pour la remplacer, ou
  **défaussez** la carte piochée (bouton **Défausser** — ou **clic sur la pile de
  défausse**, mise en évidence). Le bouton indique « **(pouvoir)** » si la carte
  piochée en a un. (Indisponible si la carte vient de la défausse : elle doit être
  échangée.)
- Pouvoirs : **sélectionnez** la ou les cartes concernées — elles se **surlignent
  en doré**, avec une petite **croix** au-dessus pour retirer une carte de la
  sélection — puis **Valider**. La **Dame** demande **1** carte (à regarder), le
  **Valet** en demande **2** (à échanger). Le bouton **Valider** ne s'active que
  lorsque le bon nombre de cartes est choisi ; **Annuler** renonce au pouvoir.
- **Défausse instantanée** : pendant la fenêtre (halo vert), cliquez **n'importe
  laquelle** de vos cartes — même valeur que la défausse = elle part ; sinon vous
  **piochez une pénalité**. Les cartes **surlignées** sont celles que vous connaissez
  et qui sont sûres à défausser (simple indication).
- **Mémoire totale** : après la mémorisation initiale, **aucune** carte n'est
  affichée face visible en jeu (ni les vôtres ni celles des adversaires). Les
  pouvoirs « regarder » ne montrent une carte qu'un **bref instant**.
- Poser ou défausser une carte est **animé** (la carte vole vers son emplacement
  ou vers la défausse).
- `Échap` : retour au menu.

## Interprétations « maison »

Ces points ne sont pas explicitement tranchés par l'énoncé ; ils suivent la
logique des règles :

- la **défausse instantanée** autorise à tenter **n'importe quelle** carte : la
  bonne valeur part, une erreur coûte une **carte de pénalité** ; la surbrillance
  (cartes **connues** de même valeur) n'est qu'une **indication** ;
- **plusieurs** joueurs peuvent défausser sur une même carte tant que la fenêtre
  est ouverte (chacun sa carte de même valeur) ; si c'est une **carte à pouvoir**,
  chacun **utilise son pouvoir chacun son tour** ;
- l'annonce « Dutch » se fait **au début du tour** mais **n'interrompt pas** le
  tour : l'annonceur joue son tour normalement et continue de pouvoir se défausser
  instantanément ; la partie se termine seulement quand le tour **lui revient** ;
- **remplacer** une carte à pouvoir (Valet/Dame) déclenche son pouvoir pour le
  joueur qui remplace (c'est la carte partie à la défausse qui agit).
