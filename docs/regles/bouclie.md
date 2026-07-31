# Le Bouclié

Jeu d'**élimination** à base de boucliers, façon Stonehenge. Implémenté dans
[`game/bouclie.py`](../../game/bouclie.py). **2 à 10 joueurs** (vous = siège 0,
les autres sont des IA autonomes).

## Le paquet

40 cartes : les rangs **As à 10** dans les 4 enseignes. **Ni figures ni jokers.**
L'**As vaut 1** (la plus faible), le **10** est la plus forte. La valeur d'une
carte est donc simplement son rang (1 à 10).

## Mise en place

Chaque joueur reçoit **3 cartes** :

- les **deux premières** sont posées **côte à côte, face visible** : elles
  forment ses **points de vie** (PV = la somme des deux, soit 2 à 20 au départ) ;
- la **troisième** est posée **à l'horizontale, juste au-dessus** des deux cartes
  de PV : c'est le **bouclier** (comme un linteau de Stonehenge).

Le **sens du jeu** et le **premier joueur** sont tirés au sort. On joue chacun son
tour dans le sens fixé.

## Un tour

Au début de son tour, le joueur **pioche une carte face cachée**. Il choisit
ensuite une action. **La carte n'est révélée qu'au moment de l'action** — sauf
pour la **charge** (elle reste cachée). Actions possibles :

### Attaquer un adversaire
La **force de frappe** = valeur de la carte tirée **+ toutes les charges
accumulées** (voir Charger). On la compare au **bouclier** de la cible :

- **force > bouclier** : la cible **perd (force − bouclier) PV**. Son bouclier
  **reste intact**. *(Ex. : j'attaque avec un 5 un bouclier de 3 → le bouclier
  absorbe 3, la cible perd 2 PV.)*
- **force = bouclier** : **rien** ne se passe.
- **force < bouclier** : c'est **l'attaquant** qui **perd (bouclier − force) PV**
  en retour. *(Ex. : bouclier 10 contre attaque 6 → l'attaquant perd 4 PV.)*

### Changer un bouclier
Remplacer un bouclier — **le sien ou celui d'un joueur de son choix** — par la
carte tirée. L'ancien bouclier est défaussé.

### Charger
Garder la carte tirée **face cachée** au-dessus de son bouclier. On peut **cumuler
plusieurs charges** au fil de ses tours. Lorsqu'on attaque, **toutes les charges
partent d'un coup** (obligatoirement) et s'ajoutent à la force de frappe.
⚠️ **Si on perd des PV** (par une attaque subie, un retour de bouclier ou un soin
raté), on **perd toutes ses charges** — sauf si l'on ne perd **aucun** PV.

### Prendre de la vie
Action **risquée** :

- carte tirée **≤ 5** : on **gagne sa valeur en PV** *(tirer 3 → +3 PV, tirer 5
  → +5 PV)* ;
- carte tirée **> 5** : on **perd** l'écart qui la sépare de 5
  *(tirer 7 → −2 PV, tirer 9 → −4 PV)*.

## As en bouclier

Si, au **début de son tour**, on a un **As en bouclier**, on **voit la valeur** de
la carte tirée **avant** de choisir son action (les autres jouent à l'aveugle).

## Élimination et victoire

Un joueur dont les **PV tombent à 0** (ou moins) est **éliminé**. La partie
continue jusqu'à ce qu'il ne reste **qu'un seul joueur debout** : il **gagne**.

## Commandes

- À votre tour, choisissez : **Attaquer** · **Changer bouclier** · **Charger** ·
  **Prendre de la vie**.
- Pour **Attaquer** ou **Changer bouclier**, cliquez ensuite le **pod** de la
  cible (adversaire pour attaquer ; n'importe qui, vous compris, pour un
  bouclier), ou **Annuler**.
- **Espace / clic** pour enchaîner après la résolution d'un coup.
- **Échap** : retour au menu.

## Lecture du jeu (animations)

Les joueurs sont disposés **en cercle**, vous en bas. Le **bouclier** de chaque
joueur est montré à la fois **en carte** (posée à l'horizontale, façon Stonehenge)
et par un **écusson** (logo bouclier + chiffre) lisible d'un coup d'œil ; les PV
sont montrés **en cartes** pour tout le monde. À chaque tour, la
carte piochée **vole vers le joueur actif** (on voit qui joue), un **bandeau**
annonce l'**action choisie et sa cible** (ex. « ATTAQUE > Alice »), puis la carte
**vole vers la cible** avant de résoudre. Chaque action se **déroule visiblement** :

- **Attaque** : les cartes sont retournées **une à une** au centre — d'abord les
  **charges**, puis la **carte tirée** — avec un compteur **« Force : N »** qui se
  cumule. Puis la frappe : **nombre de dégâts flottant** (`−N PV`) et
  **tremblement** sur la cible si ça touche, **« Bloqué ! »** + halo de bouclier si
  l'attaque est **égale** (esquive), **« Riposte ! »** sur la cible et **`−N PV`**
  sur l'attaquant si le bouclier est **plus fort**.
- **Soin** : `+N PV` (vert) si réussi, `−N PV (raté)` (rouge) si la carte est < 5.
- **Changer bouclier** : la carte est révélée puis un halo signale le nouveau
  bouclier (`ancien → nouveau`).
- **Charge** : la carte part **face cachée** au-dessus du bouclier (`Charge ×N`).

Les **PV de chacun** (vous et adversaires) sont affichés **sous forme de cartes**,
et le **bouclier** est une carte **de la même taille** posée à l'horizontale.

## Notes d'implémentation

- Les PV sont un **entier** (source de vérité) ; l'affichage « côte à côte » les
  représente par des cartes qui **somment** à ce total (`pv_to_cards`).
- La **pioche** se **recompose** en mélangeant la défausse quand elle est vide.
- L'**IA** joue à l'aveugle et **choisit la meilleure décision** (scoring) :
  attaquer la cible la plus vulnérable, **charger** pour percer un gros bouclier,
  **renforcer son bouclier ou baisser celui d'un adversaire trop protégé**, se
  soigner en danger. Elle est **agressive** (sinon la partie s'éternise).
- **Soin** : implémenté comme « **+valeur entière** de la carte si > 5 » (rend le
  soin puissant, donc la partie peut être longue si on en abuse). Réglage à
  confirmer si vous préfériez « +(valeur − 5) ».
