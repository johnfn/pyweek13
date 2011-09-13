import random
import sys
import os
import pygame
import pygame.font
import numpy as N
import math
import time
import spritesheet
from rendertext import render_textrect, TextRectException

#TODO: Move to untracted py file so there is no conflicts when someone changes this.
DEBUG = True

# Convention: directories will always have trailing slash.
ROOT_DIR = os.path.dirname(os.path.realpath(__file__)) + "/../"
DATA_DIR = ROOT_DIR + "data/"
SPRITE_DIR = DATA_DIR + "sprites/"
MAP_DIR = DATA_DIR + "maps/"
FONT_DIR = DATA_DIR + "fonts/"

# some Enums that I haven't bothered to namespace (yet)

RED = 0
GREEN = 1
BLUE = 2
COLORS = 3

LEFT = [-1, 0]
RIGHT = [1, 0]
UP = [0, -1]
DOWN = [0, 1]

GRAVITY = 3

UNCOLORED = 0
COLORED = 1

TILE_SIZE = 20
SIZE = (500, 500)
MAP_SIZE = 20
MAP_IN_PX = TILE_SIZE * MAP_SIZE
 
""" DECORATORS"""

component = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)

def extend(klass, name, *args, **kwargs):
  components = getattr(klass, 'components', [])[:]

  if name in components:
    return klass

  components.append(name)
  methods = dict(map(lambda m: [ m.__name__, m], args))
  methods.update(kwargs)
  methods["components"] = components
  new_type = type(klass)(name, (klass,), methods)
  return new_type

@component
def fallable(klass, gravity=GRAVITY):
  def update(self, entities):
    self.v[1] += gravity
    klass.update(self, entities)

  return extend(klass, 'fallable', update)

@component
def healthable(klass, health):
  def __init__(self, *args, **kwargs):
    klass.__init__(self, *args, **kwargs)
    self.health = health

  return extend(klass, 'healthable', __init__)

class Point:
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def __repr__(self):
    return "<Point x:%d y:%d>" % (self.x, self.y)

def sign(x):
  if x > 0: return 1
  if x < 0: return -1
  return 0


class BigMap:
  def __init__(self):
    self.contents = {}

  def keys_to_key(self, *keys):
    return "-".join([str(x) for x in keys])

  def put(self, value, *keys):
    self.contents[self.keys_to_key(keys)] = value

  def get(self, *keys):
    return self.contents[self.keys_to_key(keys)]

  def has(self, *keys):
    return self.keys_to_key(keys) in self.contents

#TODO: file_name -> just the "name.png" part, not the entire directory, when storing in BigMap.
def get_tilesheet_image(file_name, pos_x, pos_y, img_sz, saturation):
  assert(isinstance(saturation, list))

  if not get_tilesheet_image.loaded_sheets.has(file_name, pos_x, pos_y, saturation):
    new_sheet = spritesheet.spritesheet(file_name)
    width, height = dimensions = new_sheet.sheet.get_size()
    images = [[new_sheet.image_at((x, y, img_sz, img_sz), colorkey=(255,255,255))
            for y in range(0, height, img_sz)] for x in range(0, width, img_sz)]

    sat_levels = [UNCOLORED, 1]

    for r in sat_levels:
      for g in sat_levels:
        for b in sat_levels:
          rgb = [r,g,b]

          # O(N^5) SUCKA!!!!! (Not really.)

          for img_x in range(0, width/img_sz):
            for img_y in range(0, height/img_sz):
              img = images[img_x][img_y]
              get_tilesheet_image.loaded_sheets.put(Graphics.colorize(img, rgb), file_name, img_x, img_y, rgb)

  return get_tilesheet_image.loaded_sheets.get(file_name, pos_x, pos_y, saturation)

get_tilesheet_image.loaded_sheets = BigMap()

