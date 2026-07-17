# Documentation technique — Cartes Classic

> Application de jeux de cartes en Python / pygame, regroupant plusieurs modes
> derrière un menu commun. Ce document décrit l'architecture, les modules, le
> cycle de rendu et la marche à suivre pour ajouter un mode.
>
> _Les règles de chaque mode sont documentées séparément dans
> [`docs/regles/`](regles/)._

---

## 1. Vue d'ensemble

| | |
|---|---|
| **Langage** | Python 3.13 |
| **Bibliothèque** | pygame 2.6.1 |
| **Résolution logique** | 1280 × 820 (mise à l'échelle en plein écran) |
| **Point d'entrée** | [`main.py`](../main.py) |
| **Lancement** | `pip install pygame` puis `python main.py` |

Modes de jeu :

| Mode | Fichier | État |
|------|---------|------|
| Solitaire (Klondike) | `game/solitaire.py` | ✅ jouable |
| Le Président | `game/president.py` | ✅ jouable |
| Bataille | `game/bataille.py` | ✅ jouable |
| Le Pouilleux | `game/pouilleux.py` | ✅ jouable |
| FreeCell | — | 🔜 à venir |
| Spider | — | 🔜 à venir |

---

## 2. Arborescence

```
Jeu_de_carte_classic/
├── main.py                 Point d'entrée : App, boucle principale, plein écran
├── README.md               Présentation + règles résumées
├── docs/
│   ├── TECHNIQUE.md        Ce document
│   └── regles/             Règles détaillées, un fichier par mode
│       ├── README.md
│       ├── solitaire.md
│       ├── president.md
│       ├── freecell.md
│       ├── spider.md
│       └── bataille.md
└── game/
    ├── __init__.py
    ├── constants.py        Dimensions, couleurs, polices, enseignes
    ├── ui.py               Easing, dégradé feutre, ombres, Button
    ├── cards.py            Modèle Card + CardRenderer (rendu en cache)
    ├── scene.py            Scene (base) + SceneManager (transitions fondu)
    ├── menu.py             Menu de sélection + bouton plein écran
    ├── solitaire.py        Mode Solitaire
    ├── president.py        Le Président : scène (affichage/animations/saisie)
    ├── president_game.py   Le Président : moteur pur de règles (sans pygame)
    ├── ai.py               Bots — heuristiques + comptage de cartes
    ├── ai_mc.py            Bots — Monte-Carlo par déterminisation
    ├── bataille.py         Bataille (War) : scène + logique (avec jokers)
    └── pouilleux.py        Le Pouilleux (Old Maid) : scène + logique
```

---

## 3. Boucle applicative (`main.py`)

`App` initialise pygame, crée la fenêtre et détient le `SceneManager`.

- **Fenêtre** : `set_mode((1280, 820), pygame.SCALED | pygame.RESIZABLE)`.
  Le flag `SCALED` garde une résolution logique fixe : pygame met tout à
  l'échelle (souris comprise) quand la fenêtre est redimensionnée ou passée en
  plein écran.
- **Plein écran** : `toggle_fullscreen()` refait un `set_mode` avec ou sans
  `pygame.FULLSCREEN`. Touche **F11** ou bouton du menu. L'appel est protégé
  par `try/except` pour ne jamais planter sur un environnement non compatible.
- **Boucle** : `tick(120)` (dt plafonné à 50 ms), traitement des évènements,
  `manager.update(dt)`, `manager.draw(screen)`, `display.flip()`.

Navigation : `show_menu()`, `show_solitaire()`, `show_president()` créent la
scène et la passent au manager. Les instances de jeu courantes sont mémorisées
dans `app._solitaire` / `app._president` (utile pour les tests).

---

## 4. Système de scènes (`scene.py`)

### `Scene`
Classe de base. Méthodes surchargées par chaque écran :
`on_enter()`, `handle_event(event)`, `update(dt)`, `draw(surface)`.

### `SceneManager`
Maintient la scène courante et gère une **transition en fondu** au noir.

- `go(scene, instant=False)` : bascule immédiate ou via fondu.
- Phases : `idle` → `out` (fondu vers le noir) → `in` (fondu depuis le noir).
- Pendant `out`/`in`, les évènements ne sont pas transmis à la scène (évite les
  clics fantômes durant l'animation).

> ⚠️ **Piège de test** : après `show_xxx()`, la scène cible n'est affichée
> qu'une fois le fondu `out` terminé (~0,25 s). Pour capturer/valider un rendu,
> soit on fait tourner ~40 frames, soit on appelle directement `scene.draw()`.

---

## 5. Rendu des cartes (`cards.py`)

### `Card`
Modèle minimal (`__slots__`) : `suit`, `rank` (1 = As … 13 = Roi), `face_up`.
Propriétés `red` / `color` / `is_joker`. Les **jokers** (utilisés par la
Bataille) ont l'enseigne `C.JOKER` et un « rang » sentinelle `C.JOKER_RED` /
`C.JOKER_BLACK` servant uniquement à distinguer leur couleur ; le `CardRenderer`
leur dessine une face dédiée (étoile + mot « JOKER »). Les autres modes ne
distribuent pas de joker et sont donc inchangés.

### `CardRenderer`
Fabrique et **met en cache** les surfaces :

- `face(card)` : recto (coin rang + enseigne, symbole central, coin inversé),
  généré une fois par `(suit, rank)` puis réutilisé.
- `back` : dos bleu à motif de losanges.
- `slot` : emplacement vide (contour translucide).
- `shadow` : ombre douce pré-calculée.

Les enseignes utilisent les glyphes `♠ ♥ ♦ ♣` (police *Segoe UI Symbol*,
présente sous Windows). Taille configurable par instance (le menu utilise de
plus grandes cartes que le jeu).

---

## 6. UI & animations (`ui.py`)

- **Easing** : `ease_out_cubic`, `ease_in_out_cubic`, `ease_out_back`, `lerp`.
- **`draw_felt(surface)`** : fond feutre (dégradé vertical + vignette radiale),
  mis en cache par taille.
- **`soft_shadow(size, radius)`** : surface d'ombre portée.
- **`Button`** : rectangle arrondi avec animation de survol, liseré, ombre ;
  `handle(event)` renvoie `True` s'il a été cliqué (permet de court-circuiter la
  suite du traitement d'évènement).

Les animations de déplacement de cartes sont propres à chaque mode (petites
classes `Move` internes) mais suivent le même patron : position de départ,
cible calculée depuis la disposition courante, `t` normalisé, easing au rendu.

---

## 7. Détails d'implémentation par mode

### 7.1 Solitaire (`solitaire.py`)
- **Piles** : `Pile(kind, x, y)` avec `kind` ∈ {stock, waste, foundation,
  tableau}. `all_piles` = stock + waste + 4 fondations + 7 colonnes.
- **Distribution animée** : 28 cartes volent depuis le stock (décalage
  progressif), la dernière de chaque colonne se retourne à l'arrivée.
- **Disposition adaptative** : `fan_offsets(pile)` compresse l'éventail vertical
  si une colonne dépasse la hauteur disponible.
- **Glisser-déposer** : `hit_card` (test du dessus vers le dessous), `find_drop`
  (intersection maximale avec les zones de dépôt), `valid_drop` (règles).
- **Animations** : `Move` (vol vers destination), `Flip` (retournement en
  place), `Confetti` (victoire).
- **Undo** : `snapshot()` / `restore()` copient l'état complet des piles.
- **Auto-complétion** : bouton *Terminer* quand toutes les cartes sont face
  visible ; envoie les cartes aux fondations en cascade.

### 7.2 Le Président — moteur `president_game.py`
**Source unique de vérité des règles**, sans pygame. Utilisé par la scène ET
par l'IA Monte-Carlo. Points clés :
- **Nombre de joueurs** 4 à 8 (`N`) ; distribution **équitable** (`52 // N`,
  excédent retiré, Dames protégées) ou **complète** (tout distribué, les +1 sur
  des sièges voisins).
- **Sens du jeu** `direction` (±1), fixé à la 1re manche par les Dames (cœur =
  ouverture, pique = sens). `next_actor` avance de `direction` modulo N.
- **Ordre des forces** : `ORDER` (3 → 2) ; `ORDER_REV` en révolution.
- **Actions** `play` / `couche` / `forced_skip` mutent l'état et renvoient un
  `Result` (révolution, joueur qui finit, pli remporté, fin de manche). L'état
  avance immédiatement (la pause entre plis est purement visuelle).
- **`next_actor(frm)`** cherche le prochain joueur actif (hors finis / couchés /
  meneur) **en excluant `frm` lui-même** : si l'on « revient à soi », c'est que
  plus personne d'autre ne peut répondre → le pli se **ferme** (renvoie `None`).
  ⚠️ Sans cette exclusion, à **2 joueurs restants**, un joueur sauté en **main
  forcée** récupérait le tour et échappait à la règle (bug corrigé).
- **Titres** : `title_for(place)` gère les **neutres** (5+ joueurs).
- **Échange entre manches** (`_setup_exchange`) : renvoie l'action interactive de
  l'humain, ou `None`. Si l'humain est **gagnant** → `("give_back", loser, n)` (il
  choisit les cartes rendues, via `apply_human_gift`). Si l'humain est **perdant**
  (Trou / Vice-Trou) → `("give_best", winner, n)` : le prélèvement est **différé**
  et l'humain donne **lui-même** ses **n meilleures** cartes (imposées, via
  `human_best_gift` pour la surbrillance + `apply_human_give_best`) — pas de triche.
  Les paires 100 % IA sont réglées automatiquement (`_take_best` / `_give_lowest`).
- `clone()` (copie légère, partage les objets Card) et `legal_moves(idx)`
  (coups dédupliqués par (rang, taille)) servent au Monte-Carlo.
- **« À la volée »** (option) : `snap_moves(idx)` renvoie l'éventuel coup de
  fermeture **hors-tour** (3 simples égaux + la 4ᵉ ; ou une paire + la paire
  égale) ; `self_complete_move(idx)` gère le cas « je vole mon propre jeu »
  (2 simples égaux au sommet, à mon tour, je pose les 2 dernières d'un coup).
  Ces coups sont ensuite appliqués via le `play(idx, …)` habituel (le carré se
  ferme, main au poseur). Le moteur expose seulement ces **coups possibles** ;
  la course/réactivité et la préemption sont orchestrées par la scène.

### 7.3 Le Président — scène `president.py`
N'a plus de logique de règles : elle tient `self.g = PresidentGame(...)`, lit
l'état via des **propriétés** (`self.turn` → `self.g.turn`, …) et lui délègue
les actions. Elle gère l'écran de configuration (phase `setup`), l'animation des
cartes (`Move`), la pause entre plis, le rythme des IA (`think_t`), l'écran
d'échange, et le rendu (table en cercle, « pods » IA compacts).

**Écran de configuration** (`_layout_setup` / `_draw_setup`) : deux
**compartiments** (« PARTIE », « ADVERSAIRES & RÈGLES ») en panneaux arrondis
translucides avec en-tête coloré. Chaque option est une **ligne** = titre
explicite + description (`self.dfont`) + bouton-bascule **court** (« Normale » /
« Forte », etc.) **codé couleur** selon l'état (`_style_setup_buttons` : bleu /
rouge / vert / or / gris). Le layout est calculé une fois par frame (panneaux,
séparateurs, textes, positions des boutons stockés dans `self._panels` /
`self._texts` / `self._dividers`) et partagé entre `_layout_setup` (rects
cliquables) et `_draw_setup` (rendu). Le Pouilleux suit le même patron (un
compartiment « RÉGLAGES DE LA PARTIE »).

**Bandeau « CLASSEMENT »** (`_draw_roles_panel`) : bandeau **horizontal** placé
dans la bande libre **sous le tas central** (entre le tas et la main) — une zone
jamais occupée par un pod, quel que soit le nombre de joueurs (l'anneau des pods
entoure le centre : aucune colonne verticale à gauche/droite n'est libre pour
tous les effectifs, d'où le choix horizontal). Une **colonne par rôle clé**
(Président, Vice-Président, Vice-Trou, Trou du cul) avec pastille colorée
(`title_col`) ; à partir de `places` (inversé en `place → idx`), le **nom**
remplace le « ? » dès qu'un joueur atteint la place. À 5+ joueurs, une colonne
**Neutres** compacte affiche un compteur `faits / total` (les noms des neutres
restent lisibles sur leurs pods). Compact (une ligne) pour tenir sous le tas sans
empiéter sur les cartes jouées ni la main. **Repliable** : l'**en-tête**
« CLASSEMENT » (avec chevron triangle) est cliquable (`_roles_header`,
`roles_open`) et **déroule / replie** le corps avec une **animation** (`roles_anim`
lissé dans `update`, dévoilement par clip depuis le haut + fondu `BLEND_RGBA_MULT`).
Fond volontairement **translucide** (alpha faible) pour ne pas masquer le feutre.

**Sélection : mise au point + bouton flottant** — dans `_draw_human_hand`, dès
qu'au moins une carte est sélectionnée, les **autres cartes deviennent
transparentes** (même `BLEND_RGBA_MULT` que les cartes injouables). Un petit
bouton **flottant** (`btn_place`, positionné par `_floating_button` /
`_place_floating`) apparaît **centré au-dessus** de la/des carte(s) sélectionnée(s) :
« **Poser** » à son tour (→ `human_play`) ou « **Donner** » à l'échange
(→ `finish_exchange`). Le Pouilleux a le même bouton flottant « **Défausser** »
(`btn_discard_float` / `_place_discard_float`) au-dessus de la paire cochée en
défausse manuelle (→ `_manual_discard`).

**Orchestration « à la volée »** (option `a_la_volee`, bouton sur l'écran de
config, + réglages `snap_reactivity` et `self_steal` affichés quand elle est
activée) : après chaque `_schedule`, `_open_snaps()` détermine l'**unique**
joueur pouvant fermer hors-tour (`snap_moves`). On n'ouvre les snaps que pendant
le tour d'une **IA** (jamais quand l'humain réfléchit, sinon une IA fermerait
toujours avant lui). Le snap est appliqué par `_do_snap` → `_do_play`, qui
**préempte** l'action en attente (annule le `pending` et invalide un calcul
Monte-Carlo en cours via un `_mc_token`).

