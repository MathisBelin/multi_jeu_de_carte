# Documentation technique — Cartes Classic

> Application de jeux de cartes en Python / pygame, regroupant plusieurs modes
> derrière un menu commun. Ce document décrit l'architecture, les modules, le
> cycle de rendu et la marche à suivre pour ajouter un mode.
>
> _Les règles de chaque mode sont documentées séparément dans
> [`docs/regles/`](regles/). L'historique des changements est dans `git log`._

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
| Le Bouclié | `game/bouclie.py` | ✅ jouable |
| FreeCell | — | 🔜 à venir |
| Spider | — | 🔜 à venir |

---

## 2. Arborescence

```
Jeu_de_carte_classic/
├── main.py                 Point d'entrée : App, boucle principale, plein écran
├── prompt.md               Prompt de reprise (contexte pour une nouvelle session)
├── README.md               Présentation + règles résumées
├── docs/
│   ├── TECHNIQUE.md        Ce document
│   └── regles/             Règles détaillées, un fichier par mode
│       ├── README.md
│       ├── solitaire.md
│       ├── president.md
│       ├── pouilleux.md
│       ├── bataille.md
│       ├── freecell.md
│       └── spider.md
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
    ├── pouilleux.py        Le Pouilleux (Old Maid) : scène + logique
    └── bouclie.py          Le Bouclié (élimination boucliers/PV) : scène + logique
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

Navigation : `show_menu()`, `show_solitaire()`, `show_president()`,
`show_bataille()`, `show_pouilleux()`, `show_bouclie()` créent la scène et la
passent au manager. Les instances courantes sont mémorisées dans
`app._solitaire` / `app._president` / `app._bataille` / `app._pouilleux` /
`app._bouclie` (utile pour les tests headless).

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
- **`Button`** : rectangle arrondi avec animation de survol, liseré, ombre.
  `update(dt, mouse)` anime le survol ; `handle(event)` renvoie `True` s'il a été
  cliqué (permet de court-circuiter la suite du traitement d'évènement) ; `draw`
  et le hit-test utilisent `self.rect` — on peut donc **repositionner / recolorer**
  un bouton par frame (`rect`, `fill`, `label`, `text_col`).

Les animations de déplacement de cartes sont propres à chaque mode (petites
classes `Move` / `Fly` internes) mais suivent le même patron : position de
départ, cible calculée depuis la disposition courante, `t` normalisé, easing au
rendu.

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
**Source unique de vérité des règles**, sans pygame. Utilisé par la scène ET par
l'IA Monte-Carlo. Ne fait aucun rendu, aucune animation, aucun minuteur : les
actions mutent l'état **immédiatement** (la pause entre plis est purement
visuelle, gérée par la scène).

- **Mise en place** (`new_round`) : 2 à 10 joueurs (`N`) ; distribution
  **équitable** (`52 // N`, excédent retiré, Dames protégées) ou **complète**
  (tout distribué, les +1 sur des sièges voisins `extra_block`).
- **Sens du jeu** `direction` (±1), fixé à la 1re manche par les Dames (cœur =
  ouverture, pique = sens). `next_actor` avance de `direction` modulo N.
- **Ordre des forces** : `ORDER` (3 → 2) ; `ORDER_REV` en révolution (`order()` /
  `power()` / `closer_rank()` en dépendent).
- **Actions** `play` / `couche` / `forced_skip` renvoient un `Result`
  (`revolution_toggled`, `finished=(idx, place)`, `trick_closed`, `winner`,
  `round_over`).
- **`next_actor(frm)`** cherche le prochain joueur actif (hors finis / couchés /
  meneur) **en excluant `frm` lui-même** : si l'on « revient à soi », plus
  personne d'autre ne peut répondre → le pli se **ferme** (renvoie `None`).
  ⚠️ Sans cette exclusion, à **2 joueurs restants**, un joueur sauté en **main
  forcée** récupérait le tour et échappait à la règle (bug corrigé).