class Image:
  """An image that exists in the current room. """
  def __init__(self, file_name, file_pos_x, file_pos_y, my_x, my_y, img_sz, saturation=None):
    if saturation is None:
      saturation = [COLORED, UNCOLORED, UNCOLORED]

    assert(isinstance(saturation, list))

    self.img = get_tilesheet_image(SPRITE_DIR + file_name, file_pos_x, file_pos_y, img_sz, saturation)

    #Pygame makes you hangle images and their rects separately, it's kinda stupid.
    self.rect = self.img.get_rect()
    self.rect.x = my_x
    self.rect.y = my_y

  def xget(self):
    return self.rect.x
  
  def xset(self, value):
    print "ok..."
    self.rect.x = value

  x = property(xget, xset)

  @property
  def y(self):
    return self.rect.y

  @y.setter
  def y(self, value):
    self.rect.y = value

  def get_position(self):
    return (self.rect.x, self.rect.y)

  def set_position(self, position):
    self.rect.x = position[0]
    self.rect.y = position[1]

  def render(self, screen):
    screen.blit(self.img, self.rect)

class EntityManager:
  """Manages all entities in the game. Each entity should inherit from
  Entity."""
  def __init__(self):
    self.entities = []

  def add(self, entity):
    self.entities.append(entity)

  def update(self):
    for entity in self.entities:
      entity.update(self)

  def render(self, screen):
    # Sort by depth, if the entities have it.
    self.entities = sorted(self.entities, key=lambda entity: entity.depth() if hasattr(entity, 'depth') else -99999)

    for entity in self.entities:
      entity.render(screen)

  def get_one(self, func):
    results = [entity for entity in self.entities if func(entity)]
    assert len(results) == 1
    return results[0]

  def get_all(self, func):
    return [entity for entity in self.entities if func(entity)]

  def delete(self, obj):
    self.delete_all(lambda e: obj == e)

  def delete_all(self, func):
    """Delete all enetities E such that func(E) == True """

    entities_remaining = []
    for entity in self.entities:
      if not func(entity):
        entities_remaining.append(entity)

    self.entities = entities_remaining

class Entity(object):
  components = []

  @classmethod
  def has(cls, a):
    return a in cls.components

  def touches_point(self, point):
    return self.x <= point.x <= self.x + self.size and\
           self.y <= point.y <= self.y + self.size

  def touches_entity(self, other):
    assert self.x is not None
    assert other.x is not None

    points = [ Point(self.x,             self.y)
             , Point(self.x + self.size, self.y)
             , Point(self.x,             self.y + self.size)
             , Point(self.x + self.size, self.y + self.size)
             ]

    for point in points:
      if other.touches_point(point):
        return True

    return False

  def __init__(self, x, y, size):
    self.x = x
    self.y = y
    self.size = size
    self.v = [0, 0]

  def update(self, entities):
    raise NotImplementedException

  def render(self, screen):
    raise NotImplementedException

def bound(num, asymptote):
  a = abs(asymptote)
  if num < -a:
    return -a
  elif num > a:
    return a
  return num

class HUDIcon(Entity):
  """Icon that indicates R, G, or B mutations and whether they are in use or
  not."""

  def __init__(self, x, y, size, color, character):
    Entity.__init__(self, x, y, size)

    self.img = Image("hud.png", color, 0, x, y, size, [1,1,1])
    self.desat_img = Image("hud.png", color, 0, x, y, size, [0,0,0])

    self.character = character
    self.color = color
    self.is_saturated = False

  def update(self, entities):
    self.is_saturated = self.character.colors_on[self.color]

  def render(self, screen):
    if self.is_saturated:
      self.img.render(screen)
    else:
      self.desat_img.render(screen)

class Fireball(Entity):
  def __init__(self, creator, direction):
    Entity.__init__(self, creator.x, creator.y, TILE_SIZE / 4)

    self.img = Image("sprites.png", 0, 1, self.x, self.y, TILE_SIZE, [UNCOLORED, UNCOLORED, UNCOLORED])
    self.speed = 5

    self.dx, self.dy = [delta * self.speed for delta in direction]
    print self.dx, self.dy

  def update(self, entities):
    self.x += self.dx
    self.y += self.dy

    self.img.set_position((self.x, self.y))

    if len(entities.get_all(lambda e: hasattr(e, "wall") and e.wall and e.touches_entity(self))) > 0:
      print "bye"
      entities.delete(self)
  
  def depth(self):
    return 10

  def render(self, screen):
    self.img.render(screen)

