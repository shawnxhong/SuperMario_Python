"""
Classes to represent non-playable computer-controlled moving entity.
"""

import random
import pymunk
import time

from game.entity import DynamicEntity
from game.util import get_collision_direction
from game.item import Coin

MOB_DEFAULT_TEMPO = 30
MOB_DEFAULT_WEIGHT = 100


class Mob(DynamicEntity):
    """An abstract representation of a creature in the sandbox game

    Can be friend, foe, or neither

    Should not be instantiated directly"""
    _type = 5

    def __init__(self, mob_id, size, weight=MOB_DEFAULT_TEMPO,
                 tempo=MOB_DEFAULT_TEMPO, max_health=20):
        """Constructor

        Parameters:
            mob_id (str): A unique id for this type of mob
            size (tuple<float, float>):
                    The physical (x, y) size of this mob
            weight (int): The weight of this mob
            tempo (float):
                    The movement tempo of this mob:
                      - zero indicates no movement
                      - further from zero means faster movement
                      - negative is reversed
            max_health (float): The maximum & starting health for this mob
        """
        super().__init__(max_health=max_health)

        self._id = mob_id
        self._size = size
        self._weight = weight
        self._tempo = tempo

        self._steps = 0

    def get_id(self):
        """(str) Returns the unique id for this type of mob"""
        return self._id

    def get_size(self):
        """(str) Returns the physical (x, y) size of this mob"""
        return self._size

    def get_tempo(self):
        """(int): The movement tempo of this mob.

        - zero indicates no movement
        - further from zero means faster movement
        - negative is reversed
        """
        return self._tempo

    def set_tempo(self, tempo):
        """Set the tempo of this mob.

        Parameters:
            tempo (int): Zero for no movement, larger values for faster
                         movement and negative for reversed.
        """
        self._tempo = tempo

    def get_weight(self):
        """(int): Return the weight of this mob."""
        return self._weight

    def step(self, time_delta, game_data):
        """Advance this mob by one time step"""
        # Track time via time_delta would be more precise, but a step counter is simpler
        # and works reasonably well, assuming time steps occur at roughly constant time deltas
        self._steps += 1
        vx = self.get_tempo()
        self.set_velocity((vx, self.get_velocity()[1]))

    def __repr__(self):
        return f"{self.__class__.__name__}({self._id!r})"


class Fireball(Mob):
    """The fireball mob is a moving entity that moves straight in a direction.

    When colliding with the player it will damage the player and explode.
    """
    _id = "fireball"

    def __init__(self):
        super().__init__(self._id, size=(16, 16), weight=300, tempo=0)

    def on_hit(self, event: pymunk.Arbiter, data):
        world, player = data
        player.change_health(-1)
        world.remove_mob(self)


class CloudMob(Mob):
    """Flying cloud which seeks out the player and when above the player
    will fire a fireball at them.
    """
    _id = "cloud"
    MAX_DISTANCE = 20

    def __init__(self, fire_range=10):
        """Construct a new cloud mob.

        Parameters:
            fire_range (int): The horizontal distance from the player where
                              the cloud will start firing.
        """
        super().__init__(self._id, size=(16, 24), weight=0, tempo=80)
        self._last_drop = time.time()
        self._fire_range = fire_range

    def step(self, time_delta, game_data):
        """Move towards the player and fire when within range."""
        world, player = game_data
        vx, vy = self.get_velocity()

        mob_x, mob_y = self.get_position()
        player_x, player_y = player.get_position()

        # only fire within range
        if abs(player_x - mob_x) < self._fire_range:
            vx = 0
            # only fire after a delay
            if time.time() - self._last_drop >= 2:
                x, y = self.get_position()

                rand_val = random.randint(1, 10)
                # occasionally drop a coin instead
                if rand_val == 1:
                    drop = Coin()
                    world.add_item(drop, x, y + 22)
                else:
                    drop = Fireball()
                    world.add_mob(drop, x, y + 22)
                self._last_drop = time.time()

        # move towards the player
        elif player_x < mob_x:
            vx = -self.get_tempo()
        elif player_x > mob_x:
            vx = self.get_tempo()

        self.set_velocity((vx, 0))
