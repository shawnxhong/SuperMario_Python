"""Class for representing a Player entity within the game."""

__version__ = "1.1.0"

from game.entity import DynamicEntity


class Player(DynamicEntity):
    """A player in the game"""
    _type = 3

    def __init__(self, name: str = "Mario", max_health: float = 20):
        """Construct a new instance of the player.

        Parameters:
            name (str): The player's name
            max_health (float): The player's maximum & starting health
        """
        super().__init__(max_health=max_health)

        self._name = name
        self._score = 0
        self._niubi = False
        self._duck = False
        self._shoot = False

    def get_name(self) -> str:
        """(str): Returns the name of the player."""
        return self._name

    def get_score(self) -> int:
        """(int): Get the players current score."""
        return self._score

    def change_score(self, change: float = 1):
        """Increase the players score by the given change value."""
        self._score += change

    def clear_score(self):
        self._score = 0

    def is_niubi(self):
        """(bool): Return if the player is invincible or not. Niubi means super invincible"""
        return self._niubi

    def set_niubi(self, niubi: bool):
        """Set the player's invincibility"""
        self._niubi = niubi

    def is_duck(self):
        """(bool): Return if the player is ducking or not."""
        return self._duck

    def set_duck(self, duck: bool):
        """Set the player's state of ducking"""
        self._duck = duck

    def is_shoot(self):
        """(bool): Return if the player is able to shoot bullet or not."""
        return self._shoot

    def set_shoot(self, shoot: bool):
        """Set whether the player can shoot bullet or not"""
        self._shoot = shoot

    def __repr__(self):
        return f"Player({self._name!r})"
