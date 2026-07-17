"""Base de scene + gestionnaire de scenes avec transitions en fondu."""
import pygame
from . import ui


class Scene:
    def __init__(self, app):
        self.app = app

    def on_enter(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class SceneManager:
    def __init__(self, app):
        self.app = app
        self.current = None
        self._next = None
        self._fade = 0.0        # 0 = clair, 1 = noir
        self._phase = "idle"    # idle | out | in

    def go(self, scene, instant=False):
        if self.current is None or instant:
            self.current = scene
            scene.on_enter()
            self._fade = 0.0
            self._phase = "idle"
        else:
            self._next = scene
            self._phase = "out"

    def handle_event(self, event):
        if self._phase == "idle" and self.current:
            self.current.handle_event(event)

    def update(self, dt):
        speed = 4.0
        if self._phase == "out":
            self._fade = min(1.0, self._fade + dt * speed)
            if self._fade >= 1.0:
                self.current = self._next
                self._next = None
                self.current.on_enter()
                self._phase = "in"
        elif self._phase == "in":
            self._fade = max(0.0, self._fade - dt * speed)
            if self._fade <= 0.0:
                self._phase = "idle"
        if self.current:
            self.current.update(dt)

    def draw(self, surface):
        if self.current:
            self.current.draw(surface)
        if self._fade > 0:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(self._fade * 255)))
            surface.blit(veil, (0, 0))
