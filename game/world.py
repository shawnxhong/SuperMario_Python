"""
A class to represent a world made up of physical things
"""

import pymunk
import time
from typing import Tuple, Iterable

from game.entity import BoundaryWall, Entity
from player import Player
from game.item import DroppedItem
from game.block import Block
from game.mob import Mob

# The intention with the following constants is to express a finite range of values that
# can effectively be treated as their own type in this code. We have used collections of
# types that are familiar to the student (str/int).
# In general, however, enums are the appropriate way to express this intention, but have
# been avoided to make the code more easily understood by the student.
# See: https://docs.python.org/3/library/enum.html

# Unique ids for each collision type
COLLISION_TYPES = {
    "wall": 1,
    "block": 2,
    "player": 3,
    "item": 4,
    "mob": 5
}

# Unique ids for each category of physical thing
#   - Used when querying for items in a point/rectangle
#   - Must be a unique power of 2, less than 2 ^ 32
PHYSICAL_THING_CATEGORIES = {
    "wall": 2 ** 1,
    "block": 2 ** 2,
    "player": 2 ** 3,
    "item": 2 ** 4,
    "mob": 2 ** 5
}

# Names for each collision event recognised by pymunk (can have a callback attached)
COLLISION_HANDLER_CALLBACKS = {'begin', 'separate', 'pre_solve', 'post_solve'}

# The size of a time delta between steps
STEP_SIZE = 0.02


