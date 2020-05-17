"""
Some utility & miscellany for the game engine
"""

from game.entity import DynamicEntity, Entity

ABOVE = "A"
BELOW = "B"
RIGHT = "R"
LEFT = "L"


def get_collision_direction(entity: DynamicEntity, other: Entity):
    """Get the direction where from which a collision event occurred.

    Parameters:
        entity (DynamicEntity): Colliding entity.
        other (Entity): The entity with which the colliding entity collided.

    Returns:
        (str): The direction the collision occurred in.

        "A" for Above
        "B" for Below
        "R" for Right
        "L" for Left
    """
    bb = entity.get_shape().bb
    cx, cy = bb.center()
    lx = cx - (cx - bb.left)/2
    rx = cx + (cx - bb.left)/2

    # direction mapping
    directions = [
        ((cx, bb.top), ABOVE),
        ((lx, bb.top), ABOVE),
        ((rx, bb.top), ABOVE),

        ((cx, bb.bottom), BELOW),
        ((lx, bb.bottom), BELOW),
        ((rx, bb.bottom), BELOW),

        ((bb.left, cy), RIGHT),
        ((bb.right, cy), LEFT)
    ]

    for pos, result in directions:
        if other.get_shape().point_query(pos)[0] < 0:
            return result


def euclidean_square_distance(position1: (float, float), position2: (float, float)):
    """(tuple<float, float>) Returns the euclidean (straight-line) distance between 'position1' & 'position2'

    Parameters:
        position1 (tuple<float, float>): The first point
        position2 (tuple<float, float>): The second point
    """
    x1, y1 = position1
    x2, y2 = position2

    return (x2 - x1) ** 2 + (y2 - y1) ** 2


def positions_in_range(position1, position2, max_distance):
    """(bool) Returns True iff position1 & position2 are within 'max_distance' from each other, in terms
    of euclidean distance

    Parameters:
        position1 (tuple<float, float>): The first point
        position2 (tuple<float, float>): The second point
        max_distance (float): The maximum distance between position1 & position2
    """
    return euclidean_square_distance(position1, position2) <= max_distance ** 2