class HeadsUpDisplay(Entity):
  def __init__(self, character):
    Entity.__init__(self, 0, 0, MAP_IN_PX)
    self.width = self.height = MAP_IN_PX

    self.components = []
    self.components.append(HPBar(character))

    for x in range(COLORS):
      self.components.append(HUDIcon((x + 1) * TILE_SIZE, 2 * TILE_SIZE, TILE_SIZE, x, character))

    self.action_text = ActionText(character, self.width - 200, TILE_SIZE)
    self.components.append(self.action_text)

  def update(self, entities):
    for component in self.components:
      component.update(entities)


  def render(self, screen):
    for component in self.components:
      component.render(screen)

  def depth(self):
    return 100


#@fallable()
@healthable(5)
class Character(Entity):
  def __init__(self, x, y, size):
    Entity.__init__(self, x, y, size - 2)

    self.direction = LEFT #arbitrarily choose a starting direction
    self.on_ground = False
    self.side_accel = .5
    self.side_max   = 5
    self.decel = [ 0.6, 1 ]
    self.jump_height = 25
    self.move_speed = 8
    self.swim_speed = 3

    #colors turned on
    self.colors_on = [False, False, True]

    self.sprite = Image("tiles.png", 0, 0, self.x, self.y, TILE_SIZE, [UNCOLORED, UNCOLORED, UNCOLORED])

  def touching_wall(self, entities):
    return len(entities.get_all(lambda e: hasattr(e, "wall") and self.touches_entity(e))) > 0

  def touching_ground(self, entities):
    feet = [ Point(self.x +             2, self.y + self.size)
           , Point(self.x + self.size - 2, self.y + self.size)
           ]

    for foot in feet:
      if len(entities.get_all(lambda e: hasattr(e, "wall") and e.touches_point(foot))) > 0:
        return True

    return False

  def in_water(self, entities):
    return len(entities.get_all(lambda e: hasattr(e, "water") and e.water and self.touches_entity(e))) > 0

  def resolve_collision(self, entities, vx, vy):
    assert not (vx != 0 and vy != 0) #Doing both at once is bad!

    had_collision = False

    # Design note: we could abstract this into v[0] and v[1] and not dupe this
    # code; however I feel that v[0] is harder to understand and the actual
    # amount of duped code is small.

    while self.touching_wall(entities) and abs(vy) > 0:
      had_collision = True
      self.y -= sign(vy)
      vy -= sign(vy)

    while self.touching_wall(entities) and abs(vx) > 0:
      had_collision = True
      self.x -= sign(vx)
      vx -= sign(vx)

    return had_collision
  
  def update_facing_position(self, keys):
    if keys[pygame.K_RIGHT]:
      self.direction = RIGHT
    elif keys[pygame.K_LEFT]:
      self.direction = LEFT
    elif keys[pygame.K_UP]:
      self.direction = UP
    elif keys[pygame.K_DOWN]:
      self.direction = DOWN

  def do_action(self, entities):
    if self.colors_on[RED]:
      entities.add(Fireball(self, self.direction))

  def update(self, entities):
    keys = pygame.key.get_pressed()
    self.update_facing_position(keys)
    if keys[pygame.K_x]:
      self.do_action(entities)

    map = entities.get_one(lambda e: isinstance(e, Map))

    vx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.side_accel
    if vx == 0 or sign(vx) + sign(self.v[0]) == 0:
      self.v[0] *= self.decel[0]

    if vx != 0:
      self.v[0] += vx
      self.v[0] = bound(self.v[0], self.move_speed)

    self.v[1] -= keys[pygame.K_z] * self.jump_height if self.on_ground else 0

    if self.in_water(entities) and self.colors_on[BLUE]:
      self.v[1] += self.swim_speed * (keys[pygame.K_DOWN] - keys[pygame.K_UP])
      self.v[1] *= .6 #decel
    else:
      self.v[1] += GRAVITY

    self.x += self.v[0]

    map_dx = int(math.floor(self.x / map.size))

    if map_dx != 0:
      map.new_map(entities, map_dx, 0, rel=True)
      self.x -= map_dx * map.size

    if self.resolve_collision(entities, self.v[0], 0):
      self.v[0] = 0

    self.y += self.v[1]

    map_dy = int(math.floor(self.y / map.size))
    if map_dy != 0:
      map.new_map(entities, 0, map_dy, rel=True)
      self.x -= map_dx * map.size

    self.on_ground = self.touching_ground(entities)

    if self.resolve_collision(entities, 0, self.v[1]):
      self.v[1] = 0

    self.sprite.set_position((self.x,self.y))

    self.check_mutations(keys)

  def check_mutations(self, keys):
    key_map = {pygame.K_a : RED, pygame.K_s : GREEN, pygame.K_d : BLUE}

    for key in key_map:
      value = key_map[key]

      if KeysReleased.was_up(key):
        self.colors_on[value] = not self.colors_on[value]

  def render(self, screen):
    self.sprite.render(screen)

  def depth(self):
    return 0