- **État d'un pli** : `top_combo` (combo à battre), `required` (taille),
  `run_len` / `run_cards` (série de simples/cartes égales), `forcing_lifted`,
  `couched`, `leader`. **État de manche** : `revolution` (persiste toute la
  manche), `places` (idx → place) / `avail` (rangs restants), `ranking` /
  `prev_ranking`. `title_for(place)` gère les **neutres** (5+ joueurs) et, à
  **moins de 4 joueurs**, le schéma de titres `small_roles` (`"ends"` =
  Président/Trou · `"vices"` = Vice-Prés/Vice-Trou ; Neutre au milieu à 3),
  répercuté sur l'échange (`_setup_exchange` : 2 cartes pour les extrêmes,
  1 pour les Vices).
- **Échange entre manches** (`_setup_exchange`) : renvoie l'action interactive de
  l'humain, ou `None`.
  - Humain **gagnant** → `("give_back", loser, n)` : il **choisit** les cartes
    rendues (via `apply_human_gift`) ; les meilleures du perdant IA ont déjà été
    prises.
  - Humain **perdant** (Trou / Vice-Trou) → `("give_best", winner, n)` : le
    prélèvement est **différé** ; l'humain donne **lui-même** ses **n meilleures**
    cartes, **imposées** (`human_best_gift` pour la surbrillance,
    `apply_human_give_best` pour l'appliquer) — pas de triche possible.
  - Paires 100 % IA : automatique (`_take_best` / `_give_lowest`).
- **Support Monte-Carlo** : `clone()` (copie légère, partage les objets Card) et
  `legal_moves(idx)` (coups dédupliqués par (rang, taille), `None` = se coucher).
- **« À la volée »** (option) : `snap_moves(idx)` renvoie l'éventuel coup de
  fermeture **hors-tour** (3 simples égaux + la 4ᵉ ; ou une paire + la paire
  égale) ; `self_complete_move(idx)` gère « je vole mon propre jeu » (2 simples
  égaux au sommet, à mon tour, poser les 2 dernières d'un coup). Ces coups sont
  appliqués via le `play(idx, …)` habituel. Le moteur expose seulement les
  **coups possibles** ; la course / réactivité / préemption est orchestrée par
  la scène.

Les **règles complètes** (égalité, main forcée, fermeture, révolution, pénalités,
échange, à la volée) sont dans [`docs/regles/president.md`](regles/president.md).

### 7.3 Le Président — scène `president.py`
Aucune logique de règles : elle tient `self.g = PresidentGame(...)`, lit l'état
via des **propriétés** (`self.turn` → `self.g.turn`, …) et lui délègue les
actions. Elle gère la configuration, les animations, le rythme des IA, l'écran
d'échange et le rendu (table en cercle, « pods » IA compacts).

**Machine à états** (`phase` ∈ {`setup`, `exchange`, `playing`, `anim`, `pause`,
`round_over`}) :
- `_schedule(idx)` décide de l'action automatique (main forcée, auto-passe, tour
  d'IA) ou attend l'humain (`pending = None`) ; ouvre les éventuels snaps.
- `_execute(pending, idx)` applique l'action en attente après le délai `think_t`.
- Un coup passe par `_do_play(idx, cards)` → animation `Move` → `_after_play_anim`
  → résolution (`_after_action` : pli fermé → `pause` puis `_schedule`, sinon on
  enchaîne). L'IA en mode « Forte » calcule en thread pendant `think_t` (voir 7.4).

**Écran de configuration** (`_layout_setup` / `_draw_setup`) : deux
**compartiments** (« PARTIE », « ADVERSAIRES & RÈGLES ») en panneaux arrondis
translucides à en-tête coloré. Chaque option est une **ligne** = titre explicite
+ description (`self.dfont`) + bouton-bascule **court** **codé couleur** selon
l'état (`_style_setup_buttons`). Le layout est calculé une fois par frame
(panneaux / textes / séparateurs / positions de boutons dans `self._panels` /
`self._texts` / `self._dividers`) et partagé entre `_layout_setup` (rects
cliquables) et `_draw_setup` (rendu). Le Pouilleux suit le même patron (un
compartiment « RÉGLAGES DE LA PARTIE »).

**Bandeau « CLASSEMENT »** (`_draw_roles_panel`) : bandeau **horizontal** placé
dans la bande libre **sous le tas central** (entre le tas et la main) — une zone
jamais occupée par un pod, quel que soit l'effectif (l'anneau des pods entoure le
centre : aucune colonne verticale gauche/droite n'est libre pour tous les
effectifs, d'où le choix horizontal ; décaler le plateau a été essayé puis
**rejeté**). Une **colonne par rôle clé** (Président, Vice-Président, Vice-Trou,
Trou du cul) avec pastille colorée (`title_col`) ; le **nom** remplace le « ? »
dès qu'un joueur atteint la place (`places` inversé en `place → idx`). À 5+
joueurs, une colonne **Neutres** affiche un compteur `faits / total`. Compact
(une ligne), **repliable** : l'en-tête (chevron triangle) est cliquable
(`_roles_header`, `roles_open`) et déroule/replie le corps avec **animation**
(`roles_anim` lissé, dévoilement par clip depuis le haut + fondu
`BLEND_RGBA_MULT`). Fond **translucide** pour laisser voir le feutre.

**Sélection : mise au point + bouton flottant** (`_draw_human_hand`) :
- **En jeu**, on ne grise **que** les cartes **injouables** (rang absent de
  `_active_legal_ranks`) — jamais celles qu'on peut encore jouer.
- **À l'écran d'échange**, les cartes non sélectionnées deviennent
  **transparentes** (`BLEND_RGBA_MULT`) pour concentrer l'attention sur le don.
- Un petit bouton **flottant** (`btn_place`, positionné par `_floating_button` /
  `_place_floating`) apparaît **centré au-dessus** des cartes sélectionnées :
  « **Poser** » à son tour (→ `human_play`) ou « **Donner** » à l'échange
  (→ `finish_exchange`).

**Orchestration « à la volée »** (option `a_la_volee` + réglages `snap_reactivity`
et `self_steal`) : après chaque `_schedule`, `_open_snaps()` détermine l'**unique**
joueur pouvant fermer hors-tour (`snap_moves`). Les snaps ne s'ouvrent que
pendant le tour d'une **IA** (jamais quand l'humain réfléchit, sinon une IA
fermerait toujours avant lui). `_do_snap` → `_do_play` **préempte** l'action en
attente (annule `pending` et invalide un calcul Monte-Carlo via `_mc_token`).
- **Réactivité** (`snap_reactivity`) : `"none"` → les IA ne volent pas et le
  snappeur **humain** met le tour en pause (`snap_hold`, temps illimité, bouton
  **« Ne pas voler »** → `_decline_snap`, occasion mémorisée dans `_snap_declined`) ;
  `"slow"` → délai IA ~3 s ; `"instant"` → quasi nul. Délai **préservé** tant que
  la même occasion perdure (`_snap_key`).
