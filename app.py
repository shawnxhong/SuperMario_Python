"""
Simple 2d world where the player can interact with the items in the world.
"""

__author__ = "shawnxhong"
__copyright__ = "assignment of The University of Queensland, 2019"

import math
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Tuple, List
from PIL import ImageTk, Image, ImageOps
from threading import Timer

import pymunk

from game.block import Block, MysteryBlock
from game.item import DroppedItem
from game.entity import Entity, BoundaryWall
from game.mob import Mob, CloudMob, Fireball
from game.view import GameView, ViewRenderer
from game.util import get_collision_direction
from game.item import Coin
from game.world import World

from player import Player
from level import load_world, WorldBuilder


BLOCK_SIZE = 2 ** 4
MAX_WINDOW_SIZE = (1080, math.inf)

GOAL_SIZES = {
    "flag": (0.2, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    '^': 'cube',
    'b': 'bounce',
    'S': 'switches',
    'I': 'flag',
    '=': 'tunnel',
}


ITEMS = {
    'C': 'coin',
    '*': 'star',
    'f': 'flower',
}

MOBS = {
    '&': "cloud",
    '@': 'mushroom',
    'g': 'gang'
}


class Switch(Block):
    """
    A block that controls the hidden/visible state of the bricks near by.
    If walked by the player on top, the bricks near by get hidden for 10 seconds.
    The active state is whether the switch can be turn on again.
    """
    _id = "switches"

    def __init__(self):
        super().__init__()
        self._active = True

    def is_active(self):
        """(bool) Returns True iff this switch is ready to work"""
        return self._active

    def set_active(self, active: bool):
        """Set whether the switch is ready to work or not."""
        self._active = active

    def on_hit(self, event, data):
        """
        Callback collision with player event handler
        """
        world, player = data
        brick_list = []
        if get_collision_direction(player, self) != "A":
            return

        if self.is_active():
            self._active = False

            x, y = self.get_position()
            things = world.get_things_in_range(x, y, 60)
            for thing in things:
                if thing._type == 2 and thing.get_id() == 'brick':
                    x_brick, y_brick = thing.get_position()
                    brick_list.append((thing, x_brick, y_brick))
                    world.remove_block(thing)

            #  count down 10 seconds to set the switch back to on, and bring back the bricks
            timer_active = Timer(10, self.set_active, [True])
            timer_active.start()
            timer_blocks = Timer(10, self.blocks_recover, [brick_list, world])
            timer_blocks.start()

    def blocks_recover(self, brick_list, world: World):
        """Recover the hidden bricks
        Parameters:
            brick_list (list): store the bricks to be recovered and their coordinate
             looks like this : [(brick_object, x, y),]
        """
        for n in brick_list:
            brick, x, y = n
            world.add_block(brick, x, y)


class Bounce(Block):
    """a type of block which will propel the player into the air when they walk over or jump on top of the block.
    """
    _id = "bounce"

    def __init__(self):
        super().__init__()
        self._active = False

    def is_active(self):
        """(bool) Returns True iff it is on"""
        return self._active

    def set_active(self, active: bool):
        """Set whether it is on or not."""
        self._active = active

    def on_hit(self, event, data):
        """Callback collision with player event handler."""
        world, player = data
        if get_collision_direction(player, self) == "A":
            self._active = True
            player.set_velocity((0, -400))
            timer = Timer(0.5, self.set_active, [False])  # this is for the animation
            timer.start()


class Mushroom(Mob):
    """"
    A mushroom-look monster that moves slowly. Can be kill when jumped on.
    """
    _id = "mushroom"

    def __init__(self):
        super().__init__(self._id, size=(16, 16), weight=800, tempo=-30)
        self._squished = False

    def is_squished(self):
        """(bool) Returns True iff it is squished"""
        return self._squished

    def set_squished(self, squished: bool):
        """Set whether it is squished or not."""
        self._squished = squished

    def on_hit(self, event: pymunk.Arbiter, data):
        """Callback collision with player event handler."""
        world, player = data
        if get_collision_direction(player, self) == "A":
            self.set_squished(True)
            player.set_velocity((0, -100))  # player slightly bounce off
            self.set_tempo(0)  # stop moving when squished
            #  destroy the mob after 0.4 seconds. just for the animation
            timer = Timer(0.4, world.remove_mob, [self])
            timer.start()
        elif get_collision_direction(player, self) == "R":
            player.change_health(-1)
            player.set_velocity((50, 0))
            self.set_tempo(-self.get_tempo())
        elif get_collision_direction(player, self) == "L":
            player.change_health(-1)
            player.set_velocity((-50, 0))
            self.set_tempo(-self.get_tempo())


class Gang(Mob):
    """
    A monster looks like gangster which seeks out the player on the ground
    """
    _id = "gang"

    def __init__(self):
        super().__init__(self._id, size=(16, 16), weight=800, tempo=-80)
        self._squished = False

    def is_squished(self):
        """(bool) Returns True iff it is squished"""
        return self._squished

    def set_squished(self, squished: bool):
        """Set whether it is squished or not."""
        self._squished = squished

    def on_hit(self, event: pymunk.Arbiter, data):
        """Callback collision with player event handler."""
        world, player = data
        if get_collision_direction(player, self) == "A":
            self.set_squished(True)
            player.set_velocity((0, -100))
            self.set_tempo(0)  # stop moving when squished
            #  destroy the mob after 0.4 seconds. just for the animation
            timer = Timer(0.4, world.remove_mob, [self])
            timer.start()
        elif get_collision_direction(player, self) == "R":
            player.change_health(-1)
            player.set_velocity((50, 0))
        elif get_collision_direction(player, self) == "L":
            player.change_health(-1)
            player.set_velocity((-50, 0))

    def step(self, time_delta, game_data):
        """Move towards the player"""
        world, player = game_data
        vx, vy = self.get_velocity()

        mob_x, mob_y = self.get_position()
        player_x, player_y = player.get_position()

        # move towards the player
        if player_x < mob_x:
            vx = self.get_tempo()
        elif player_x > mob_x:
            vx = -self.get_tempo()

        self.set_velocity((vx, vy))


class Star(DroppedItem):
    """
    A type of item that makes the player invincible for 10 seconds
    """
    _id = "star"

    def __init__(self):
        super().__init__()

    def collect(self, player):
        """Collect star, set the player to be invincible"""
        player.set_niubi(True)
        timer = Timer(10, player.set_niubi, [False])
        timer.start()


class Flower(DroppedItem):
    """
    A type of item that enable the player to shoot bullet
    """
    _id = "flower"

    def __init__(self):
        super().__init__()

    def collect(self, player):
        """Collect flower, enable the player to shoot"""
        player.set_shoot(True)


class Flag(Block):
    """
    When a player collides with this, immediately take the player to the next level.
    If the player lands on top of the flag pole, their health should be increased.
    """
    _id = "flag"

    def __init__(self):
        super().__init__()

    def get_cell_size(self):
        return GOAL_SIZES.get("flag")

    def on_hit(self, event, data):
        world, player = data
        if get_collision_direction(player, self) == "A":
            player.change_health(1)


class Tunnel(Block):
    """
    By default this should act as a normal block.
    If the player presses the down key while standing on top of this block, the player should be taken to another level.
    """
    _id = "tunnel"

    def __init__(self):
        super().__init__()

    def get_cell_size(self):
        return GOAL_SIZES.get("tunnel")


class BulletLeft(Mob):
    """The Bullet mob is a moving entity that moves left
    When colliding with the player or other mob it will cause damage and explode.
    """
    _id = "bullet_l"

    def __init__(self):
        super().__init__(self._id, size=(12, 12), weight=40, tempo=-300)


class BulletRight(Mob):
    """The Bullet mob is a moving entity that moves right
    When colliding with the player or other mob it will cause damage and explode.
    """
    _id = "bullet_r"

    def __init__(self):
        super().__init__(self._id, size=(12, 12), weight=40, tempo=300)


class SpriteSheetReader:
    """
    Class used to grab images out of a sprite sheet.
    All the cropped images are stored in __init__ to avoid multiple cropping.
    Otherwise the game will be extremely slow
    """
    def __init__(self):
        # crop player right side images
        self._player_right = []
        img = Image.open('spritesheets/characters.png')
        for i in range(1, 4):
            im = img.crop((80 + i * 17, 34, 96 + i * 17, 50))
            self._player_right.append(ImageTk.PhotoImage(im))

        # crop player left side images
        self._player_left = []
        img = Image.open('spritesheets/characters.png')
        for i in range(1, 4):
            im = img.crop((80 + i * 17, 34, 96 + i * 17, 50))
            im_flip = ImageOps.mirror(im)
            self._player_left.append(ImageTk.PhotoImage(im_flip))

        # crop player jump/fall images, first one jump, second on fall
        self._player_air = []
        img = Image.open('spritesheets/characters.png')
        im = img.crop((80 + 5 * 17, 34, 96 + 5 * 17, 50))
        self._player_air.append(ImageTk.PhotoImage(im))
        fall = img.crop((80 + 6 * 17, 34, 96 + 6 * 17, 50))
        self._player_air.append(ImageTk.PhotoImage(fall))

        # crop coin spinning images
        self._coin = []
        img = Image.open("spritesheets/items.png")
        for i in range(2):
            im = img.crop((0 + i * 16, 112, 16 + i * 16, 127))
            self._coin.append(ImageTk.PhotoImage(im))
        im = img.crop((0, 96, 16, 112))
        self._coin.append(ImageTk.PhotoImage(im))

        # crop mushroom walking images
        self._mushroom = []
        img = Image.open("spritesheets/enemies.png")
        for i in range(2):
            im = img.crop((0 + i * 16, 16, 16 + i * 16, 32))
            self._mushroom.append(ImageTk.PhotoImage(im))

        # crop the mushroom squished image
        self._dead_mushroom = []
        img = Image.open("spritesheets/enemies.png")
        im = img.crop((0 + 2 * 16, 16, 16 + 2 * 16, 32))
        self._dead_mushroom.append(ImageTk.PhotoImage(im))

        # crop bounce block image
        self._bounce = []
        img = Image.open("spritesheets/items.png")
        for i in range(3):
            im = img.crop((80 + i * 16, 0, 96 + i * 16, 32))
            self._bounce.append(ImageTk.PhotoImage(im))

        # crop gang monster images
        self._gang = []
        img = Image.open("spritesheets/enemies.png")
        for i in range(3,5):
            im = img.crop((0 + i * 16, 16, 16 + i * 16, 32))
            self._gang.append(ImageTk.PhotoImage(im))

        # crop the squished gang monster image
        self._dead_gang = []
        img = Image.open("spritesheets/enemies.png")
        im = img.crop((0 + 5 * 16, 16, 16 + 5 * 16, 32))
        self._dead_gang.append(ImageTk.PhotoImage(im))

        # crop bullet image
        self._bullet = []
        img = Image.open("spritesheets/items.png")
        im = img.crop((114, 146, 126, 158))
        self._bullet.append(ImageTk.PhotoImage(im))

        # crop flower image
        self._flower = []
        img = Image.open("spritesheets/items.png")
        im = img.crop((0, 32, 16, 48))
        self._flower.append(ImageTk.PhotoImage(im))

    def player_right(self) -> list:
        """
        Return: List[tk.PhotoImage]: player walking right
        """
        return self._player_right

    def player_left(self) -> list:
        """
        Return: List[tk.PhotoImage]: player walking left
        """
        return self._player_left

    def player_air(self):
        """
        Return: List[tk.PhotoImage]: player in the air, the first one is jumping, the second one is falling
        """
        return self._player_air

    def coin_rotate(self):
        """
        Return: List[tk.PhotoImage]: coin spinning
        """
        return self._coin

    def mushroom(self):
        """
        Return: List[tk.PhotoImage]: mushroom walking
        """
        return self._mushroom

    def dead_mushroom(self):
        """
        Return: List[tk.PhotoImage]: squished mushroom
        """
        return self._dead_mushroom

    def gang(self):
        """
        Return: List[tk.PhotoImage]: gang walking
        """
        return self._gang

    def dead_gang(self):
        """
        Return: List[tk.PhotoImage]: gang squished
        """
        return self._dead_gang

    def bounce(self):
        """
        Return: List[tk.PhotoImage]: bounce block bouncing
        """
        return self._bounce

    def bullet(self):
        """
        Return: List[tk.PhotoImage]: bullet image
        """
        return self._bullet

    def flower(self):
        """
        Return: List[tk.PhotoImage]: flower image
        """
        return self._flower


def create_block(world: World, block_id: str, x: int, y: int, *args):
    """Create a new block instance and add it to the world based on the block_id.

    Parameters:
        world (World): The world where the block should be added to.
        block_id (str): The block identifier of the block to create.
        x (int): The x coordinate of the block.
        y (int): The y coordinate of the block.
    """
    block_id = BLOCKS[block_id]
    if block_id == "mystery_empty":
        block = MysteryBlock()
    elif block_id == "mystery_coin":
        block = MysteryBlock(drop="coin", drop_range=(3, 6))
    elif block_id == "bounce":
        block = Bounce()
    elif block_id == 'switches':
        block = Switch()
    else:
        block = Block(block_id)

    world.add_block(block, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_item(world: World, item_id: str, x: int, y: int, *args):
    """Create a new item instance and add it to the world based on the item_id.

    Parameters:
        world (World): The world where the item should be added to.
        item_id (str): The item identifier of the item to create.
        x (int): The x coordinate of the item.
        y (int): The y coordinate of the item.
    """
    item_id = ITEMS[item_id]
    if item_id == "coin":
        item = Coin()
    elif item_id == "star":
        item = Star()
    elif item_id == 'flower':
        item = Flower()
    else:
        item = DroppedItem(item_id)

    world.add_item(item, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_mob(world: World, mob_id: str, x: int, y: int, *args):
    """Create a new mob instance and add it to the world based on the mob_id.

    Parameters:
        world (World): The world where the mob should be added to.
        mob_id (str): The mob identifier of the mob to create.
        x (int): The x coordinate of the mob.
        y (int): The y coordinate of the mob.
    """
    mob_id = MOBS[mob_id]
    if mob_id == "cloud":
        mob = CloudMob()
    elif mob_id == "fireball":
        mob = Fireball()
    elif mob_id == "mushroom":
        mob = Mushroom()
    elif mob_id == 'gang':
        mob = Gang()
    elif mob_id == 'bullet_l':
        mob = BulletLeft()
    elif mob_id == 'bullet_r':
        mob = BulletRight()
    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))


BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
    "bounce": "bounce_block",
    "switches": "switch",
    "flag": "flag",
    "tunnel": "tunnel",
}