class Tile(Entity):
  def type_to_image(self, type):
    if type == (0, 0, 0):
      self.wall = True
      return Image("tiles.png", 1, 0, 30, 30, TILE_SIZE)
    elif type == (255, 255, 255):
      return Image("tiles.png", 0, 1, 30, 30, TILE_SIZE)
    elif type == (0, 0, 255):
      self.water = True
      return Image("tiles.png", 1, 1, 30, 30, TILE_SIZE)
    else:
      raise NoSuchTileException

  def __init__(self, position, type, size):
    Entity.__init__(self, position[0], position[1], size)

    self.sprite = self.type_to_image(type)
    self.sprite.set_position(position)

  def get_position(self): 
    return self.sprite.get_position()

  def update(self, entities):
    pass

  def render(self, screen):
    self.sprite.render(screen)

class Map(Entity):
  def __init__(self, img_sz, map_sz, file_name):
    self.mapx = None
    self.mapy = None

    self.img_sz = img_sz
    self.map_sz = map_sz
    self.file_name = file_name

    Entity.__init__(self, 0, 0, img_sz * map_sz)

  def update(self, entities):
    pass

  def render(self, screen):
    pass

  def new_map(self, entity_manager, x, y, **kwargs):
    assert isinstance(x, int)
    assert isinstance(y, int)

    if kwargs["rel"] == True:
      assert (x != 0 or y != 0)
      assert not (x != 0 and y != 0)
      # assert (x != 0 xor y != 0) lol

      self.mapx += x
      self.mapy += y
    else:
      self.mapx = x
      self.mapy = y

    self.map_data = get_tilesheet_image(MAP_DIR + self.file_name, self.mapx, self.mapy, self.map_sz, [1,1,1])

    entity_manager.delete_all(lambda e: isinstance(e, Tile))

    self.map = self.make_map()

    for tile_row in self.map:
      for tile in tile_row:
        entity_manager.add(tile)

  def make_map(self):
    map_data = [[None for x in range(self.map_sz)] for y in range(self.map_sz)]

    for x in range(self.map_sz):
      for y in range(self.map_sz):
        rgb_val = self.map_data.get_at((x, y))

        map_data[x][y] = Tile((x * self.img_sz, y * self.img_sz), rgb_val, self.img_sz)

    return map_data

