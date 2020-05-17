"""
High-level abstract classes to represent entities in the game world
"""

import pymunk

from typing import Tuple


class Entity:
    """The highest-level abstract representation of an entity in the game world

    Should not be instantiated directly.
    """

    _type = 0

    def __init__(self):
        self._shape: pymunk.Shape = None

    @classmethod
    def get_type(cls) -> int:
        """Get the unique group type of the entity, used for querying for groups
        of entities in an area.

        Must be a unique power of 2, less than 2 ^ 32
        """
        return 2 ** cls._type

    def resolve_shape(self, shape: pymunk.Shape, friction: float = 1.):
        """Resolve the shape of a method by setting appropriate entity groups

        Assigns the shapes object to the current entity.
        """
        shape.friction = friction
        shape.collision_type = self.get_type()
        shape.filter = pymunk.ShapeFilter(categories=self.get_type())
        shape.object = self

    def set_shape(self, shape: pymunk.Shape):
        """Set the pymunk physical shape of the entity.

        Parameters:
            shape (pymunk.Shape): The physical shape of the entity.
        """
        self._shape = shape

    def get_shape(self) -> pymunk.Shape:
        """(pymunk.Shape): Return the shape of the entity."""
        return self._shape

    def get_position(self) -> Tuple[float, float]:
        """(tuple<float, float>) Returns the (x, y) position of this thing in the world"""
        position = self._shape.body.position
        return position.x, position.y

    def step(self, time_delta: float, game_data):
        """Advance this thing by one time-step

        Parameters:
            time_delta (float): The amount of time that has passed since the last step, in seconds
            game_data (tuple<World, Player>): Arbitrary data supplied by the app class
        """
        pass

    def on_hit(self, event: pymunk.Arbiter, data):
        """Event handler for a player colliding with the entity.

        Parameters:
            event (pymunk.Arbiter): Details on the collision event.
            data (tuple<World, Player): Useful data to use to process the collision.
        """
        pass


class DynamicEntity(Entity):
    """An entity that has the ability to move with a velocity.

    This entity will have an associated health.

    Should not be instantiated directly.
    """

    def __init__(self, max_health=20):
        super().__init__()

        self._health = self._max_health = max_health
        self._jumping = False

    def change_health(self, change):
        """Increases the dynamic thing's health by 'change (float)'"""
        self._health += change

        if self._health < 0:
            self._health = 0
        elif self._health > self._max_health:
            self._health = self._max_health

    def get_max_health(self):
        """(float) Returns the maximum health of the dynamic entity."""
        return self._max_health

    def get_health(self):
        """(float) Returns the dynamic thing's health"""
        return self._health

    def is_dead(self):
        """(bool) Returns True iff this thing is dead"""
        return self._health <= 0

    def get_velocity(self):
        """Returns the velocity of this dynamic thing

        Return:
            tuple<float, float>: The (x, y) components of the velocity
        """
        return self.get_shape().body.velocity

    def set_velocity(self, velocity: Tuple[float, float]):
        """Sets the velocity of this dynamic thing to 'velocity'

        Parameters:
            velocity (tuple<float, float>):
                    The (x, y) components of the new velocity
        """
        self.get_shape().body.velocity = velocity

    def is_jumping(self) -> bool:
        """(bool): Return whether or not the player is jumping currently."""
        return self._jumping

    def set_jumping(self, jumping: bool):
        """Set whether the player is currently jumping."""
        self._jumping = jumping


class BoundaryWall(Entity):
    """A boundary wall to prevent movement off the edge of the game world"""

    _type = 1

    def __init__(self, wall_id: str, body: pymunk.Shape,
                 top_left: Tuple[float, float], bottom_right: Tuple[float, float],
                 thickness: float):
        """Constructor

        Parameters:
            wall_id (str): The unique id of this wall (e.g. 'left', 'top', etc.)
        """
        super().__init__()

        self._id = wall_id
        self._shape = shape = pymunk.Segment(body, top_left, bottom_right, thickness)
        self.resolve_shape(shape)

    def get_id(self) -> str:
        """(str) Returns the unique id of this wall"""
        return self._id

    def get_position(self) -> Tuple[float, float]:
        """(tuple<float, float>) Returns the position of the centre of this wall"""
        x, y = self.get_shape().bb.center()
        return x, y

    def __repr__(self):
        return f"BoundaryWall({self._id!r})"