ITEM_IMAGES = {
    "coin": "coin_item",
    "star": "star",
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down",
    "mushroom": "mushroom",
}


class MarioViewRenderer(ViewRenderer):
    """A customised view renderer for a game of mario."""
    def __init__(self, block_images, item_images, mob_images):
        super().__init__(block_images, item_images, mob_images)
        self.spritesheet = SpriteSheetReader()

        self.player_right_index = 0
        self.player_left_index = 0
        self._coin_index = 0
        self._mob_index = 0
        self._bounce_index = 0

    @ViewRenderer.draw.register(Player)
    def _draw_player(self, instance: Player, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if shape.body.velocity.x == 0:
            if shape.body.velocity.y > 0:
                image = self.spritesheet.player_air()[1]  # falling
            elif shape.body.velocity.y < 0:
                image = self.spritesheet.player_air()[0]  # jump
            else:
                image = self.load_image("mario_right")
        elif shape.body.velocity.x > 0:
            # the player_right_index is added up at a constant speed, index only has three possible value 0, 1, 2.
            # the images in the list is hence loaded periodically.
            # The loading speed can be controlled by setting different value e.g. if set 6 to 18 the speed goes down.
            index = (self.player_right_index + 1) // 6 % 3
            image = self.spritesheet.player_right()[index]
            self.player_right_index += 1
        else:
            index = (self.player_left_index + 1) // 6 % 3
            image = self.spritesheet.player_left()[index]
            self.player_left_index += 1

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="player")]

    @ViewRenderer.draw.register(MysteryBlock)
    def _draw_mystery_block(self, instance: MysteryBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("coin")
        else:
            image = self.load_image("coin_used")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    @ViewRenderer.draw.register(Switch)
    def _draw_switch(self, instance: Switch, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image('switch')
        else:
            image = self.load_image('switch_pressed')

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    @ViewRenderer.draw.register(Coin)
    def _draw_coin(self, instance: Coin, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        index = (self._coin_index + 1) // 30 % 2
        image = self.spritesheet.coin_rotate()[index]
        self._coin_index += 1

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="coin")]

    @ViewRenderer.draw.register(Mushroom)
    def _draw_mushroom(self, instance: Mushroom, shape: pymunk.Shape,
                   view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if not instance.is_squished():
            index = (self._mob_index + 1) // 20 % 2
            image = self.spritesheet.mushroom()[index]
            self._mob_index += 1
        else:
            image = self.spritesheet.dead_mushroom()[0]

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="mushroom")]

    @ViewRenderer.draw.register(Bounce)
    def _draw_bounce(self, instance: Bounce, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            index = (self._bounce_index + 1) // 72 % 3
            image = self.spritesheet.bounce()[index]
            self._bounce_index += 1
        else:
            image = self.load_image('bounce_block')
        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="bounce")]

    @ViewRenderer.draw.register(Gang)
    def _draw_gang(self, instance: Gang, shape: pymunk.Shape,
                       view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if not instance.is_squished():
            index = (self._mob_index + 1) // 20 % 2
            image = self.spritesheet.gang()[index]
            self._mob_index += 1
        else:
            image = self.spritesheet.dead_gang()[0]

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="gang")]

    @ViewRenderer.draw.register(BulletLeft)
    def _draw_bullet_left(self, instance: BulletLeft, shape: pymunk.Shape,
                          view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.spritesheet.bullet()[0]

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="bullet_l")]

    @ViewRenderer.draw.register(BulletRight)
    def _draw_bullet_right(self, instance: BulletRight, shape: pymunk.Shape,
                           view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.spritesheet.bullet()[0]

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="bullet_r")]

    @ViewRenderer.draw.register(Flower)
    def _draw_flower(self, instance: Flower, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        image = self.spritesheet.flower()[0]

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="flower")]


