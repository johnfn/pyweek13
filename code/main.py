import pygame
import math
import time
import spritesheet
import os

# Convention: directories will always have trailing slash.
ROOT_DIR = os.path.dirname(os.path.realpath(__file__)) + "/../"
GRAPHICS_DIR = ROOT_DIR + "data/"
SPRITE_DIR = GRAPHICS_DIR + "sprites/"
MAP_DIR = GRAPHICS_DIR + "maps/"
GRAVITY = 3

TILE_SIZE = 20
SIZE = (500, 500)
MAP_SIZE = 20
 
screen = pygame.display.set_mode(SIZE)

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

def get_tilesheet_image(file_name, pos_x, pos_y, img_sz):
  if file_name not in get_tilesheet_image.loaded_sheets:
    new_sheet = spritesheet.spritesheet(file_name)
    width, height = dimensions = new_sheet.sheet.get_size()
    get_tilesheet_image.loaded_sheets[file_name] = [[new_sheet.image_at((x, y, img_sz, img_sz), colorkey=(255,255,255))
                                                      for y in range(0, height, img_sz)] for x  in range(0, width, img_sz)]

  return get_tilesheet_image.loaded_sheets[file_name][pos_x][pos_y]

get_tilesheet_image.loaded_sheets = {}

# Expect this class to get bigger. Lol.
class Image:
  """An image that exists in the current room. """
  def __init__(self, file_name, file_pos_x, file_pos_y, my_x, my_y, img_sz):
    self.img = get_tilesheet_image(SPRITE_DIR + file_name, file_pos_x, file_pos_y, img_sz)

    #Pygame makes you hangle images and their rects separately, it's kinda stupid.
    self.rect = self.img.get_rect()
    self.rect.x = my_x
    self.rect.y = my_y

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

@fallable()
class Character(Entity):
  def __init__(self, x, y, size):
    Entity.__init__(self, x, y, size - 2)

    self.on_ground = False
    self.side_accel = 1.1
    self.side_max   = 5
    self.decel = [ 0.5, 1 ]
    self.jump_height = 25
    self.move_speed = 8

    self.sprite = Image("tiles.png", 0, 0, self.x, self.y, TILE_SIZE)

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

  def update(self, entities):
    keys = pygame.key.get_pressed()

    map = entities.get_one(lambda e: isinstance(e, Map))

    vx  = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.move_speed
    vx *= self.side_accel
    self.v[0] *= self.decel[0]
    self.v[0] += bound(vx, self.side_max)

    self.v[1] -= keys[pygame.K_z] * self.jump_height if self.on_ground else 0

    self.x += self.v[0]

    map_dx = int(math.floor(self.x / map.size))

    if map_dx != 0:
      map.new_map(entities, map_dx, 0, rel=True)
      self.x -= map_dx * map.size

    if self.resolve_collision(entities, self.v[0], 0):
      self.v[0] = 0

    self.v = [int(v) for v in self.v]

    self.y += self.v[1]

    map_dy = int(math.floor(self.y / map.size))
    if map_dy != 0:
      map.new_map(entities, 0, map_dy, rel=True)
      self.x -= map_dx * map.size

    self.on_ground = self.touching_ground(entities)

    if self.resolve_collision(entities, 0, self.v[1]):
      self.v[1] = 0

    self.sprite.set_position((self.x,self.y))

  def render(self, screen):
    self.sprite.render(screen)

  def depth(self):
    return 0

class Tile(Entity):
  def type_to_image(self, type):
    if type[0] == 0:
      self.wall = True
      return Image("tiles.png", 1, 0, 30, 30, TILE_SIZE)
    elif type[0] == 255:
      return Image("tiles.png", 0, 1, 30, 30, TILE_SIZE)
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

    self.map_data = get_tilesheet_image(MAP_DIR + self.file_name, self.mapx, self.mapy, self.map_sz)

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

class Graphics:
  """This 'class' isn't really a class at all but more of a namespace for
  Graphics related functions."""

  @staticmethod
  def post_process(screen):
    rgbarray = surfarray.array3d(surfarray)
    redimg = N.array(rgbarray)
    redimg[:,:,1:] = 0

    return surfarray.make_surface(rgbarray)

class Game:
  def __init__(self):
    self.entities = EntityManager()

    self.entities.add(Character(21, 20, TILE_SIZE))
    self.map = Map(TILE_SIZE, MAP_SIZE, "map.png")
    self.map.new_map(self.entities, 0, 0, rel=False)

    self.entities.add(self.map)

  def main_loop(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          exit(0)

      self.entities.update()

      screen.fill((0,0,0))
      self.entities.render(screen)
      pygame.display.flip()
      time.sleep(.02) #TODO: Fix with variable timestep.

def main():
  game = Game()

if __name__ == "__main__":
  game = Game()
  game.main_loop()
