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
1. **Menu** (`game/menu.py`) : 8 tuiles en **3 colonnes** (Solitaire, Président,
   Bataille, Pouilleux, Bouclié, Barbu, Dutch, Le 98), plein écran. Les
   descriptions des tuiles passent à la ligne si besoin (`wrap_text`, 2 lignes max)
   → plus de débordement. La tuile **Solitaire** ouvre un **écran de choix**
   Klondike / Spider (`game/solitaire_select.py`) — le Spider n'a pas de tuile
   propre. FreeCell (à venir) n'est plus affiché au menu.
2. **Solitaire Klondike** (`game/solitaire.py`) : complet — glisser-déposer,
   distribution animée, double-clic → fondation, annuler (U), résolution auto,
   victoire + confettis.
2bis. **Spider Solitaire** (`game/spider.py`) : 2 jeux (104 cartes), 10 colonnes,
   difficulté 1/2/4 couleurs (phase `setup`). Empile décroissant toute enseigne,
   déplace un bloc seulement s'il est d'une seule enseigne ; pioche = 1 carte/
   colonne (interdit si colonne vide) ; suite Roi→As même enseigne → fondation
   (8 = victoire). Double-clic = déplacement auto, undo, score. `main.py` :
   `show_solitaire`=chooser, `show_klondike`, `show_spider`.
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
   - **Format `survival`** (option config « Format » : Manche unique / Survie,
     min 3 j.) : en survie, le Pouilleux de chaque manche est **éliminé** puis on
     **redistribue** jusqu'au **dernier survivant**. `new_game` = reset tournoi +
     `_deal_round` (distribue aux non-éliminés) ; `_finish` élimine, phase
     `round_over` (bouton « Manche suivante » → `_next_round`) puis `over`
     (`_draw_over_survival`).