class MarioApp:
    """High-level app class for Mario, a 2d platformer"""
    _world: World

    def __init__(self, master: tk.Tk):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self._master = master
        # default configuration setting
        self._level = "level1.txt"
        self._gravity = (0, 300)
        self._max_health = 5
        self._mass = 100
        self._x = BLOCK_SIZE
        self._y = BLOCK_SIZE
        self._max_velocity = 500
        self._config = {}

        self._master.update_idletasks()
        self.load_config()

        world_builder = WorldBuilder(BLOCK_SIZE, self._gravity, fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder

        self._player = Player(max_health=self._max_health)
        self._player.set_jumping(True)
        self._player.set_shoot(False)

        self.reset_world(self._level)

        self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
        self._view = GameView(master, size, self._renderer)
        self._view.pack()

        self.bind()

        self.menu_bar()

        # create the character status bar
        self.status_bar = Status(master)
        self.status_bar.pack()

        # Wait for window to update before continuing
        master.update_idletasks()
        self.step()

    def read_config(self, filename: str):
        """
        To read the configuration data from the txt file
        Parameter:
            filename (str): filename
        Return (dictionary): looks like {"level":{'key':value, 'key': value},}
        """
        config = {}
        with open(filename) as hand:
            for line in hand:
                line = line.rstrip()
                if line.startswith("==") and line.endswith("=="):
                    # heading line
                    heading = line[2:-2]
                    config[heading] = {}
                else:
                    # attribute line
                    attr, _, value = line.partition(' : ')
                    config[heading][attr] = value
        hand.close()
        return config

    def load_config(self):
        """
        load the read configuration to the default settings
        If the configuration file is invalid, exit the game with an error message.
        """
        config_file = filedialog.askopenfilename()
        try:
            config = self.read_config(config_file)
            self._config = config
            self._level = config['World']['start']
            self._gravity = (0, int(config['World']['gravity']))
            self._x = float(config['Player']['x'])
            self._y = float(config['Player']['y'])
            self._mass = int(config['Player']['mass'])
            self._max_health = int(config['Player']['health'])
            self._max_velocity = int(config['Player']['max_velocity'])
        except UnboundLocalError:
            tk.messagebox.showerror('Error', 'Bad Input')
            self._master.destroy()

    def reset_world(self, new_level):
        self._world = load_world(self._builder, new_level)
        self._world.add_player(self._player, self._x, self._y, self._mass)
        self._builder.clear()

        self._setup_collision_handlers()
    
    def menu_bar(self):
        """
        Create a menu bar
        """
        menubar = tk.Menu(self._master)
        self._master.config(menu=menubar)
        # within the menu bar create the file menu
        filemenu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=filemenu)
        # within the file menu create the file processing options
        filemenu.add_command(label="Load Level", command=self.load_level)
        filemenu.add_command(label="Reset Level", command=self.reset_level)
        filemenu.add_command(label="High Score", command=self.show_scores)
        filemenu.add_command(label="Exit", command=self.exit)

    def load_level(self):
        """
        Input a level file and load that level
        """
        filename = filedialog.askopenfilename()
        if filename:
            self.reset_world(filename)
        self._level = filename

    def reset_level(self):
        """
        Reset the current level and all player progress
        """
        ans = messagebox.askokcancel('Restart Game', 'Restart Game?')
        if ans:
            self.reset_world(self._level)
            self._player.clear_score()
            self._player.change_health(self._player.get_max_health())
            self.redraw_status()
        else:
            self._master.destroy()

    def exit(self):
        """
        exit the game
        """
        ans = messagebox.askokcancel('Exit Game', 'Really exit?')
        if ans:
            self._master.destroy()

    def game_over(self):
        """
        See if the player is dead. If so, ask if want to start a new game or just quit.
        """
        if self._player.is_dead():
            ans = messagebox.askokcancel('Player is dead', 'Start Over?')
            if ans:
                self.reset_world('level1.txt')
                self._level = 'level1.txt'
                self._player.clear_score()
                self._player.change_health(self._player.get_max_health())
                self.redraw_status()
            else:
                self._master.destroy()

    def read_score(self):
        """
        read the score records from the text file
        Return:
            score (dictionary): looks like this {'level':[('name', int), ('name', int), ('name', int), ], }
        """
        score = {}
        with open("high_score.txt") as hand:
            for line in hand:
                line = line.rstrip()
                if line.startswith("**") and line.endswith("**"):
                    heading = line[2:-2]
                    score[heading] = []
                else:
                    record = line.split(' : ')
                    score[heading].append((record[0], int(record[1])))
        hand.close()
        return score

    def update_score(self):
        """
        ask for the name of the current player and get the current score.
        read the high score records and see if the current player gets into the top 10 high scores for the current level
        if so, update the high score text file with the lowest one replace
        """
        name = tk.simpledialog.askstring("your name", "what's your name", parent=self._master)  # 这人名字
        score = self._player.get_score()
        score_records = self.read_score()
        # rank the record list of the current level from low to high by score in the dictionary
        score_records[self._level].sort(key=lambda x: x[1])
        if len(score_records[self._level]) < 10:
            score_records[self._level].append((name, score))
        elif score > score_records[self._level][0][1]:
            score_records[self._level][0] = (name, score)  # replace the one with the lowest score

        with open("high_score.txt", 'w') as handle:  # write back to the text file
            for k, v in score_records.items():
                handle.write('**{}**\n'.format(k))
                for n in v:
                    name, value = n
                    handle.write('{} : {}\n'.format(name, value))
        handle.close()

    def show_scores(self):
        """
        Display the score records in a window
        """
        score = self.read_score()
        score_window = tk.Toplevel(self._master)
        score_window.geometry('300x200')
        score_window.title(self._level.rstrip(".txt").capitalize() + ' Top 10 Scores')

        tk.Label(score_window, text="Top 10 Scores In This Level").pack(side=tk.TOP)
        tk.Label(score_window, text="\n".join('name：{}\tscore: {}'.format(k, v)
                                              for (k, v) in score[self._level])).pack(side=tk.TOP)

    def get_next_level(self):
        """
        (str) Return the string of next level file name
        """
        return self._config[self._level]['goal']

    def load_next_level(self):
        """load the next level in world"""
        self.reset_world(self.get_next_level())

    def bind(self):
        """Bind all the keyboard events to their event handlers."""
        self._master.bind("<a>", self.key_press)
        self._master.bind("<Left>", self.key_press)
        self._master.bind("<d>", self.key_press)
        self._master.bind("<Right>", self.key_press)
        self._master.bind("<w>", self.key_press)
        self._master.bind("<Up>", self.key_press)
        self._master.bind("<space>", self.key_press)
        self._master.bind("<s>", self.key_press)
        self._master.bind("<Down>", self.key_press)
        self._master.bind("<b>", self.key_press)

    def key_press(self, e):
        """
        What to execute when certain key is pressed
        """
        key = e.keysym
        if key == 'a' or key == 'Left':
            self._move(-150, 0)
        elif key == 'd' or key == 'Right':
            self._move(150, 0)
        elif key == 'w' or key == 'Up' or key == 'space':
            self._jump()
        elif key == 's' or key == 'Down':
            self._duck()
        elif key == "b":
            self.shoot()

    def redraw_status(self):
        """
        Redraw the player status bar with the updated health and score value
        """
        self.status_bar.clear()
        self.status_bar.update_health(self._player.get_health(), self._player.is_niubi(), self._player)
        self.status_bar.update_score(self._player.get_score())

    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)
        self._view.draw_entities(self._world.get_all_things())
        self.redraw_status()

    def scroll(self):
        """Scroll the view along with the player in the center unless
        they are near the left or right boundaries
        """
        x_position = self._player.get_position()[0]
        half_screen = self._master.winfo_width() / 2
        world_size = self._world.get_pixel_size()[0] - half_screen

        # Left side
        if x_position <= half_screen:
            self._view.set_offset((0, 0))

        # Between left and right sides
        elif half_screen <= x_position <= world_size:
            self._view.set_offset((half_screen - x_position, 0))

        # Right side
        elif x_position >= world_size:
            self._view.set_offset((half_screen - world_size, 0))

    def step(self):
        """Step the world physics and redraw the canvas."""
        data = (self._world, self._player)
        self._world.step(data)

        self.scroll()
        self.redraw()
        self.game_over()
        self._master.after(10, self.step)  # refresh

    def _move(self, dx: int, dy: int):
        """
        move the player
        Parameter:
            dx (int): velocity on x axis
            dy (int): velocity on y axis
        """
        self._player.set_velocity((dx, dy))

    def _jump(self):
        """
        if the player is not jumping, make it jump, and change the jumping status to True.
        """
        if not self._player.is_jumping():
            self._move(0, -200)
            self._player.set_jumping(True)

    def _duck(self):
        """
        set the duck status of the player to True
        """
        self._player.set_duck(True)

    def shoot(self):
        """
        player shoots the bullet
        """
        x, y = self._player.get_position()
        vx, vy = self._player.get_velocity()
        if self._player.is_shoot:
            if vx >= 0:
                self._world.add_mob(BulletRight(), x + 16, y)
            else:
                self._world.add_mob(BulletLeft(), x - 16, y)
        else:
            print('不射')

    def _setup_collision_handlers(self):
        self._world.add_collision_handler("player", "item", on_begin=self._handle_player_collide_item)
        self._world.add_collision_handler("player", "block", on_begin=self._handle_player_collide_block,
                                          on_separate=self._handle_player_separate_block)
        self._world.add_collision_handler("player", "mob", on_begin=self._handle_player_collide_mob)
        self._world.add_collision_handler("mob", "block", on_begin=self._handle_mob_collide_block)
        self._world.add_collision_handler("mob", "mob", on_begin=self._handle_mob_collide_mob)
        self._world.add_collision_handler("mob", "item", on_begin=self._handle_mob_collide_item)

    def _handle_mob_collide_block(self, mob: Mob, block: Block, data,
                                  arbiter: pymunk.Arbiter) -> bool:
        if mob.get_id() == "fireball" or mob.get_id() == 'bullet_l' or mob.get_id() == 'bullet_r':
            if block.get_id() == "brick":
                self._world.remove_block(block)
                self._world.remove_mob(mob)
            else:
                self._world.remove_mob(mob)
        elif mob.get_id() == "mushroom":  # mushroom bounces back a little when encountering blocks
            if get_collision_direction(mob, block) == "R" or get_collision_direction(mob, block) == "L":
                mob.set_tempo(-mob.get_tempo())
        elif mob.get_id() == 'gang':  # gang jumps over the blocks when encountering them
            if get_collision_direction(mob, block) == "R":
                mob.set_velocity((50, -350))
            elif get_collision_direction(mob, block) == "L":
                mob.set_velocity((-50, -350))

        return True

    def _handle_mob_collide_item(self, mob: Mob, block: Block, data,
                                 arbiter: pymunk.Arbiter) -> bool:
        return False

    def _handle_mob_collide_mob(self, mob1: Mob, mob2: Mob, data,
                                arbiter: pymunk.Arbiter) -> bool:
        if mob1.get_id() == "fireball" or mob2.get_id() == "fireball":
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)
        elif mob1.get_id() == 'bullet_l' or mob1.get_id == 'bullet_r' or mob2.get_id() == 'bullet_l' or mob2.get_id == 'bullet_r':
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)
        elif mob1.get_id() == "gang" and mob2.get_id() == "mushroom":
            return False
        elif mob1.get_id() == "mushroom" and mob2.get_id() == "gang":
            return False
        elif mob1.get_id() == "gang" and mob2.get_id() == "gang":
            return False
        elif mob1.get_id() == "mushroom" and mob2.get_id() == "mushroom":
            mob1.set_tempo(-mob1.get_tempo())
            mob2.set_tempo(-mob2.get_tempo())
        else:
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)

        return False
    def _handle_player_collide_item(self, player: Player, dropped_item: DroppedItem,
                                    data, arbiter: pymunk.Arbiter) -> bool:
        """Callback to handle collision between the player and a (dropped) item. If the player has sufficient space in
        their to pick up the item, the item will be removed from the game world.

        Parameters:
            player (Player): The player that was involved in the collision
            dropped_item (DroppedItem): The (dropped) item that the player collided with
            data (dict): data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter): Data about a collision
                                      (see http://www.pymunk.org/en/latest/pymunk.html#pymunk.Arbiter)
                                      NOTE: you probably won't need this
        Return:
             bool: False (always ignore this type of collision)
                   (more generally, collision callbacks return True iff the collision should be considered valid; i.e.
                   returning False makes the world ignore the collision)
        """

        if dropped_item.get_id() == 'coin':
            dropped_item.collect(self._player)
            self._world.remove_item(dropped_item)
        elif dropped_item.get_id() == 'star':
            dropped_item.collect(self._player)
            self._world.remove_item(dropped_item)
        elif dropped_item.get_id() == 'flower':
            dropped_item.collect(self._player)
            self._world.remove_item(dropped_item)
        return False

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:

        if get_collision_direction(player, block) == "A":  # when player touch the blocks, set jumping to false
            self._player.set_jumping(False)

        if block.get_id() == "flag":
            if get_collision_direction(player, block) == "A":
                block.on_hit(arbiter, data)
            else:
                # tell the player to input their name and see if the score records need to be updated
                self.update_score()
                if self.get_next_level() == 'END':  # if there's no further level, ask if start over
                    ans = messagebox.askokcancel('Good job, you finish the game', 'Start Over?')
                    if ans:
                        self.reset_world('level1.txt')
                        self._level = 'level1.txt'
                        self._player.clear_score()
                        self._player.change_health(self._player.get_max_health())
                        self.redraw_status()
                    else:
                        self._master.destroy()
                else:
                    self.reset_world(self.get_next_level())
                    self._level = self.get_next_level()
        elif block.get_id() == "tunnel":
            if get_collision_direction(player, block) == "A" and self._player.is_duck() is True:
                self._player.set_duck(False)
                self.reset_world(self.get_next_level())
        elif block.get_id() == 'switches':
            if block.is_active():
                block.on_hit(arbiter, (self._world, player))

        block.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        if player.is_niubi():
            self._world.remove_mob(mob)
        elif player.is_shoot():
            player.set_shoot(False)
        else:
            mob.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        return True