- **Réactivité des bots** (`snap_reactivity`) : `"none"` → les IA ne volent pas
  et le snappeur **humain** met le tour en **pause** (`snap_hold`, temps illimité,
  bouton **« Ne pas voler »** → `_decline_snap`, occasion mémorisée dans
  `_snap_declined` pour ne pas re-proposer) ; `"slow"` → délai IA ~3 s (et
  fenêtre humaine de 3 s) ; `"instant"` → délai IA quasi nul. Le délai IA est
  **préservé** tant que la même occasion perdure (clé `_snap_key`).
- **« Voler son propre jeu »** (`self_steal`, OFF par défaut) : n'autorise le
  cas « 2 dernières cartes d'un coup à son tour » (`self_complete_move`) que s'il
  est activé — pour l'humain (sélection de 2 cartes) comme pour l'IA forcée.

⚠️ Le Monte-Carlo (`ai_mc`) **ne simule pas** l'à-la-volée dans ses rollouts
(approximation acceptée : ils jouent en-tour via l'heuristique).

### 7.4 Le Président — IA des bots
Deux niveaux, choisis sur l'écran de configuration (« IA : Normale / Forte ») :
- **`ai.py`** (heuristique + comptage de cartes) : joue la plus basse carte
  légale, finit dès que possible, se débarrasse de sa carte de fermeture avant
  d'être forcé de finir dessus. `build_view(game, idx)` prépare la vue de
  comptage (`unseen`).
- **`ai_mc.py`** (Monte-Carlo par déterminisation) : pour chaque coup candidat,
  tire des mains adverses plausibles et simule la fin de manche avec
  l'heuristique, puis garde la meilleure place moyenne. Optimisé :
  raccourci sur décision triviale, candidats dédupliqués/pré-filtrés,
  **déterminisations partagées entre candidats** (common random numbers),
  rollouts par l'heuristique, `clone()` léger. Mesuré **plus fort** que
  l'heuristique (place moyenne ~1.0 contre 3 heuristiques, vs 1.5 neutre).
  ~0.5 s/décision, **calculé dans un thread de fond** (`_mc_launch`) pendant le
  délai de réflexion de l'IA → aucune latence perçue (le résultat est appliqué
  quand la réflexion est écoulée et le calcul terminé).