- **« Voler son propre jeu »** (`self_steal`, OFF par défaut) : n'autorise le cas
  « 2 dernières cartes d'un coup à son tour » (`self_complete_move`) que s'il est
  activé — humain (sélection de 2 cartes) comme IA forcée.

> ⚠️ Le Monte-Carlo (`ai_mc`) **ne simule pas** l'à-la-volée dans ses rollouts
> (approximation acceptée : les rollouts jouent en-tour via l'heuristique).

### 7.4 Le Président — IA des bots (`ai.py`, `ai_mc.py`)
Deux niveaux, choisis sur l'écran de configuration (« IA : Normale / Forte »).
La scène expose la vue de comptage : `played_counts` (cartes révélées) alimente
`ai.build_view(game, idx)` (`unseen` = 4 − en main − jouées, main groupée,
ordre, carte de fermeture…).

- **`ai.py` — Normale (heuristique + comptage)** : joue la plus basse carte
  légale (conserve 2 / 3), finit dès que possible, et **se débarrasse de sa carte
  de fermeture avant d'être forcé de finir dessus** (la grosse leçon : les ajouts
  « économiser / passer » avaient régressé ; cette règle d'endgame fait le gain).
  Mesuré nettement plus fort que l'ancienne IA gloutonne (~1.18 vs ~1.82 à 4).
- **`ai_mc.py` — Forte (Monte-Carlo par déterminisation)** : pour chaque coup
  candidat, tire des mains adverses plausibles et simule la fin de manche avec
  l'heuristique, garde la meilleure place moyenne. Optimisé : raccourci sur
  décision triviale, candidats dédupliqués / pré-filtrés, **déterminisations
  partagées entre candidats** (common random numbers), rollouts par l'heuristique,
  `clone()` léger. Mesuré **dominant** (place moyenne ~1.0 contre 3 heuristiques).
  ~0.5 s/décision **calculé dans un thread de fond** (`_mc_launch`) pendant le
  délai de réflexion → aucune latence perçue ; le résultat est appliqué quand
  `think_t` est écoulé **et** le thread terminé (jeton `_mc_token` pour ignorer un
  résultat périmé, ex. après un snap). `choose_mc` ne mute pas `self.g` (il clone)
  → thread sûr.

### 7.5 Bataille (`bataille.py`)
Mode autonome à 2 (humain contre ordinateur), **sans décision** (le hasard
tranche). État par joueur : une **pioche** (`deque` face cachée) et des **gains**
(liste) ; `_draw_card` recompose la pioche à partir des gains **mélangés** quand
elle est vide (évite les boucles). Le paquet compte **54 cartes** (52 + 2
jokers, `card_value` : As = 14, joker = 20, jokers **égaux**).

Machine à états pilotée par des lots d'animations (`Fly`, avec retournement
dos→face) et un callback `_after` :
`idle` → `anim` (retourne les 2 cartes) → `showdown` (pause pour **voir** les
cartes et le résultat, clic pour accélérer) → `anim` (ramassage vers les gains du
vainqueur) → `idle`. Égalité → `_war` : une carte cachée + une visible rejoignent
le **pot** (`self.pot`), qui revient au vainqueur ; si un joueur ne peut pas
fournir la carte visible, il perd la bataille. Fin : un joueur a 0 carte, ou borne
`MAX_BATTLES` (4000) tranchée au nombre de cartes.
Voir [`docs/regles/bataille.md`](regles/bataille.md).