class Status(tk.Frame):
    """
    The status bar widget for the player.
    """

    def __init__(self, master):
        super().__init__(master)
        self._master = master

        # canvas1 for the health bar, canvas2 for the score
        self._canvas1 = tk.Canvas(self._master, bg='black')
        self._canvas1.pack(side=tk.TOP, expand=1, fill=tk.X, ipady=2)
        self._canvas2 = tk.Canvas(self._master)
        self._canvas2.pack(side=tk.TOP)

        self.health = tk.Label(self._canvas1, text="", bg='green', width=154)
        self.health.pack(side=tk.LEFT, anchor=tk.W)

        tk.Label(self._canvas2, text="Score:").pack(side=tk.LEFT)
        self.score = tk.Label(self._canvas2, text="")
        self.score.pack(side=tk.LEFT)
    
    def update_health(self, health: int, niubi: bool, player: Player):
        """
        To update the health bar when health value changes
        Parameter:
            health (int): the current health value of the player
            niubi (bool): whether the player is invincible or not. Niubi means super invincible.
        """
        max_health = player.get_max_health()
        if health >= 0.5*max_health:
            self.health.configure(bg='green', width=int(154*(health/max_health)))
        elif 0.25*max_health <= health < 0.5*max_health:
            self.health.configure(bg='orange', width=int(154*(health/max_health)))
        elif health < 0.25*max_health:
            self.health.configure(bg='red', width=int(154*(health/max_health)))
        else:
            self.health.configure(bg='black', width=0)

        if niubi:
            self.health.configure(bg='yellow', width=154)

    def update_score(self, score: int):
        """
        To update the score when its value changes
        Parameter:
            score (int): current score value
        """
        self.score.configure(text="{0:>1}".format(score))

    def clear(self):
        """
        To clear the player status canvas.
        """
        self._canvas1.delete(tk.ALL)
        self._canvas2.delete(tk.ALL)


def main():
    root = tk.Tk()
    root.title("Mario")
    app = MarioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