class HPBar(Entity):
  BORDER_WIDTH   = 2
  BORDER_HEIGHT  = 2
  BORDER_COLOR   = pygame.Color(0, 0, 0, 0)
  HURT_COLOR     = pygame.Color(128, 0, 0)
  SHAKE_OFFSET   = 2
  SHAKE_DELAY    = 2
  SHAKE_INTERVAL = 2

  def __init__(self, entity, x=20, y=20, width=100, height=10):
    if not entity.has('healthable'):
        raise NotHealthableException
    self.max_health = self.health = entity.health
    self.width = width
    self.height = height
    self.time = 0
    self.x = x
    self.y = y
    self.offset = (0, 0)
    self.color = pygame.Color(0x0000)
    self.update_color()
    self.hurt_rect   = pygame.Rect(self.x, self.y, self.width, self.height)
    self.health_rect = pygame.Rect(self.x, self.y, self.width, self.height)
    self.border_rect = pygame.Rect(self.x - self.BORDER_WIDTH, self.y - self.BORDER_HEIGHT,
                                   self.width + self.BORDER_WIDTH * 2, self.height + self.BORDER_HEIGHT * 2)

  def update_color(self):
    self.color.hsla = (120 * self.health / self.max_health, 100, 50, 100)

  def damage(self, num):
    self.health = max(self.health - num, 0)
    self.health_rect.width = self.health * self.width / self.max_health
    self.time = time.time() + self.SHAKE_DELAY

  def update(self, entities):
    if self.health_rect.width < self.hurt_rect.width:
      t = time.time()
      if self.time > t:
        o = self.SHAKE_OFFSET
        self.offset = (random.randint(-o, o), random.randint(-o, o))
        self.hurt_rect.width  = max(self.time - t, 0) / self.SHAKE_INTERVAL
        self.hurt_rect.width *= self.hurt_rect.width - self.health_rect.width
        self.hurt_rect.width += self.health_rect.width
        self.update_color()
      else:
        self.hurt_rect.width = self.health_rect.width
        self.offset = (0, 0)

  def render(self, screen):
    pygame.draw.rect(screen, self.BORDER_COLOR, self.border_rect.move(self.offset))
    pygame.draw.rect(screen, self.HURT_COLOR, self.hurt_rect.move(self.offset))
    pygame.draw.rect(screen, self.color, self.health_rect.move(self.offset))

  def depth(self):
    return 100

class Graphics:
  """This 'class' isn't really a class at all but more of a namespace for
  Graphics related functions."""

  @staticmethod
  def post_process(screen):
    rgbarray = pygame.surfarray.array3d(screen)
    redimg = N.array(rgbarray)
    redimg[:,1:,:] = 0

    return pygame.surfarray.make_surface(rgbarray)

  @staticmethod
  def colorize(surf, rgb):
    """Given a surf SURF and rgb array RGB=[R,G,B] representing whether (for
    instance) the R channel should be shown or not, returns a new surface with
    only the desired color channels visible. R,G,B should only be 0 or 1."""

    #GOD this method is slow.
    if DEBUG:
      return surf

    dr, dg, db = rgb # desaturation values.

    surf.lock()

    rgbimg = pygame.surfarray.array3d(surf)
    rgbarray = N.array(rgbimg)

    #TODO: Cite source.

    for x, s in enumerate(rgbarray):
      for y, t in enumerate(s):
        r, g, b = t
        lum = int(0.3 * r + 0.59 * g + 0.11 * b)

        resultant = []
        for desat_val, actual_val in zip(rgb, t):
          if desat_val == UNCOLORED:
            resultant.append(lum)
          else:
            resultant.append(actual_val)

        rgbarray[x][y] = resultant

    surf.unlock()
    return pygame.surfarray.make_surface(rgbarray).convert()

class FontManager:
  """Let's not load any particular Font more than once. Yay for memory saving!
  Again, this isn't a class so much as namespaced functions."""

  fonts = {}

  @staticmethod
  def get(font_name):
    if font_name not in FontManager.fonts:
      FontManager.fonts[font_name] = pygame.font.Font(FONT_DIR + font_name, 14)

    return FontManager.fonts[font_name]

class ActionText(Entity):
  def __init__(self, follow, x, y):
    self.text = StaticText("Press X to Die.", x, y)
    self.follow = follow

  def update(self, entities):
    if self.follow.colors_on[RED]:
      self.text.set_text("Press X to FIREBALL.")
    else:
      self.text.set_text("Press X to Die.")

  def render(self, screen):
    self.text.render(screen)

class StaticText(Entity):
  """This is text that just stays in one place forever."""

  def __init__(self, contents, x, y):
    Entity.__init__(self, x, y, 200)

    self.width = 200
    self.height = 60
    self.contents = contents
    self.font = FontManager.get("nokiafc22.ttf")
    self.fontcolor = (254, 255, 255)

  def set_text(self, new_text):
    self.contents = new_text

  def update(self, entities):
    pass

  def render(self, screen):
    fontrect = pygame.Rect((self.x, self.y, self.width, self.height))

    try:
      rendered_text = render_textrect(self.contents, self.font, fontrect, self.fontcolor, (255,255,255), justification=1)
    except TextRectException:
      print "Failed to render textbox."
    else:
      screen.blit(rendered_text, fontrect.topleft)