### 7.6 Le Pouilleux (`pouilleux.py`)
Mode **interactif** à 2–10 joueurs (humain = siège 0, IA autonomes), autonome (la
logique et le rendu vivent dans la scène, sur le patron de `bataille.py`).
`_layout_seats` dispose les joueurs **en cercle** (ellipse `EC`/`RX`/`RY`) :
l'humain en bas, les adversaires sur l'**arc supérieur** (le centre-bas reste
libre) ; effectifs 2→10 vérifiés sans chevauchement ni clip. La **défausse** est
au **centre** de l'anneau. Le **titre** indique la version (« — Classique » /
« — Mystère »).
- **Cartes du voisin « devant moi »** : quand c'est le tour de l'humain,
  `_launch_zone_in` **anime** l'arrivée des cartes (face cachée) du voisin depuis
  son pod jusqu'à la **zone** (`_zone_slots`, centre-bas) où on les pioche ;
  pendant l'animation (`phase == "anim"`, `Fly`) `_draw_center` masque les cartes
  en vol puis les révèle une fois posées, avant de passer en `wait`. À la pioche
  (`_do_draw`, `cur == 0`), la carte choisie vole **vers l'humain** et **les
  cartes restantes repartent chez le voisin** (mêmes `Fly`, symétrie).

- **Appariement** `pair_key(card) = (rank, red)` : deux cartes s'apparient si même
  rang **et** même couleur. Une main ne conserve jamais deux cartes de même clé.