- **État d'un pli** : `top_combo` (combo à battre), `required` (taille),
  `run_len` (série de simples égaux), `forcing_lifted`, `couched`, `leader`.
- **État de manche** : `revolution` (persiste toute la manche), `places` /
  `avail` (attribution gloutonne des rangs), `prev_ranking` (pour l'échange).
- **Machine à états** : `phase` ∈ {exchange, playing, anim, pause, round_over}.
  - `_schedule(idx)` décide de l'action automatique (main forcée, auto-passe,
    tour d'IA) ou attend l'humain (`pending = None`).
  - `_execute` applique l'action après un court délai (`think_t`).
  - `play_combo` → animation → `_after_play` → résolution (`resolve` /
    `_trick_over`).
- **IA des bots** (`game/ai.py`, étape 1) : heuristiques + **comptage de
  cartes**. La scène maintient `played_counts` (cartes révélées) ; `ai_pick`
  construit une vue (`unseen` = 4 − en main − jouées, main groupée, ordre,
  fermeture…) et délègue à `ai.choose`. Stratégie : jouer la plus basse carte
  légale (conserve les 2/3), finir dès que possible, et **se débarrasser de sa
  carte de fermeture avant d'être forcé de finir dessus**. Mesuré nettement plus
  fort que l'IA gloutonne précédente (place moyenne ~1.18 vs ~1.82 en duel à 4).
  _Étape 2 prévue : Monte-Carlo par déterminisation (voir mémoire projet)._

Les **règles complètes** (égalité, main forcée, fermeture, révolution,
pénalités, échange) sont dans [`docs/regles/president.md`](regles/president.md).

### 7.5 Bataille (`bataille.py`)
Mode autonome à 2 (humain contre ordinateur), **sans décision** (le hasard
tranche). État par joueur : une **pioche** (`deque` face cachée) et des **gains**
(liste) ; `_draw_card` recompose la pioche à partir des gains **mélangés** quand
elle est vide (évite les boucles). Le paquet compte **54 cartes** (52 + 2
jokers, `card_value` : As = 14, joker = 20, jokers **égaux**).

Machine à états pilotée par des lots d'animations (`Fly`, avec retournement
dos→face) et un callback `_after` :
`idle` → `anim` (retourne les 2 cartes) → `showdown` (pause pour **voir** les
cartes et le résultat, clic pour accélérer) → `anim` (ramassage vers les gains
du vainqueur) → `idle`. Égalité → `_war` : une carte cachée + une visible
rejoignent le **pot** (`self.pot`), qui revient au vainqueur ; si un joueur ne
peut pas fournir la carte visible, il perd la bataille. Fin : un joueur a 0
carte, ou borne `MAX_BATTLES` (4000) tranchée au nombre de cartes. Le rendu
montre les 2 pioches, les 2 tas de gains (avec compteurs), le pot (« Enjeu »),
les cartes en duel et un message. Boutons **Auto** / **Nouvelle partie** /
**Menu** ; commandes clic/`Espace` (avancer), `A` (auto), `N` (rejouer).
Voir [`docs/regles/bataille.md`](regles/bataille.md).

