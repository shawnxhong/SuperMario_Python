"""File to handle the dynamic entity construction based on the identifier
tokens of entities.
"""

__version__ = "1.1.0"

from typing import Tuple, Callable, Iterable

from game.world import World


class WorldBuilder:
    """World builder class that can be used to construct a world from
    entity ids by dynamically assigning processors to ids.
    """
    def __init__(self, block_size: int, gravity: Tuple[int, int] = (0, 300),
                 fallback: Callable = None):
        """Construct a new world builder with a specific block size.

        The args passed to the fallback callback is determined by what is given
        to the add_entity method.

        Parameters:
            block_size (int): The pixel dimensions of blocks used to calculate
                              the require world dimensions.
            gravity (tuple<int, int>): The gravity of the world.
            fallback (Callable<World, str, int, int, *> -> None): The builder
                callback to add an entity to the world for an unknown id.
        """
        # the builders dictionary contains mappings on how to
        # process ids of entities
        self._builders = {}
        self._entities = []
        self._fallback = fallback
        self._block_size = block_size
        self._gravity = gravity
        self._width = 0
        self._height = 0

    def register_builder(self, entity_id: str, builder: Callable):
        """Register a new builder process for an entity id.

        The given builder is called whenever an entity with the given entity id
        is encountered during world construction.

        The signature of the builder method should be as follows:
            builder(world: World, entity_id: str, x: int, y: int, *args) -> None
        The args passed to the builder callback is determined by what is given
        to the add_entity method.

        Parameters:
            entity_id (str): String identifier for an entity.
            builder (Callable): The builder callback to add an entity to the world.
        """
        self._builders[entity_id] = builder

    def register_builders(self, entity_ids: Iterable[str], builder: Callable):
        """Registers a new builder process for a given entity id

        The given builder is called whenever an entity with the given entity id
        is encountered during world construction.

        The signature of the builder method should be as follows:
            builder(world: World, entity_id: str, x: int, y: int, *args) -> None
        The args passed to the builder callback is determined by what is given
        to the add_entity method.

        Parameters:
            entity_ids (<str, ...>): Iterable of string identifiers for an entity.
            builder (Callable): The builder callback to add an entity to the world.
        """
        for entity_id in entity_ids:
            self._builders[entity_id] = builder

    def add_entity(self, entity_id: str, x: int, y: int, *args):
        """Add an entity to the world based on the entity id.

        Parameters:
            entity_id (str): The id of the entity used when processing the entity.
            x (int): The x coordinate of the entity.
            y (int): The y coordinate of the entity.
            *args: Any additional arguments, passed to the builder for this entity.

        Returns:
            (WorldBuilder): self, allows for chained method calls.
        """
        # resize the world accordingly
        if x >= self._width:
            self._width = x + self._block_size // 2
        if y >= self._height:
            self._height = y + self._block_size // 2

        self._entities.append((entity_id, x, y, args))

        return self

    def build(self) -> World:
        """Construct a new world containing all the added entities.

        The size of the world is determined by the maximum entity space occupied.

        Each entity builder is called during this construction.

        Raises:
            KeyError: If there is no associated builder for an entity id and no
                      fallback builder has been set.
        """
        world = World((self._width, self._height), self._block_size, gravity=self._gravity)
        for entity in self._entities:
            entity_id, x, y, args = entity

            if entity_id not in self._builders:
                if self._fallback is None:
                    raise KeyError(f"Unable to build world,"
                                   f"no matching processor for entity id of {entity_id}")
                self._fallback(world, *entity)
                continue

            processor = self._builders[entity_id]
            processor(world, entity_id, x, y, *args)

        return world

    def clear(self):
        """
        Removes all the entities that were added
        """
        self._entities.clear()
        self._width = 0
        self._height = 0


def level_size(level: str) -> Tuple[int, int]:
    """Calculate the rows, columns dimensions of a level from the level string.

    Parameters:
        level (str): The level string.

    Returns:
        (tuple<int, int>): rows, columns dimensions of the given level.
    """
    return level.count('\n') + 1, level.find('\n')


def load_level(filename: str) -> str:
    """Load a level file into a string and returns that string.

    Pads the string so that each line has the same amount of characters.

    Parameters:
        filename (str): The name of the level file to load.

    Returns:
        (str): The level string resulting from loading a level file.
    """
    with open(filename, 'r') as file:
        file_contents = file.readlines()

    # get the length of the longest line
    max_width = len(max(file_contents))

    level = []
    for line in file_contents:
        # find how many characters are missing from the current line
        fill = max_width - len(line)
        # pad the current line
        level.append(line.rstrip() + (" " * fill))

    return "\n".join(level)


def load_world(builder: WorldBuilder, filename: str, *args):
    """Loads entities within a file into a world builder.

    Parameters:
        builder (WorldBuilder): The builder to append found entities to.
        filename (str): The game world file to load with blocks.

    Returns:
        (World): The world produced by adding the found entities.
    """
    level = load_level(filename)
    for y, line in enumerate(level.split('\n')):
        for x, character in enumerate(line):
            if character in ('\n', ' '):
                continue

            builder.add_entity(character, x, y, *args)

    return builder.build()