- **Deck** : 52 cartes moins une. Version **classique** → on retire le Valet de
  Trèfle (l'orpheline est le Valet de Pique, connu) ; version **mystère** → on
  retire une carte au hasard (orpheline = son partenaire de couleur, inconnu).
  51 cartes = 25 paires + 1 orpheline.
- **Tour** : `_victim(cur)` = joueur actif précédent (sens fixe) ; on pioche une
  carte chez lui. `_do_draw(k)` anime le vol (`Fly` : retournement si l'humain
  pioche, face visible si l'IA pioche chez l'humain, sinon dos), `_after_draw`
  ajoute la carte et défausse la paire éventuelle, `_post_turn` marque les
  « sauvés » et passe au `_next_active`.
- **Défausse `auto` / `manuel`** (`self.mode`, bouton de config) :
  - **Auto** (défaut) : les paires (de départ **et** après pioche) partent seules.
  - **Manuel** : seul l'humain écarte ses paires (les IA restent auto). Paires
    **surlignées** (`_paired_ids`), on **coche** les 2 cartes (`_toggle_select`)
    puis on valide via le **bouton flottant « Défausser »** (au-dessus de la paire,
    `btn_discard_float` / `_place_discard_float`) ou un clic sur la pile
    (`_manual_discard`). Deux moments : phase **`ready`** (mise en place, bouton
    **Prêt** = `_ready_done`, actif quand `_paired_ids()` est vide) et phase
    **`discard`** (après pioche, bouton **Donner** = `_donner_done`). `_discarding`
    neutralise l'éventail-victime pendant l'animation.
    - **Un seul « Donner »** : le joueur qui suit le tour de l'humain pioche
      **toujours** chez lui, donc la phase `discard` était systématiquement suivie
      d'une phase `give` (2ᵉ « Donner » redondant). `_donner_done` **fusionne** les
      deux : après `_post_turn`, s'il enchaîne sur `give` (`victim == 0`), il
      appelle directement `_give_consent`. Le mélange / réordonnancement est donc
      autorisé **pendant** `discard` (`_reorder_allowed` inclut `discard`, bouton
      **Mélanger** ajouté) pour préserver le rôle de la phase `give`. Les phases
      `give` du **début de partie** (un voisin pioche chez l'humain avant qu'il
      ait joué) gardent leur « Donner » propre.
- **Réordonnancement de sa main** (les deux modes) : la main humaine n'est **pas
  triée d'office**. On l'arrange par **glisser-déposer** (`_press_card` /
  `_drag_card`, seuil de 8 px pour distinguer clic court et glisser) ou via
  **Mélanger la main** (`_shuffle_hand`). Autorisé **hors de son tour**
  (`_reorder_allowed` : phases `ready` / `give`, ou `wait` quand `cur != 0`).
  Pendant la manipulation, l'IA **patiente** (`think_t` gelé).
  - **Écart d'insertion animé** : `_hand_layout` réserve un emplacement (largeur
    d'une carte) à l'index d'insertion (`_insert_index`, même calcul que
    `_drop_drag`) ; les cartes voisines **s'écartent** et un **emplacement cible
    surligné** (`_hand_ph`) montre où la carte va se poser. Déplacement **lissé**
    frame par frame (`_animate_hand` → `_card_x` → `_hand_draw`, réutilisé aussi à
    l'ajout / défausse de cartes).
  - **Les IA rebattent aussi leur main** (symétrie) : une IA-victime est
    `random.shuffle`-ée dans `_begin_turn` **avant qu'on pioche chez elle**, et
    une IA rebat sa main **après chaque pioche** conservée (`_after_draw`) → plus
    d'ordre trié exploitable par un humain attentif.
- **Accord avant de se faire piocher** (phase `give`) : quand un voisin va piocher
  chez l'humain (`cur != 0` **et** `victim == 0`), `_begin_turn` bascule en `give`
  — l'IA **ne pioche pas** tant que l'humain n'a pas cliqué **« Donner »**
  (`_give_consent`). Laisse le temps de mélanger / réordonner.
- **Fin** : quand ≤ 1 joueur a des cartes, le détenteur de l'orpheline est le
  Pouilleux. L'écran de fin révèle l'orpheline et l'ordre des « sauvés ».

Règles détaillées : [`docs/regles/pouilleux.md`](regles/pouilleux.md).

### 7.7 Le Bouclié (`bouclie.py`)
Mode **interactif** d'**élimination** à 2–10 joueurs (humain = siège 0, IA
autonomes ; patron `bataille.py` / `pouilleux.py`). Paquet **réduit** : rangs
**As (=1) à 10**, 4 enseignes = **40 cartes**, ni figures ni jokers (`_fresh_deck`
ne prend que `range(1, 11)`). La **pioche** se recompose depuis la **défausse**
mélangée quand elle est vide (`_draw_card`).

