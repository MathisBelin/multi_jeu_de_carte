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
from game.president import PresidentScene
from game.bataille import BattleScene
from game.pouilleux import PouilleuxScene


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
        self._president = None
        self._bataille = None
        self._pouilleux = None
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
        self._solitaire = SolitaireScene(self)
        self.manager.go(self._solitaire)

    def show_president(self):
        self._president = PresidentScene(self)
        self.manager.go(self._president)

    def show_bataille(self):
        self._bataille = BattleScene(self)
        self.manager.go(self._bataille)

    def show_pouilleux(self):
        self._pouilleux = PouilleuxScene(self)
        self.manager.go(self._pouilleux)

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