class TextChain(Entity):
  """In-game dialog. The current concept is that all dialog will 'follow'
  something, be it a character, NPC, enemy, etc (so long as it is an Entity).
  Following an Entity just means that the dialog will appear on top of their
  head, follow them as they move, etc. I'm not a huge fan of dialog that stops
  the game from progressing. You should still be able to move around while
  dialog is being shown. """

  def __init__(self, contents, follow, fontcolor=(255, 254, 255)):
    Entity.__init__(self, follow.x, follow.y, 200)

    self.width = 200
    self.height = 60
    self.end_contents = contents.pop(0)
    self.rest_contents = contents
    self.cur_contents = ""
    self.font = FontManager.get("nokiafc22.ttf")
    self.fontcolor = fontcolor
    self.follow = follow
    self.dist = 0
    self.ticks = 0

    self.speed = 2

  def update(self, entities):
    # letter by letter, skip to end if player hits x

    if self.dist < len(self.end_contents):
      self.ticks += 1
      if self.ticks % self.speed == 0:
        self.dist += 1 

      if KeysReleased.was_up(pygame.K_x):
        self.dist = len(self.end_contents)

      self.cur_contents = self.end_contents[:self.dist]
    else:
      if KeysReleased.was_up(pygame.K_x):
        entities.delete(self)
        if len(self.rest_contents) > 0:
          entities.add(TextChain(self.rest_contents, self.follow, self.fontcolor))

  def depth(self):
    return 0

  def render(self, screen):
    fontrect = pygame.Rect((self.follow.x - self.width / 2, self.follow.y - self.follow.size - self.height, self.width, self.height))

    try:
      rendered_text = render_textrect(self.cur_contents + " (press x)", self.font, fontrect, self.fontcolor, (255,255,255), justification=1)
    except TextRectException:
      print "Failed to render textbox."
    else:
      screen.blit(rendered_text, fontrect.topleft)

class KeysReleased:
  """KeysReleased.was_up(pygame.K_somekey) will be true if and only if the
  player has released the specified key in the last game tick. This is
  important for doing actions that the player doesn't want to do several times
  in a row for one reason or another. A good example of this is dialog. You
  dont want the playter to accidentally hold down the x key for 5 ticks and
  miss a ton of important stuff. The fact that dialog shouldn't be important is
  besides the point."""

  keys = {}

  @staticmethod
  def key_up(key):
    KeysReleased.keys[key] = True

  @staticmethod
  def was_up(key):
    if key in KeysReleased.keys:
      prev_val = KeysReleased.keys[key]
      KeysReleased.keys[key] = False
      return prev_val
    else:
      return False

  @staticmethod
  def flush():
    keys = {}

class Game:
  def __init__(self):
    pygame.font.init()

    self.screen = pygame.display.set_mode(SIZE)

    self.entities = EntityManager()

    character = Character(21, 20, TILE_SIZE)
    self.entities.add(character)
    self.map = Map(TILE_SIZE, MAP_SIZE, "map.png")
    self.map.new_map(self.entities, 0, 0, rel=False)

    self.entities.add(self.map)
    self.entities.add(HeadsUpDisplay(character))

    self.entities.add(TextChain(["Wazzup? This text is long like longcat.", "This one isn't", "This dialog is amazing isnt it."], self.entities.get_one(lambda e: isinstance(e, Character))))

    print "Done loading."

  def main_loop(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          exit(0)
        if event.type == pygame.KEYUP:
          KeysReleased.key_up(event.key)

      self.entities.update()
      self.screen.fill((0,0,0))
      self.entities.render(self.screen)

      pygame.display.flip()
      time.sleep(.02) #TODO: Fix with variable timestep.

      KeysReleased.flush()

def main():
  game = Game()

if __name__ == "__main__":
  game = Game()
  game.main_loop()