- **État d'un joueur** (`BPlayer`) : `pv` (entier, **source de vérité**),
  `pv_cards` (cartes d'affichage sommant à `pv` via `pv_to_cards`), `shield`
  (une carte), `charges` (liste de cartes face cachée), `alive`.
- **Mise en place** (`new_game`) : 3 cartes/joueur → PV = somme des 2 premières,
  bouclier = la 3ᵉ. Sens (`direction` ±1) et premier joueur **aléatoires**.
- **Disposition en cercle** : les joueurs sont placés sur une **ellipse**
  (`_layout_seats` via angles ; centre `EC`, rayons `RX`/`RY`), l'humain **en bas**
  (grand, cartes `self.mid`), les adversaires sur l'**arc supérieur** (compacts,
  `self.mini`) — l'arc évite le bas (réservé à l'humain) et le sommet reste sous
  le bandeau HUD. Pioche / défausse dans les **coins bas**. Effectifs **2 à 10**
  vérifiés : aucun pod ne déborde de l'écran ni ne chevauche un voisin ou la
  rangée de boutons.
- **Bouclier** : montré **à la fois** par la **carte-bouclier** horizontale
  (`_draw_shield`, façon Stonehenge, au-dessus des PV) **et** par un **écusson**
  chiffré dans la plaque (`_draw_shield_badge` : silhouette + valeur, lisible d'un
  coup d'œil). Vrai pour tout le monde, adversaires (`self.mini`) comme humain
  (`self.mid` + écusson `big`).
- **Machine à états** (`phase`) : `setup` → `draw` (la carte tirée **vole vers le
  joueur actif**, `Fly` pile → `_held_pos`) → `choose` (humain) / `ai_think` (IA)
  → `target_attack` / `target_shield` (clic sur un pod, `_pod_hitbox`) → `anim`
  → `hold` (pause lisible) → tour suivant (`_advance_turn` saute les morts).
- **La carte tirée est cachée** jusqu'à l'action (`peek` = visible d'avance si
  **As en bouclier**). Pendant `choose`/`ai_think`, elle est **tenue** près du
  joueur actif (`_draw_held`), pour qu'on voie **qui** joue.
- **Lisibilité de l'action** (`anim`) : `_perform` pose un **bandeau** (`banner` :
  action + cible, ex. « ATTAQUE > Alice »), puis monte une **timeline**
  (`{dur, fn}`, `_advance_timeline`). Les cartes se **révèlent une à une** près de
  l'acteur (`stage`, `flip`) — pour une attaque, **charges puis carte tirée**,
  avec un total **`Force : N`** cumulé — puis un **projectile** (`self.proj`,
  carte face visible) **vole de l'acteur vers la cible** (`_cast`) avant la
  résolution (`_strike` / `_apply_*`). Retours visuels : **textes flottants**
  (`FloatText` : `−N`/`+N` PV, « Bloqué ! », « Riposte ! », « raté »),
  **tremblement** (`shakes` / `_shake_offset`) et **halo** de bouclier (`glow`).
  Tout est animé par `_animate_fx` (les nombres montent même pendant `hold`).
