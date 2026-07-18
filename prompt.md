# Prompt de reprise — Cartes Classic

> Copier-coller ce fichier au début d'une nouvelle session pour redonner tout le
> contexte du projet, puis remplir la section **Tâche du jour** en bas.

Je reprends le développement d'un jeu de cartes en Python déjà bien avancé.

## Contexte
- Dossier : `F:\Projets\Jeux\Jeu_de_carte_classic`
- Python 3.13 + pygame 2.6.1 (Windows). Lancer : `python main.py`
- Résolution logique 1280×820 (flag `SCALED` → plein écran F11 mis à l'échelle).
- App multi-modes derrière un menu, soin porté au visuel / animations / UX.
- Architecture par scènes (`game/scene.py`, `SceneManager`, transitions en
  fondu) : ajouter un mode = créer une `Scene`, l'exposer dans `main.py`
  (`show_*`), l'activer dans `menu.py` (`available=True` + action). Gabarit récent
  et simple : `game/bataille.py`.

## Ce qui est fait
1. **Menu** (`game/menu.py`) : 7 tuiles en **3 colonnes** (5 jouables : Solitaire,
   Président, Bataille, Pouilleux, Bouclié ; FreeCell/Spider à venir), plein écran.
2. **Solitaire Klondike** (`game/solitaire.py`) : complet — glisser-déposer,
   distribution animée, double-clic → fondation, annuler (U), résolution auto,
   victoire + confettis.
3. **Bataille** (`game/bataille.py`) : duel 2 joueurs (vous vs ordinateur),
   **avec 2 jokers** (54 cartes), autonome (aucune décision). Animations de
   retournement, écran « showdown » (pause pour voir le résultat, clic accélère),
   batailles sur égalité (pot), recomposition des pioches par mélange, mode Auto.
   → Support joker ajouté au modèle : enseigne `C.JOKER`, rangs sentinelles
   `JOKER_RED`/`JOKER_BLACK`, face dédiée dans `CardRenderer` (les autres modes
   ne distribuent pas de joker, donc inchangés).
4. **Le Président** (variante maison détaillée) — le plus abouti :
   - Moteur **pur** des règles : `game/president_game.py` (`PresidentGame`), sans
     pygame, source unique de vérité, avec `clone()`, `legal_moves()`,
     `snap_moves()`, `self_complete_move()`.
   - Scène : `game/president.py` — délègue TOUTE la logique au moteur (`self.g`),
     lit l'état via des propriétés ; gère écran de config, animations, pause,
     rythme IA, écran d'échange, rendu (table en cercle, pods IA compacts).
   - IA bots : `game/ai.py` (heuristique + comptage) et `game/ai_mc.py`
     (Monte-Carlo par déterminisation, threadé). Option « IA : Normale / Forte ».
5. **Le Pouilleux** (`game/pouilleux.py`) : Old Maid français interactif 2–10
   joueurs (humain = siège 0, IA autonomes), versions **classique** (Valet de
   Pique connu) / **mystère**. Appariement même rang + même couleur.
   - **Présentation** : joueurs disposés **en cercle** (ellipse `EC`/`RX`/`RY`,
     humain en bas, adversaires sur l'arc supérieur ; centre-bas libre), défausse
     au **centre** de l'anneau, **titre** avec la version (« — Classique/Mystère »).
     À mon tour, `_launch_zone_in` anime les cartes du voisin qui **arrivent devant
     moi** (`_zone_slots`, y=498) ; à la pioche, la carte choisie vient à moi et
     les autres **repartent chez le voisin** (`_do_draw`, symétrie).
   - **Défausse `auto` / `manuel`** (bouton sur l'écran de config). En manuel,
     l'humain écarte lui-même ses paires (surbrillance + clic sur les 2 cartes
     puis sur la pile de défausse) à la **mise en place** (phase `ready`, bouton
     **Prêt**, actif quand plus aucune paire) et **après chaque pioche** (phase
     `discard`, bouton **Donner**) ; les IA restent automatiques
     (`_paired_ids` / `_manual_discard` / `_ready_done` / `_donner_done`).
   - **Réordonnancement de la main** (les 2 modes) : la main humaine n'est plus
     triée d'office ; glisser-déposer ou bouton **Mélanger la main**
     (`_shuffle_hand`), autorisé hors de son tour (`_reorder_allowed`, IA gelée
     pendant la manipulation) → casse la prévisibilité de l'ordre présenté au
     voisin. Écart d'insertion animé pendant le glisser (`_hand_layout` /
     `_animate_hand` / `_hand_ph`). Les IA rebattent AUSSI leur main
     (`random.shuffle` dans `_begin_turn` avant qu'on pioche + `_after_draw`).
   - **Défausse manuelle** : bouton flottant **Défausser** centré au-dessus de la
     paire cochée (`btn_discard_float` / `_place_discard_float`), en plus du clic
     sur la pile.
   - **Accord « Donner »** (phase `give`, les 2 modes) : quand un voisin va piocher
     chez l'humain (`cur != 0` et `victim == 0`), l'IA attend que l'humain clique
     **Donner** (`_give_consent`) → laisse le temps de mélanger/réordonner.
6. **Le Bouclié** (`game/bouclie.py`) : jeu d'élimination 2–10 joueurs (humain =
   siège 0, IA autonomes). Paquet **40 cartes** (As=1 … 10, ni figures ni jokers).
   Chacun a des **PV** (2 cartes côte à côte, `pv` entier = source de vérité +
   `pv_cards` d'affichage via `pv_to_cards`) et un **bouclier** (1 carte dessinée à
   l'horizontale, `rotate 90`). À son tour on tire **face cachée** puis on choisit
   (carte révélée à l'action, SAUF charge) : **Attaquer** (force = tirée + Σ
   charges vs bouclier : `>` dégâts cible / `=` rien / `<` retour sur l'attaquant),
   **Changer bouclier** (soi ou autre), **Charger** (garder caché, cumulable,
   dépensé d'un coup en attaquant ; perdu si on perd des PV), **Prendre de la vie**
   (>5 gagne la valeur, <5 perd `5−v`). **As en bouclier** = voir la carte d'avance
   (`peek`). Machine à états `draw`/`choose`/`target_*`/`anim`/`hold` ; `_change_pv`
   vide les charges à toute perte de PV et élimine à `pv<=0`. Dernier survivant gagne.
   - **Présentation** : joueurs **en cercle** (ellipse, humain en bas), PV **en
     cartes** pour tous, bouclier montré **à la fois en carte** (Stonehenge) **et
     en écusson** chiffré (`_draw_shield_badge`). Effectifs 2→10 sans chevauchement,
     pioche/défausse (même taille) dans les coins bas.
   - **Lisibilité** : la carte tirée **vole vers le joueur actif**, un **bandeau**
     annonce l'action + cible, les charges+carte se **révèlent une à une**
     (`stage`, « Force : N »), puis un **projectile** (`proj`) vole vers la cible.
     Effets : `FloatText` (dégâts/soin/Bloqué/Riposte), `shakes`, `glow`.
   - **IA** `_ai_decide` : scoring **agressif** (sinon la partie ne converge pas) ;
     change son bouclier OU celui d'un adversaire à son avantage.

## Règles du Président (implémentées, à respecter absolument)
- 2 à 10 joueurs (humain = siège 0 + IA), choisis sur l'écran de config. À moins
  de 4 joueurs, réglage `small_roles` : garder les extrêmes (Président/Trou, 2
  cartes) ou les Vices (Vice-Prés/Vice-Trou, 1 carte) ; Neutre au milieu à 3.
- Distribution : « équitable » (52//N chacun, excédent retiré, les 2 Dames
  toujours conservées) ou « complète » (tout distribué, les joueurs à +1 carte
  sont des sièges VOISINS). L'option n'apparaît que si `52 % N != 0`.
- Ordre des forces : 3 < 4 < … < As < 2. Combos simple/paire/brelan/carré,
  surenchère de même taille ; ÉGALITÉ acceptée (mêmes valeurs, simples ET doubles).
- Main forcée (simples seulement) : 2 cartes égales de suite → le joueur doit
  poser la 3e égale s'il l'a, OU se coucher (choix, jamais auto pour l'humain) ;
  s'il ne l'a pas il est sauté SANS être couché.
- 4 mêmes cartes à la suite (1+1+1+1 ou 2+2, sur plusieurs poses) ferment le pli ;
  main au dernier qui a posé.
- Poser un 2 ferme le pli. Se coucher manuellement = sorti pour tout le pli ;
  passe automatique si aucun coup possible (ne compte pas comme se coucher).
- On ne joue pas sur le futur Président : dès qu'un joueur pose sa dernière
  carte et devient Président (1er à finir), le pli se ferme, main au suivant.
- Révolution = un CARRÉ posé d'un seul coup par une personne → ordre inversé
  pour TOUTE la manche (le 3 devient la fermeture) ; un autre carré = contre-
  révolution (bascule ON/OFF). (La chaîne de 4 simples ferme mais N'inverse PAS.)
- Finir la manche sur un 2 (un 3 en révolution) → pire place disponible
  (2e fautif → 2e pire place).
- 1er tour uniquement : la Dame de cœur ouvre ; le sens du jeu (fixé pour la
  partie) dépend du côté le plus proche où se trouve la Dame de pique (aléatoire
  si équidistant ou même détenteur).
- Titres : Président, Vice-Président, (Neutres au milieu si 5+ joueurs), Vice-Trou,
  Trou du cul. Échange entre manches : le Trou donne ses 2 meilleures au Président,
  le Vice-Trou 1 au Vice-Président ; les gagnants choisissent les cartes rendues
  (écran dédié si c'est l'humain) ; les neutres n'échangent pas.
  → Si l'humain est PERDANT (Trou / Vice-Trou), il donne LUI-MÊME ses meilleures
  cartes : elles sont IMPOSÉES et en SURBRILLANCE (verrouillées, pas de triche),
  puis bouton « Donner mes meilleures cartes » (moteur `give_best` :
  `human_best_gift` / `apply_human_give_best`). Les IA perdantes : automatique.
- Clic sur le tas central = bouton Jouer. Sélection : les cartes NON sélectionnées
  deviennent transparentes (comme les injouables) et un petit bouton flottant
  « Poser » (« Donner » à l'échange) s'affiche centré au-dessus des cartes choisies
  (`btn_place` / `_floating_button`). Idem Pouilleux : « Défausser » au-dessus de
  la paire cochée (`btn_discard_float`).
- UX : écran de config en COMPARTIMENTS (titres + descriptions + bascules codées
  couleur) ; tableau « CLASSEMENT » horizontal REPLIABLE (translucide) sous le tas,
  colonnes par rôle, noms qui remplissent les « ? » au fur et à mesure.
- **Option « À la volée »** (toggle config, OFF par défaut) : fermer un carré
  HORS-TOUR pour récupérer la main (réactivité ; au plus 1 snappeur car 4
  cartes/rang). 3 cas : simples (3 égaux au tas + je pose la 4e), paires (paire
  au tas + je pose la paire égale → 2+2), et « voler son propre jeu » (à mon
  tour, 2 simples au tas, je pose mes 2 dernières d'un coup). Jamais avec la
  carte de fermeture (2, ou 3 en révolution). Quand l'option est ON, 2 réglages
  apparaissent : **réactivité des bots** (« ne volent pas » + bouton « Ne pas
  voler » et temps illimité pour l'humain / « 3 s » / « instantané ») et **« Voler
  son propre jeu »** (sous-option, OFF par défaut).

## Docs et mémoire
- `docs/TECHNIQUE.md` (architecture détaillée), `docs/regles/*.md` (une fiche par
  mode). `README.md` (présentation + résumés).
- Mémoire projet persistée (fiches `cartes-classic-project`, `ia-president-approche`).
- **MERCI de maintenir docs + fiches de règles + mémoire à jour à chaque changement.**

## Tests (sans fenêtre)
Tout est testable en headless avec le pilote SDL dummy :

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python - <<'PY'
from main import App
app = App(); app.show_president(); sc = app._president   # ou show_bataille / show_solitaire
for _ in range(200):
    sc.update(1/60)
# pygame.image.save(app.screen, "out.png")
PY
```

On pilote le moteur/scène en boucle, on vérifie les invariants (cartes
conservées, N places attribuées, pas de boucle infinie) et on sauve des rendus
via `pygame.image.save`. L'avertissement « no fast renderer available » = normal
en dummy. (Astuce : `PYTHONIOENCODING=utf-8` pour éviter les erreurs cp1252 en
imprimant des cartes ♥/♠ ; pour tester l'IA MC en boucle synchrone, faire
`sc._mc_thread.join()` après `update`.)

## Reste à faire / pistes
- Modes **FreeCell, Spider** (annoncés dans le menu, non implémentés) — créer une
  `Scene`, l'exposer dans `main.py` (`show_*`), l'activer dans `menu.py`
  (`available=True` + action), documenter dans `docs/regles/`. Gabarit :
  `game/bataille.py`.
- Réglage éventuel du budget Monte-Carlo (`determinizations=32`) si l'IA
  « Forte » est trop lente à 10 joueurs.
- Le Monte-Carlo NE simule PAS l'« à la volée » dans ses rollouts (approximation
  assumée) — chantier possible si on veut le rendre exact.
- Sons / effets, améliorations visuelles.

## Consigne de démarrage
Commence par lire la mémoire projet et `docs/TECHNIQUE.md`, puis dis-moi ce que
tu comprends de l'état actuel avant de coder.

## Tâche du jour
<!-- Décris ici la tâche du jour. -->