### 7.6 Le Pouilleux (`pouilleux.py`)
Mode **interactif** à 2–8 joueurs (humain = siège 0, IA autonomes), autonome (la
logique et le rendu vivent dans la scène, sur le patron de `bataille.py`).

- **Appariement** `pair_key(card) = (rank, red)` : deux cartes s'apparient si même
  rang **et** même couleur. Chaque main est invariante — jamais deux cartes de
  même clé (défausse immédiate).
- **Deck** : 52 cartes moins une. Version **classique** → on retire le Valet de
  Trèfle (l'orpheline est le Valet de Pique, connu) ; version **mystère** → on
  retire une carte au hasard (orpheline = son partenaire de couleur, inconnu).
  51 cartes = 25 paires + 1 orpheline.
- **Mise en place** : distribution round-robin, `_discard_initial` retire les
  paires de départ, les mains vides sont « sauvées » d'emblée, premier joueur
  tiré au sort.
- **Tour** : `_victim(cur)` = joueur actif précédent (sens fixe) ; on pioche une
  carte chez lui. `_do_draw(k)` anime le vol (`Fly`, retournement si l'humain
  pioche, face visible si l'IA pioche chez l'humain, sinon dos), `_after_draw`
  ajoute la carte et défausse la paire éventuelle, `_post_turn` marque les
  « sauvés » et passe au `_next_active`.
- **Interaction** : au tour de l'humain, l'éventail face cachée de la victime est
  affiché au centre (`_zone_slots`) et cliquable ; les IA piochent au hasard
  après un court délai (`think_t`).
- **Défausse `auto` / `manuel`** (`self.mode`, bouton sur l'écran de config) :
  - **Auto** (défaut) : comportement historique — les paires (de départ **et**
    après pioche) partent toutes seules.
  - **Manuel** : seul l'humain écarte lui-même ses paires (les IA restent
    automatiques). Deux moments dédiés, mêmes gestes : les paires de la main
    humaine sont **surlignées** (`_paired_ids`), on **coche** les 2 cartes
    (`_toggle_select`) puis on clique la **pile de défausse** (`_manual_discard`,
    anime les cartes vers `DISCARD` et incrémente `discard_count`).
    - Phase **`ready`** (mise en place) : à la distribution, la main humaine
      **n'est pas** auto-défaussée ; on écarte ses paires puis on clique
      **« Prêt »** (`_ready_done`, actif seulement quand `_paired_ids()` est vide)
      → tirage du premier joueur et début des tours.
    - Phase **`discard`** (après avoir pioché) : `_after_draw` bascule en
      `discard` au lieu de défausser ; on écarte son éventuel double puis on
      clique **« Donner »** (`_donner_done`, même garde) → `_post_turn`.
  - `_discarding` neutralise l'affichage de l'éventail-victime au centre pendant
    l'animation de défausse manuelle ; les boutons `Prêt`/`Donner` s'activent via
    leur `enabled` dans `update`.
- **Réordonnancement de sa main** (les deux modes) : la main humaine n'est **plus
  triée automatiquement** (seul le tri initial à la distribution subsiste ; les IA
  restent triées). L'humain arrange ses cartes par **glisser-déposer**
  (`_press_card`/`_drag_card`, seuil de 8 px pour distinguer clic court et glisser,
  `_drop_drag` réinsère à l'index le plus proche) ou via le bouton **Mélanger la
  main** (`_shuffle_hand`, `random.shuffle`). Autorisé **hors de son tour**
  seulement (`_reorder_allowed` : phases `ready` / `give`, ou `wait` quand
  `cur != 0`) — pas pendant sa pioche ni au moment de « Donner » sa défausse. Tant
  qu'une carte est saisie, l'IA **patiente** (le décompte `think_t` est gelé). Un
  clic court sert toujours à (dé)cocher pour la défausse manuelle.
  - **Écart d'insertion animé** : pendant un glisser, `_hand_layout` réserve un
    emplacement (largeur d'une carte) à l'index d'insertion (`_insert_index`, même
    calcul que `_drop_drag`) ; les cartes voisines **s'écartent** pour l'ouvrir et
    un **emplacement cible surligné** (`_hand_ph`) montre où la carte va se poser.
    Le déplacement est **lissé** frame par frame (`_animate_hand`, positions
    animées `_card_x` → `_hand_draw`), utilisé aussi à l'ajout/défausse de cartes.
  - **Les IA rebattent aussi leur main** (symétrie avec l'humain) : une IA-victime
    est `random.shuffle`-ée dans `_begin_turn` **juste avant qu'on pioche chez
    elle**, et une IA rebat sa main **après chaque pioche** conservée (`_after_draw`,
    shuffle au lieu de sort) → plus d'ordre trié exploitable par un humain attentif.
- **Accord avant de se faire piocher** (phase `give`, les deux modes) : quand un
  voisin va piocher chez l'humain (`cur != 0` **et** `victim == 0`), `_begin_turn`
  bascule en `give` au lieu de `wait` — l'IA **ne pioche pas** tant que l'humain
  n'a pas cliqué **« Donner »** (`_give_consent`, qui lance alors la pioche
  aléatoire du voisin). Cela lui laisse le temps de mélanger / réordonner sa main.
- **Fin** : quand ≤ 1 joueur a des cartes, le détenteur de l'orpheline est le
  Pouilleux. L'écran de fin révèle l'orpheline et l'ordre des « sauvés ».

Règles détaillées : [`docs/regles/pouilleux.md`](regles/pouilleux.md).

---

## 8. Ajouter un nouveau mode

1. Créer `game/<mode>.py` avec une classe `Scene` (voir `solitaire.py` comme
   gabarit) : `handle_event`, `update`, `draw`.
2. Réutiliser `CardRenderer`, `ui.draw_felt`, `ui.Button`, les easing.
3. Exposer le mode dans `main.py` : ajouter `show_<mode>()`.
4. L'activer dans `game/menu.py` : passer `available=True` et l'action dans la
   liste `specs`.
5. Documenter ses règles dans `docs/regles/<mode>.md` et mettre à jour
   l'index `docs/regles/README.md` et le tableau de ce document.

---

## 9. Commandes & raccourcis

**Global** : `F11` plein écran · `Échap` retour menu.

**Solitaire** : glisser-déposer · double-clic → fondation · clic sur la pioche ·
`Espace` piocher · `U` annuler · `N` nouvelle partie.

**Le Président** : clic pour (dé)sélectionner · `Entrée` Jouer · `Espace`
Coucher. Avec l'option **à la volée**, le bouton Jouer / `Entrée` / clic centre
sert aussi à **fermer hors-tour** quand une occasion s'ouvre.

**Bataille** : clic / `Espace` avancer (ou accélérer le résultat) · `A` mode
auto · `N` nouvelle partie.

---

## 10. Tests

Les modes sont testables **sans fenêtre** via le pilote SDL « dummy » :

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python - <<'PY'
from main import App
app = App(); app.show_president(); sc = app._president
for _ in range(200): sc.update(1/60)
PY
```

On peut piloter une partie complète en boucle (voir les scénarios de
validation), forcer des états précis, puis vérifier les invariants (52 cartes
conservées, 4 places attribuées, absence de boucle infinie) et sauver un rendu
avec `pygame.image.save(app.screen, "out.png")`.

---

_Dernière mise à jour : **Bouton flottant « Poser » + mise au point de la
sélection** (Président & Pouilleux) — les cartes non sélectionnées deviennent
transparentes (comme les injouables) et un petit bouton centré (« Poser » /
« Donner » / « Défausser ») s'affiche juste au-dessus des cartes choisies
(`btn_place` / `_floating_button`, `btn_discard_float` / `_place_discard_float`).
Auparavant : **Don obligatoire du perdant (Président)** — quand l'humain est Trou
du cul / Vice-Trou, il donne **lui-même** ses meilleures cartes, imposées et en
**surbrillance** (verrouillées, pas de triche) via un écran dédié (`give_best` :
`_setup_exchange` différé, `human_best_gift` / `apply_human_give_best`, bouton
« Donner mes meilleures cartes »). Auparavant : **Classement (Président)
repliable, plus étroit et translucide** : en-tête « CLASSEMENT » cliquable qui déroule/replie le bandeau
avec animation (`roles_open` / `roles_anim`, clip + fondu) ; largeur réduite
(colonnes 96 px) et fond translucide. Auparavant : **Classement en bandeau
horizontal** sous le tas central (`_draw_roles_panel`) : l'ancien panneau vertical
à gauche se superposait aux pods dès 6 joueurs, et décaler le plateau a été
rejeté ; le bandeau horizontal occupe la bande libre entre le tas et la main
(jamais un pod), une colonne par rôle clé + compteur « Neutres » à 5+ joueurs.
Auparavant :
**Refonte des écrans de configuration** (Président &
Pouilleux) : options regroupées en **compartiments** (panneaux à en-tête coloré),
chaque réglage avec un **titre explicite** + description + bouton-bascule court
**codé couleur** selon l'état, plus d'espace et de hiérarchie (`_layout_setup` /
`_draw_setup` / `_style_setup_buttons`). Auparavant : **Les IA du Pouilleux
rebattent aussi leur main** (`_begin_turn` avant qu'on pioche chez elles +
`_after_draw`) pour rester imprévisibles. Auparavant : **Deux améliorations UX** —
(1) Le Pouilleux : pendant
le glisser-déposer de la main, un **emplacement cible surligné** s'ouvre et les
cartes voisines **s'écartent** pour montrer où la carte va se poser (déplacement
lissé, `_hand_layout` / `_animate_hand` / `_hand_ph`). (2) Le Président : **tableau
« CLASSEMENT »** à gauche (`_draw_roles_panel`) listant les rôles à venir ; le nom
remplace le « ? » dès qu'un joueur finit (dessiné sous les pods pour les garder
lisibles). Auparavant : **Le Pouilleux — accord « Donner » + bouton Mélanger** :
avant qu'un voisin ne pioche chez l'humain, le jeu attend son accord (phase
`give`, bouton **Donner**, dans les deux modes) pour lui laisser le temps de
réorganiser sa main ; ajout d'un bouton **Mélanger la main** (`_shuffle_hand`).
Auparavant : **réordonnancement de la main** : la main
humaine n'est plus triée d'office ; on arrange ses cartes par glisser-déposer
hors de son tour (`_reorder_allowed`, IA gelée pendant la manipulation) pour
casser la prévisibilité de l'ordre. Auparavant : **défausse manuelle** : option
`auto` / `manuel` sur l'écran de config. En manuel, l'humain écarte lui-même ses
paires (surbrillance + clic sur les cartes puis sur la pile de défausse) à la
mise en place (phase `ready`, bouton **Prêt**) et après chaque pioche (phase
`discard`, bouton **Donner**) ; les IA restent automatiques.
Auparavant : **nouveau mode Le Pouilleux** (`pouilleux.py`, Old Maid
français interactif 2–8 joueurs, versions classique/mystère ; tuile de menu
activée, fiche de règles ajoutée).
Auparavant : **Président** — affichage du rôle du joueur humain dès
qu'il pose sa dernière carte (toast « vous êtes … » + titre coloré permanent dans
l'encart « Vous », sans attendre la fin de manche).
Auparavant : **nouveau mode Bataille** (`bataille.py`, 54 cartes avec
2 jokers ; support joker ajouté à `Card`/`CardRenderer`). Auparavant : réglages
de l'« à la volée » (réactivité des bots none/3 s/instant + bouton « Ne pas
voler », sous-option « Voler son propre jeu ») et **correctif** de la main forcée
à 2 joueurs (`next_actor` exclut `frm`).
Auparavant : option « à la volée » du Président (fermeture d'un carré hors-tour ;
`snap_moves`/`self_complete_move` moteur, orchestration + préemption scène) ;
plein écran ; refonte des règles du Président (révolution par carré / persistante
/ contre-révolution, égalité sur les doubles, bouton « Coucher », choix sur main
forcée)._