- **Résolution** : `_resolve_attack` (force = tirée + Σ charges ; `> / = / <`
  bouclier → dégâts cible / rien / retour sur l'attaquant), `_resolve_shield`
  (remplace le bouclier de la cible), `_resolve_heal` (`>5` gagne la valeur, `<5`
  perd `5−v`), `_resolve_charge` (empile). `_change_pv` applique le delta,
  **vide les charges** du joueur dès qu'il **perd** des PV, régénère `pv_cards`
  et marque `alive=False` à `pv <= 0`.
- **IA** (`_ai_decide`) : joue à l'aveugle (valeur espérée ≈ 5,5 ; carte connue si
  `peek`), **choisit la meilleure décision** par scoring parmi : attaquer la cible
  la plus vulnérable, **charger** pour percer un gros bouclier, **renforcer son
  bouclier** OU **baisser celui d'un adversaire trop protégé**, se soigner en
  danger. Volontairement **agressive** (biais d'attaque) pour que la partie
  **converge** — une IA trop défensive (soins + boucliers hauts) traînerait sans
  fin. Le soin ayant une espérance positive (règle « +valeur si > 5 »), l'IA ne se
  soigne qu'à très bas PV.
- **Rendu** : **PV affichés en cartes** chez tout le monde (`pv_to_cards` →
  `_draw_pv_row`), le **bouclier** est une carte **de la même taille** posée à
  l'horizontale (`_draw_shield`, `rotate 90`). Trois tailles : `self.mid`
  (joueur / cartes en vol), `self.mini` (adversaires, compactes), `self.renderer`
  (pioche / défausse). Fin : dernier survivant (`_draw_over`).

Règles détaillées : [`docs/regles/bouclie.md`](regles/bouclie.md).

---

## 8. Ajouter un nouveau mode

1. Créer `game/<mode>.py` avec une classe `Scene` (gabarit simple :
   `bataille.py`) : `handle_event`, `update`, `draw`.
2. Réutiliser `CardRenderer`, `ui.draw_felt`, `ui.Button`, les easing.
3. Exposer le mode dans `main.py` : ajouter `show_<mode>()`.
4. L'activer dans `game/menu.py` : passer `available=True` et l'action dans la
   liste `specs`.
5. Documenter ses règles dans `docs/regles/<mode>.md` et mettre à jour l'index
   `docs/regles/README.md` et le tableau §1 de ce document.

---

## 9. Commandes & raccourcis

**Global** : `F11` plein écran · `Échap` retour menu.

**Solitaire** : glisser-déposer · double-clic → fondation · clic sur la pioche ·
`Espace` piocher · `U` annuler · `N` nouvelle partie.

**Le Président** : clic pour (dé)sélectionner une carte · bouton **« Poser »**
flottant au-dessus de la sélection, bouton **Jouer**, `Entrée`, ou **clic sur le
tas central** pour jouer · `Espace` Coucher. Avec l'option **à la volée**, ces
mêmes commandes servent aussi à **fermer hors-tour** quand une occasion s'ouvre.
À l'échange : sélection (si gagnant) puis **Donner** / **Confirmer le don**.

**Bataille** : clic / `Espace` avancer (ou accélérer le résultat) · `A` mode
auto · `N` nouvelle partie.

**Le Pouilleux** : clic sur une carte du voisin (à son tour) · glisser-déposer
pour réordonner sa main · **Mélanger la main** · **Donner** (autoriser un voisin
à piocher) · en défausse manuelle : (dé)cocher une carte puis bouton flottant
**Défausser**, boutons **Prêt** / **Donner**.

---

## 10. Tests (headless)

Les modes sont testables **sans fenêtre** via le pilote SDL « dummy » :

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python - <<'PY'
from main import App
app = App(); app.show_president(); sc = app._president   # ou show_bataille / …
for _ in range(200):
    sc.update(1/60)
# pygame.image.save(app.screen, "out.png")
PY
```

On pilote le moteur/scène en boucle, on force des états précis, on vérifie les
invariants (cartes conservées, N places attribuées, absence de boucle infinie) et
on sauve des rendus via `pygame.image.save`.

- L'avertissement « no fast renderer available » est **normal** en dummy.
- `PYTHONIOENCODING=utf-8` évite les erreurs cp1252 en imprimant des cartes ♥ / ♠.
- Pour tester l'IA « Forte » de façon synchrone, faire `sc._mc_thread.join()`
  après `update` (sinon le calcul tourne en thread de fond).
- Le tour de l'**humain** ne s'auto-joue pas : en headless, piloter le siège 0
  (ex. via `ai.choose(ai.build_view(sc.g, 0))` + `sc._do_play(0, …)`) pour faire
  avancer une manche.