6. **Le Bouclié** (`game/bouclie.py`) : jeu d'élimination 2–10 joueurs (humain =
   siège 0, IA autonomes). Paquet **40 cartes** (As=1 … 10, ni figures ni jokers).
   Chacun a des **PV** (2 cartes côte à côte, `pv` entier = source de vérité +
   `pv_cards` d'affichage via `pv_to_cards`) et un **bouclier** (1 carte dessinée à
   l'horizontale, `rotate 90`). À son tour on tire **face cachée** puis on choisit
   (carte révélée à l'action, SAUF charge) : **Attaquer** (force = tirée + Σ
   charges vs bouclier : `>` dégâts cible / `=` rien / `<` retour sur l'attaquant),
   **Changer bouclier** (soi ou autre), **Charger** (garder caché, cumulable,
   dépensé d'un coup en attaquant ; perdu si on perd des PV), **Prendre de la vie**
   (≤5 gagne la valeur, >5 perd `v−5`). **As en bouclier** = voir la carte d'avance
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
7. **Le Barbu** (`game/barbu.py`) : jeu de **levées à contrats** interactif **3–10
   joueurs** (humain = siège 0, IA autonomes). Logique + rendu dans la scène (pas
   de moteur séparé). But = **le moins de points**. **6 manches** fixes (`MANCHES`) :
   `plis` (sans règle), `coeurs`, `dames`, `roi_pique` (**K♠**, pas roi de cœur !),
   `dernier` (dernier pli), `tout` (cumul).
   - **Distribution égale** (`_deal`) : paquet 52, on retire `52 % N` cartes de
     plus **bas rang** parmi les **non importantes** du contrat (`_is_important`
     protège tous les cœurs / les 4 dames / le K♠ / les trois au tour « Tout »),
     puis `52 // N` chacun. `manche_deck` = snapshot de la compo (pour l'IA).
   - **Pli** : fournir le **signe** demandé si on l'a (`_legal_cards`), sinon
     défausse libre ; **pas d'atout**, plus fort du signe gagne (`rank_val`, As
     haut) et entame le suivant. `self.per = 52 // N` plis/manche, N cartes/pli.
   - **Scoring** (`_trick_points`) au vainqueur du pli : `heart`/cœur, `queen`/dame,
     `king` (K♠), `last` (dernier pli), **et** `trick` (+5) **par pli si**
     `trick_counts[manche_idx]` (VRAI par défaut TOUTES manches). Défauts
     5/10/20/80/100, tous réglables.
   - **Premier joueur** = `(first_seat + manche_idx) % N`, `first_seat` **tiré au
     sort** à `new_game` (sinon la manche 1 commençait toujours par l'humain), puis
     tourne ; le vainqueur d'un pli mène le suivant.
   - **Phases** : `setup`/`advanced` (sous-écran réglages) · `manche_intro` →
     `playing`/`ai_think` → `anim` → `trick_end` → **ramassage animé**
     (`_collect_trick` : les cartes du pli **volent vers le vainqueur**,
     `_finish_collect`) → `manche_end` → suivante ou `over`.
   - **IA** `_ai_play` : **heuristique** (pas de MC) mais affûtée — en suivant,
     passe **sous** la maîtresse en lâchant sa carte la plus **dangereuse**
     (`_danger`) ; prise inévitable (dernière à jouer) → n'ajoute pas de pénalité
     (`_penalty_of`), lâche une haute carte sûre ; défaussée → jette la plus
     dangereuse ; à l'entame (`_ai_lead`) utilise une **mémoire des cartes**
     (`manche_played` + `_outstanding_higher`) pour mener une couleur qu'elle **ne
     remportera pas**. Benchmark vs ancienne IA (N=4) : ~275 vs ~310 pts, 336 vs
     264 parties gagnées.
   - **Présentation** : cercle (`_layout_seats`), pli en couronne au centre
     (`_trick_slot`), main cliquable en bas (injouables **grisées**), **score par
     pod** (`_live_score` = total + manche courante). **Écran Avancé** : par valeur
     de pénalité, boutons `−/+` **et** un **champ de saisie clavier** stylé
     (`pen_field`, `_start_edit`/`_commit_edit`, caret, focus doré) ; + 6 bascules
     « plis comptés » par manche. La saisie clavier est interceptée AVANT le
     traitement normal des events (sinon Échap quitterait).
8. **Le Dutch** (`game/dutch.py`) : jeu de **mémoire / bluff** interactif **2–6
   joueurs** (humain = siège 0, IA autonomes). Logique + rendu dans la scène.
   But = **plus petit total** ; **seul l'annonceur** de « Dutch » gagne/perd.
   Paquet 52 ; **valeurs Dutch** (`dutch_value`) : As=1, 2–10=rang, J=11, Q=12,
   **Roi noir (♠/♣)=0** (meilleure), **Roi rouge (♥/♦)=15** (pire). Chacun a **4
   cartes face cachée**, en **regarde 2** au départ (humain choisit en phase
   `peek`). **Connaissance** (`DPlayer.knows`) = ensemble d'**objets Card** vus,
   qui **suit l'objet** (donc survit à un échange).
   - **Tour** : piocher (`_begin_draw`) OU **prendre le dessus de la défausse**
     (`_begin_take_discard`, `from_discard`) puis **remplacer** une carte
     (`_do_replace`) ou **défausser** (`_do_discard`) pour un **pouvoir**
     (`power_of`). **Seuls le Valet** (échanger deux cartes, `swap`) **et la Dame**
     (regarder n'importe quelle carte, `look_any`) ont un pouvoir — toutes les
     autres cartes n'en ont aucun. **Remplacer** une carte à pouvoir (Valet/Dame,
     celle qui part à la défausse) **déclenche** son pouvoir pour le remplaçant
     (`_finish_replace` → `_open_slap(discarder_power=True)`). Une carte prise dans
     la défausse **doit être échangée**. Le `peek` initial humain est **définitif**.
   - **Pouvoirs — sélection + validation** (`power_sel`) : on **sélectionne** la/les
     carte(s) (surbrillance dorée + **croix** de désélection `_power_x_rects`) puis
     **Valider** (`_validate_power`, actif à `len==_power_need()` : 1 Dame, 2 Valet)
     ou **Annuler** (`_cancel_power`). File `power_queue` (`_process_next_power`,
     `_order_power_seats`) : chaque défausseur d'une carte à pouvoir l'utilise
     **chacun son tour** ; les IA passent par `_ai_power`.
   - **Annonce « Dutch »** (`_announce_dutch`) : **ne coupe PAS le tour** — le joueur
     joue son tour normalement puis la partie **se termine quand le tour lui revient**
     (`_start_turn` révèle si `seat == dutch_caller`). Il peut continuer à slapper.
   - **Défausse instantanée** (`_open_slap`/`_do_slap`/`_tick_slap`) — **temps réel,
     non bloquante** : l'humain peut cliquer **n'importe quelle** de ses cartes
     (`_human_slap_click`) → bonne valeur = elle part (`_do_slap`), mauvaise = **carte
     de pénalité** (`_slap_penalty`, +1). Le **halo/timer** ne s'affiche **que si
     l'humain** a une carte **connue** de la valeur (jamais d'indice sur les autres).
     La fenêtre **bloque** (le prochain, une IA, attend le décompte) **seulement si le
     prochain est une IA ET que l'humain peut se défausser** (ou pouvoir humain de
     défausseur) ; sinon **arrière-plan** (`slap_bg`, `slap_flies`, IA slappent en
     fond, leurs pouvoirs résolus instantanément `_apply_bot_power`/`_bot_swap_instant`).
     Le tick bg ne tourne PAS pendant `self.flies` (sinon slot périmé) ; `_finish_replace`
     défensif. Fin (`_do_reveal`) : l'annonceur gagne si total le plus bas **et**, à
     égalité, strictement **moins de cartes** que les ex æquo (égalité parfaite ⇒ perd).
   - **IA heuristique** (pas de MC) : `_ai_turn_start` pioche/annonce selon
     `_est_total` (connues + espérance `UNKNOWN_EV≈6.6`) avec **pression** croissante ;
     `_ai_choose` remplace au meilleur gain ou défausse pour un pouvoir ; `_ai_swap`
     échange une carte haute connue contre une adverse plus basse.
   - **Difficulté + options** (écran setup, conservées entre parties) : sélecteur
     **Facile** (toutes aides ON + réaction max) / **Difficile** (tout OFF + réaction
     min) / **Perso** (affiche le menu). 4 réglages en perso : `opt_show_known`
     (cartes connues face visible), `opt_slap_highlight` (« Aide à la défausse » :
     surligne **quelle** carte connue défausser), `opt_free_slap` (tenter avec
     n'importe quelle carte, pénalité), `slap_window` (**temps de réaction des bots**,
     1–4 s, presets `SLAP_PRESETS`).
   - **Mémoire TOTALE** (demande utilisateur) : l'humain voit ses 2 cartes UNIQUEMENT
     pendant la phase `peek` ; ensuite `_draw_hand` affiche TOUT face cachée (ses
     cartes ET les adversaires) jusqu'à `over`. Les cartes vues (pioche/pouvoir)
     restent dans `knows` (slap/IA) mais NE SONT JAMAIS affichées ; les pouvoirs ne
     montrent qu'un aperçu bref (`_show_peek`). Pas de badge permanent.
   - **Animations** (`_do_replace`/`_finish_replace`, `_do_discard`/`_finish_discard`) :
     poser/défausser fait **voler** la carte, mutation du modèle **différée** à
     l'atterrissage (carte en vol restée dans `self.drawn` = comptée ; `hide_slot`
     masque l'emplacement animé).
   - **Présentation** : cercle (`_layout_seats`), pioche/défausse **au centre**,
     tout face cachée en jeu. Écran de fin : mains révélées + **total par plaque**.
9. **Le 98** (`game/le98.py`) : défausse à **total commun** ≤ 98 (variante du « 99 »),
   interactif 2–10 joueurs (humain siège 0, IA autonomes). 4 cartes/joueur, pioche
   52 au centre, `pile_total` de 0 à max 98. Tour : poser 1 carte (effet) puis
   repiocher (revenir à 4) ; qui ne peut plus jouer ≤ 98 **déborde**. Valeurs
   (`_result_total`) : 2–10 = +valeur ; **As** +1/+11 (choix) ; **Valet** 0 +
   inverse le sens ; **Dame** −10 ; **Roi** = 70. Modes : **Manche unique** (le
   premier à déborder = `loser`, fin) / **Survie** (min 3 j. : élimine puis
   redistribue jusqu'au dernier = `winner`) ; `_resolve_bust` branche selon
   `survival`. IA `_ai_choose` **agressive**
   (pousse le total au plus haut ≤ 98) — sinon manches sans fin. Total géant au
   centre (rouge ≥ 85) entre pile et pioche, vies en pastilles, cartes jouables
   surlignées / injouables grisées. `main.py` `show_le98`/`_le98` + tuile menu.

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
app = App(); app.show_president(); sc = app._president   # ou show_bataille / show_barbu / …
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
- Mode **FreeCell** (annoncé dans le menu, non implémenté) — créer une `Scene`,
  l'exposer dans `main.py` (`show_*`), l'activer dans `menu.py` (`available=True`
  + action), documenter dans `docs/regles/`. Gabarit : `game/bataille.py` (ou
  `game/spider.py` pour un solitaire à colonnes).
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
