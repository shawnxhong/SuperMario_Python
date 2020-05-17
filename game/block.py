"""
Classes to represent static block entities in the game world.
"""

import random
from typing import Tuple

from game.entity import Entity
from game.item import Coin
from game.util import get_collision_direction


class Block(Entity):
    """One of the blocks in the sandbox game"""
    # The unique identifier for this block
    _id = None
    _type = 2
    _cell_size = (1, 1)

    def __init__(self, block_id: str = None):
        """Construct a generic block with a block identifier.

        Parameters:
            block_id (str): The unique id of this block
        """
        super().__init__()

        if block_id is not None:
            self._id = block_id

    def get_id(self) -> str:
        """(str) Returns the unique id of this block"""
        return self._id

    def get_position(self) -> Tuple[float, float]:
        """(float, float) Returns the (x, y) position of the block's centre"""
        x, y = self.get_shape().bb.center()
        return x, y

    def get_cell_size(self) -> Tuple[int, int]:
        """Dimensions of the block relative to the grid size.

        A cell size of (1, 1) indicates a pixel size of (BLOCK_SIZE, BLOCK_SIZE)
        """
        return self._cell_size

    def __repr__(self):
        return f"{self.__class__.__name__}({self._id})"


class MysteryBlock(Block):
    """A mystery block drops items when the player hits its underside.

    The active state of a mystery block is whether it has dropped items or not.
    """
    _id = "mystery"

    def __init__(self, drop: str = None, drop_range: Tuple[int, int] = (1, 1)):
        """
        Construct a new mystery block.

        Parameters:
            drop (str): The string identifier of the dropped item for this block.
            drop_range (tuple<int, int>): The range of drops for this block,
                                          first element is the minimum drops,
                                          second element is the maximum drops.
        """
        super().__init__()
        self._drop = drop
        self._drop_range = drop_range
        self._active = True

    def get_drops(self) -> Tuple[str, ...]:
        """Get the drops of the mystery block

        Returns:
            tuple<str, ...>: The item identifiers of the dropped items.
        """
        return (self._drop,) * random.randint(*self._drop_range)

    def _drop_items(self, world, drops: Tuple[str]):
        """Drop each of the dropped items into the world.

        Parameters:
            world (World): The world to place dropped items within.
            drops (tuple<str>): A tuple of item identifiers to place.
        """
        x, y = self.get_position()
        for drop in drops:
            if drop is not None:
                # world.add_item(create_item(drop), TODO: Make this non-hardcoded
                world.add_item(Coin(), x + random.randint(-10, 10), y - 25)

    def on_hit(self, event, data):
        """Callback collision with player event handler."""
        world, player = data
        # Ensure the bottom of the block is being hit
        if get_collision_direction(player, self) != "B":
            return

        if self._active:
            self._active = False

            # Drop items into the game world
            drops = self.get_drops()
            self._drop_items(data[0], drops)

    def is_active(self) -> bool:
        """(bool): Returns true if the block has not yet dropped items."""
        return self._active