class World:
    """Game world that contains things in physical space.

    Space is subdivided into grid cells. Blocks take up all of the space within their
    grid cell, whereas all other things can be any size. Each cell has a (column, row)
    position which the (x, y) position of the cell's centre.

    Handles physical motion & collisions in a step-wise fashion. Accounts for
    velocity, acceleration, & general gravity.

    A motion quantity is an (x, y) pair, where x & y can be floats. The following
    names are all considered motion quantities:
        - position/point/coordinates
        - velocity/speed
        - acceleration/gravity
    """

    def __init__(self, grid_size, cell_expanse, gravity=(0, 300), boundary_thickness=50,
                 collision_types=None, thing_categories=None):
        """Creates a new world with four boundary walls

        Parameters:
            grid_size (tuple<int, int>): The (column, row) size of the grid
            cell_expanse (int): The size (i.e. width/height) of each grid cell
            gravity (tuple<int, int>): The default gravity of the system
            boundary_thickness (int): The thickness of the boundary walls
            collision_types (dict<str: int>):
                    Mapping of collision types to unique numbers
                    Defaults to COLLISZION_TYPES constant
            thing_categories (dict<str: int>):
                    Mapping of thing categories to unique powers of 2
                    Defaults to PHYSZICAL_THING_CATEGORIES constant

        """
        if collision_types is None:
            collision_types = COLLISION_TYPES
        self._collision_types = collision_types

        if thing_categories is None:
            thing_categories = PHYSICAL_THING_CATEGORIES
        self._thing_categories = thing_categories

        self._space = pymunk.Space()

        self._space.gravity = gravity

        self._grid_size = grid_size
        self._cell_expanse = cell_expanse

        self._pixel_size = tuple(grid * cell_expanse for grid in grid_size)

        self._create_boundaries(boundary_thickness)

        self._last_time = time.time()

    def get_space(self) -> pymunk.Space:
        """(pymunk.Space): Return the space used by the world."""
        return self._space

    def _create_boundaries(self, thickness):
        """Create boundary walls of given 'thickness'"""
        width, height = self._pixel_size

        walls = [
            ('top', (0 - thickness, 0 - thickness), (width + thickness, 0 - thickness)),
            ('bottom', (0 - thickness, height + thickness), (width + thickness, height + thickness)),
            ('left', (0 - thickness, 0 - thickness), (0 - thickness, height + thickness)),
            ('right', (width + thickness, 0 - thickness), (width + thickness, height + thickness)),
        ]

        for wall_id, top_left, bottom_right in walls:
            wall = BoundaryWall(wall_id, self._space.static_body,
                                top_left, bottom_right, thickness)

            self._space.add(wall.get_shape())

    def set_gravity(self, gravity_x, gravity_y):
        """Sets the gravity of the world

        Parameters:
            gravity_x (float): The x component of the gravity
            gravity_y (float): The y component of the gravity
        """
        self._space.gravity = (gravity_x, gravity_y)

    def get_pixel_size(self):
        """Returns the (width, height) size of the world"""
        return self._pixel_size

    def get_grid_size(self):
        """Returns the (column, row) size of the world grid"""
        return self._grid_size

    def get_cell_expanse(self) -> int:
        """Returns the expanse (width/height) of each grid cell"""
        return self._cell_expanse

    def step(self, game_data):
        """Steps the game world forward by one time step

        1. Advances all things in the game world forward by one time step
            step method is called on each thing, with:
                - time_delta: the time (in seconds) since the last step
                - game_data: the game_data parameter supplied to this method
        2. Applies/resolves physics

        Parameters:
            game_data (tuple<World, Player>): Arbitrary data to be passed on to all things
        """
        now = time.time()
        time_delta = now - self._last_time
        for shape in self._space.shapes:
            thing = shape.object

            if thing:
                thing.step(time_delta, game_data)

        self._space.step(STEP_SIZE)
        self._last_time = now

    def xy_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Converts pixel position (xy) to grid position"""
        return int(x // self._cell_expanse), int(y // self._cell_expanse)

    def grid_to_xy(self, x: int, y: int) -> Tuple[int, int]:
        """Converts grid position to pixel position of its top-left corner"""
        return x * self._cell_expanse, y * self._cell_expanse

    def grid_to_xy_centre(self, x: int, y: int) -> Tuple[int, int]:
        """Converts grid position to pixel position of its centre"""
        return int((x + .5) * self._cell_expanse), int((y + .5) * self._cell_expanse)

    def _wrap_callback(self, callback):
        """Wraps a pymunk collision callback into a more OOP form"""

        def wrapped_callback(arbiter, space, data):
            thing_a, thing_b = [s.object for s in arbiter.shapes]
            return callback(thing_a, thing_b, data['data'], arbiter)

        return wrapped_callback

    def add_collision_handler(self, collision_type_a, collision_type_b, data=None,
                              on_begin=None, on_separate=None, on_pre_solve=None, on_post_solve=None):
        """Adds a collision handler to the game world

        Parameters:
            collision_type_a (str): A collision type in
        """
        handler = self._space.add_collision_handler(self._collision_types[collision_type_a],
                                                    self._collision_types[collision_type_b])

        handler.data['data'] = data

        local_variables = locals()

        for key in COLLISION_HANDLER_CALLBACKS:
            callback = local_variables[f"on_{key}"]
            if callback:
                setattr(handler, key, self._wrap_callback(callback))

    def get_all_things(self) -> Iterable[Entity]:
        """Yields all physical things in this world, including boundary walls

        Yield:
            Entity
        """
        for shape in self._space.shapes:
            thing = shape.object

            if thing:
                yield thing

    def add_thing(self, thing: Entity, x: float, y: float, size: Tuple[float, float], collision_type=None,
                  categories=None, mass: float = 1, friction: float = 1):
        """Adds a thing to the game world centred at the position ('x', 'y')

        Parameters:
            thing (Entity): The entity to add to the game world
            x (float): The x-coordinate at which to place the thing
            y (float): The y-coordinate at which to place the thing
            size (tuple<float, float>): The (x, y) size of the thing
            collision_type (int): The collision type of the thing; should be a value of self._collision_types
            categories (int): The query categories of the thing; should be a bitwise combination of the
                              value of self._physical_thing_categories
            mass (float): The mass of the thing
            friction (float): The friction of the thing
        """
        width, height = size

        left = -width // 2
        right = left + width
        top = -height // 2
        bottom = top + height

        body = pymunk.Body(mass, pymunk.inf)
        body.position = x, y
        shape = pymunk.Poly(body, [(left, top), (left, bottom), (right, bottom), (right, top)])

        shape.object = thing
        if collision_type is not None:
            shape.collision_type = collision_type

        if categories is not None:
            shape.filter = pymunk.ShapeFilter(categories=categories)

        shape.friction = friction

        thing.set_shape(shape)
        self._space.add(body, shape)

    def remove_thing(self, thing: Entity):
        """Removes a thing from the world"""
        self._space.remove(thing.get_shape())

    def add_player(self, player: Player, x: float, y: float, mass: float = 100, friction: float = .5):
        """Adds a player to game world at the position ('x', 'y')"""
        dx = dy = int(self._cell_expanse * .4 - 2)

        body = pymunk.Body(mass, pymunk.inf)
        body.position = x, y

        shape = pymunk.Poly(body, [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)], radius=3)
        shape.friction = friction
        shape.collision_type = self._collision_types['player']
        shape.object = player
        shape.filter = pymunk.ShapeFilter(categories=self._thing_categories["player"])

        player.set_shape(shape)

        self._space.add(body, shape)

    def remove_player(self, player: Player):
        """Removes the player from the game world"""
        self._space.remove(player.get_shape())

    def add_block_to_grid(self, entity, column: int, row: int,
                         width: int, height: int, friction: float = 1.):
        """Adds a block to the game world at the grid cell centred at ('column', 'row')

        Parameters:
            item (Entity): The item to add to the grid
            column (int): The column of the grid cell at which to place the block
            row (int): The row of the grid cell at which to place the block
            width (int): The width in cells of this entity
            height (int): The height in cells of this entity
            friction (float): The friction on the surface of the block
        """

        left = column * self._cell_expanse
        right = (column + width) * self._cell_expanse
        top = row * self._cell_expanse
        bottom = (row + height) * self._cell_expanse

        shape = pymunk.Poly(self._space.static_body, [(left, top), (left, bottom), (right, bottom), (right, top)])
        shape.object = entity
        shape.group = 2

        shape.friction = friction
        shape.collision_type = self._collision_types["block"]
        shape.filter = pymunk.ShapeFilter(categories=self._thing_categories["block"])

        entity.set_shape(shape)
        self._space.add(shape)

    def add_block(self, block: Block, x: float, y: float, *args, **kwargs):
        """Adds a block to the game world at the grid cell that contains ('x', 'y')

        Parameters:
            block (Block): The block to add to the grid
            x (float): The x-coordinate of the position contained by the cell
            y (float): The y-coordinate of the position contained by the cell

            - See add_block_to_grid for other parameters
        """
        col, row = self.xy_to_grid(x, y)
        row -= block.get_cell_size()[1] - 1
        return self.add_block_to_grid(block, col, row,
                                      *block.get_cell_size(), *args, **kwargs)

    def get_block(self, x, y):
        """(Block) Returns a block on the point ('x', 'y'), or None if there is no block there

        Note: It is technically possible for multiple blocks to overlap, in which case
              this method will return one of those. This should never happen, though.
        """
        blocks = self._space.point_query((x, y), 0, pymunk.ShapeFilter(mask=self._thing_categories["block"]))

        if blocks:
            return blocks[0].shape.object

    def remove_block(self, block: Block):
        """Removes a block from the game world"""
        self.remove_thing(block)

    def add_item(self, item: DroppedItem, x: float, y: float, size: Tuple[float, float] = (8, 8),
                 mass: float = 2, friction: float = 1.):
        """Adds an item to the game world centred at the position ('x', 'y')

        Parameters:
            item (DroppedItem): The (physical) item to add to the game world
                                Note: this is an instance of DroppedItem, not Item!

            - See add_thing for other parameters
        """

        self.add_thing(item, x, y, size, collision_type=self._collision_types['item'],
                       categories=self._thing_categories["item"], mass=mass, friction=friction)

    def remove_item(self, item: DroppedItem):
        """Removes an item from the world"""
        self.remove_thing(item)

    def add_mob(self, mob: Mob, x: float, y: float, friction: float = 1.):
        """Adds a mob to the game world centred at the position ('x', 'y')

        Parameters:
            mob (Mob): The mob to add to the game world

            - See add_thing for other parameters
        """

        self.add_thing(mob, x, y, mob.get_size(), collision_type=self._collision_types['mob'],
                       categories=self._thing_categories["mob"], mass=mob.get_weight(), friction=friction)

    def remove_mob(self, mob: Mob):
        """Removes a mob from the world"""
        self.remove_thing(mob)

    def get_things_in_range(self, x: float, y: float, distance: float):
        """(list<Entity>) Returns all things within the given distance range from point ('x', 'y')"""
        queries = self._space.point_query((x, y), distance, pymunk.ShapeFilter(
            mask=pymunk.ShapeFilter.ALL_MASKS ^ self._thing_categories["wall"]))

        return [q.shape.object for q in queries]

    def get_things(self, x: float, y: float) -> [Entity]:
        """(list<Entity>) Returns all things on the point ('x', 'y')"""
        return self.get_things_in_range(x, y, 0)

    def get_thing(self, x: float, y: float) -> Entity:
        """(Entity) Returns a thing on the point ('x', 'y'), or None if there is no thing there

        Note: It is technically possible for multiple objects to overlap, in which case
              this method will return one of those. To get all things, see get_things
        """
        things = self.get_things(x, y)
        return things[0] if things else None

    def get_items(self, x: float, y: float, max_distance: float) -> [DroppedItem]:
        """(list<DroppedItem>) Returns all items within 'max_distance' from the point ('x', 'y')"""
        queries = self._space.point_query((x, y), max_distance,
                                          pymunk.ShapeFilter(mask=self._thing_categories["item"]))

        return [q.shape.object for q in queries]

    def get_mobs(self, x: float, y: float, max_distance: float) -> [Mob]:
        """(list<Mob>) Returns all mobs within 'max_distance' from the point ('x', 'y')"""
        queries = self._space.point_query((x, y), max_distance,
                                          pymunk.ShapeFilter(mask=self._thing_categories["mob"]))

        return [q.shape.object for q in queries]
