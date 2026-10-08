"""Les 52 cartes du jeu et leurs attributs (rang, enseigne, couleur)."""

from dataclasses import dataclass

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"]
SUITS = ["hearts", "diamonds", "clubs", "spades"]
RED_SUITS = {"hearts", "diamonds"}
FACE_RANKS = {"jack", "queen", "king"}


@dataclass(frozen=True)
class Card:
    rank: str  # "2" ... "10", "jack", "queen", "king", "ace"
    suit: str  # enseigne : "hearts", "diamonds", "clubs", "spades"

    @property
    def color(self):
        return "red" if self.suit in RED_SUITS else "black"

    @property
    def is_face(self):
        return self.rank in FACE_RANKS

    @property
    def name(self):
        return f"{self.rank} of {self.suit}"

    @property
    def class_id(self):
        return SUITS.index(self.suit) * len(RANKS) + RANKS.index(self.rank)

    @property
    def filename(self):
        return f"{self.rank}_of_{self.suit}.png"


DECK = [Card(rank, suit) for suit in SUITS for rank in RANKS]
