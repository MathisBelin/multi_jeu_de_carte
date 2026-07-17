"""Constantes globales : dimensions, couleurs, polices."""

# --- Fenetre ---
SCREEN_W = 1280
SCREEN_H = 820
FPS = 120
TITLE = "Cartes Classic"

# --- Cartes ---
CARD_W = 100
CARD_H = 142
CARD_RADIUS = 10

# Enseignes
SPADE, HEART, DIAMOND, CLUB = "spades", "hearts", "diamonds", "clubs"
SUITS = [SPADE, HEART, DIAMOND, CLUB]
RED_SUITS = {HEART, DIAMOND}
SUIT_GLYPH = {SPADE: "♠", HEART: "♥", DIAMOND: "♦", CLUB: "♣"}

# Jokers (utilisés par la Bataille) : enseigne à part + « rangs » sentinelles
# servant uniquement à distinguer le joker rouge du noir (même force au jeu).
JOKER = "joker"
JOKER_RED = 20
JOKER_BLACK = 21

RANK_LABEL = {1: "A", 11: "J", 12: "Q", 13: "K"}


def rank_label(rank: int) -> str:
    return RANK_LABEL.get(rank, str(rank))


# --- Couleurs ---
FELT_TOP = (24, 110, 78)
FELT_BOT = (10, 60, 44)
FELT_VIGNETTE = (0, 0, 0)

CARD_FACE = (250, 250, 252)
CARD_FACE_EDGE = (206, 210, 216)
CARD_SHADOW = (0, 0, 0)

SUIT_RED = (201, 47, 57)
SUIT_BLACK = (33, 38, 46)

BACK_MAIN = (33, 71, 140)
BACK_DARK = (22, 48, 99)
BACK_LIGHT = (78, 120, 196)
BACK_EDGE = (245, 247, 250)

SLOT_LINE = (255, 255, 255)
SLOT_FILL = (255, 255, 255)

TEXT_LIGHT = (238, 244, 241)
TEXT_DIM = (183, 205, 195)
ACCENT = (226, 188, 88)
ACCENT_DARK = (168, 133, 48)
HILITE = (120, 220, 150)

# --- Polices systeme (Windows) ---
FONT_UI = "Segoe UI"
FONT_SUIT = "Segoe UI Symbol"
