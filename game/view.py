"""
View classes for the sandbox game
"""

import tkinter as tk
from typing import Iterable, Tuple, List
from functools import singledispatch, update_wrapper

import pymunk

from game.entity import Entity
from game.block import Block
from game.item import DroppedItem
from game.mob import Mob


# Warning: You do not need to understand how this function works
def singledispatchmethod(func):
    """Wrapper over the functools.singledispatch function which considers
    the type of the second parameter rather than the first parameter.

    This is useful for methods where the first parameter is always self.

    Note: this is a built-in feature of Python 3.8
    """
    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        return dispatcher.dispatch(args[1].__class__)(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


class ViewRenderer:
    """
    Renderer class that informs the view of how entities within the game should
    be rendered.

    The draw method is the main rendering router. It utilizes single method
    dispatch to appropriately render entities.

    Each entity draw method must take the following parameters:
        instance (Entity): The entity to draw
        shape (pymunk.Shape): The entities shape in the world
        view (tk.Canvas): The canvas on which to draw the entity
        offset (tuple<int, int>): The offset of the logical view from the canvas.

    To implement a new view method, add a decorator to the draw method of the form:
        @ViewRenderer.draw.register(Type)
    Where Type would be the class of the entity you wish to render.
    """

    def __init__(self, block_images, item_images, mob_images):
        """
        Construct a new ViewRouter with appropriate entity id to image file mappings.

        Parameters:
             block_images (dict<str: str>): A mapping of block ids to their respective images
             item_images (dict<str: str>): A mapping of item ids to their respective images
             mob_images (dict<str: str>): A mapping of mob ids to their respective images
        """
        super().__init__()

        self._images = {}

        self._block_images = block_images
        self._item_images = item_images
        self._mob_images = mob_images

    def load_image(self, file: str) -> tk.PhotoImage:
        """Load an image in the file location of images/{file}.png or images/{file}.gif

        Caches the image within the class so it can be drawn within the canvas.
        """
        if file in self._images:
            return self._images[file]

        try:
            image = tk.PhotoImage(file="images/" + file + ".png")
        except tk.TclError:
            image = tk.PhotoImage(file="images/" + file + ".gif")
        self._images[file] = image

        return image

    @singledispatchmethod
    def draw(self, instance: Entity, shape: pymunk.Shape,
             view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        """Method to draw the canvas elements for the given entity.

        Using the singledispatchmethod annotation the functionality of the draw
        method is overloaded by different entity types.
        Any methods registered to this method using the @draw.register annotation
        will overload the instance parameter.

        Parameters:
            instance (Entity): The entity to draw
            shape (pymunk.Shape): The entities shape in the world
            view (tk.Canvas): The canvas on which to draw the entity
            offset (tuple<int, int>): The offset of the logical view from the canvas.
        """
        return [view.create_rectangle(shape.bb.left + offset[0], shape.bb.top,
                                      shape.bb.right + offset[0], shape.bb.bottom,
                                      fill='black', tag='undefined')]

    @draw.register(Block)
    def _draw_block(self, instance: Block, shape: pymunk.Shape,
                    view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.load_image(self._block_images[instance.get_id()])
        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    @draw.register(DroppedItem)
    def _draw_physical_item(self, instance: DroppedItem, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.load_image(self._item_images[instance.get_id()])
        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="item")]

    @draw.register(Mob)
    def _draw_mob(self, instance: Mob, shape: pymunk.Shape,
                        view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.load_image(self._mob_images[instance.get_id()])
        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="mob")]


class GameView(tk.Canvas):
    """A view class for the sandbox game, with convenience methods to draw various parts of the UI"""

    def __init__(self, master, size, physical_view_router: ViewRenderer):
        """Constructor

        Parameters:
            master (tk.Tk | tk.Toplevel | tk.Frame): The tkinter master widget
            size (tuple<int, int>): The (width, height) size of the view, in pixels
            physical_view_router (ViewRenderer):
                    View router that facilitates drawing of physical items through
                    calling draw method with:
                        (entity, entities shape, self (canvas), offset)
        """
        width, height = size
        super().__init__(master, width=width, height=height, bg="#6080ff")

        self._world_view_router = physical_view_router
        self._offset = (0, 0)

    def shift(self, offset: Tuple[int, int]):
        """Shift the view offset by the given offset.

        Parameters:
            offset (tuple<int, int>): X and Y pixel offsets of the view.
        """
        self._offset = (self._offset[0] + offset[0],
                        self._offset[1] + offset[1])

    def set_offset(self, offset: Tuple[int, int]):
        """Sets the offset of the logical view to the given offset pari."""
        self._offset = offset

    def get_offset(self) -> Tuple[int, int]:
        """(tuple<int, int>): Return the X and Y pixel offsets of the view."""
        return self._offset

    def draw_entities(self, things: Iterable[Entity]):
        """Draws all entities, according to their draw method (on the view renderer)

        Parameters:
            things (iterable<Entity>): The entities to draw.
        """
        for thing in things:
            shape = thing.get_shape()

            self._world_view_router.draw(thing, shape, self, self._offset)
