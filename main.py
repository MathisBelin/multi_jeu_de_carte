"""Cartes Classic — point d'entree.

Un jeu de cartes classique regroupant plusieurs modes de jeu.
Lancer avec :  python main.py
"""
import sys
import pygame

from game import constants as C
from game.scene import SceneManager
from game.menu import MenuScene
from game.solitaire import SolitaireScene
from game.solitaire_select import SolitaireSelectScene
from game.spider import SpiderScene
from game.president import PresidentScene
from game.bataille import BattleScene
from game.pouilleux import PouilleuxScene
from game.bouclie import BouclieScene
from game.barbu import BarbuScene
from game.dutch import DutchScene
from game.le98 import Le98Scene


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        # SCALED : la resolution logique reste 1280x820 et pygame met a
        # l'echelle automatiquement en plein ecran (souris incluse).
        self.windowed_flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H),
                                              self.windowed_flags)
        self.fullscreen = False
        self.clock = pygame.time.Clock()
        self.manager = SceneManager(self)
        self._solitaire = None
        self._spider = None
        self._president = None
        self._bataille = None
        self._pouilleux = None
        self._bouclie = None
        self._barbu = None
        self._dutch = None
        self._le98 = None
        self.running = True
        self.manager.go(MenuScene(self), instant=True)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = (pygame.SCALED | pygame.FULLSCREEN
                 if self.fullscreen else self.windowed_flags)
        try:
            self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H), flags)
        except pygame.error:
            # environnement sans support du plein ecran : on annule
            self.fullscreen = not self.fullscreen

    # --- navigation entre scenes ---
    def show_menu(self):
        self.manager.go(MenuScene(self))

    def show_solitaire(self):
        # tuile « Solitaire » du menu : ecran de choix Klondike / Spider
        self.manager.go(SolitaireSelectScene(self))

    def show_klondike(self):
        self._solitaire = SolitaireScene(self)
        self.manager.go(self._solitaire)

    def show_spider(self):
        self._spider = SpiderScene(self)
        self.manager.go(self._spider)

    def show_president(self):
        self._president = PresidentScene(self)
        self.manager.go(self._president)

    def show_bataille(self):
        self._bataille = BattleScene(self)
        self.manager.go(self._bataille)

    def show_pouilleux(self):
        self._pouilleux = PouilleuxScene(self)
        self.manager.go(self._pouilleux)

    def show_bouclie(self):
        self._bouclie = BouclieScene(self)
        self.manager.go(self._bouclie)

    def show_barbu(self):
        self._barbu = BarbuScene(self)
        self.manager.go(self._barbu)

    def show_dutch(self):
        self._dutch = DutchScene(self)
        self.manager.go(self._dutch)

    def show_le98(self):
        self._le98 = Le98Scene(self)
        self.manager.go(self._le98)

    # --- boucle principale ---
    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif (event.type == pygame.KEYDOWN
                      and event.key == pygame.K_F11):
                    self.toggle_fullscreen()
                else:
                    self.manager.handle_event(event)
            self.manager.update(dt)
            self.manager.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    App().run()
