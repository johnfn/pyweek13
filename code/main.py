import pygame
import spritesheet
import os

# Convention: directories will always have trailing slash.
ROOT_DIR = os.path.dirname(__file__) + "/../"
GRAPHICS_DIR = ROOT_DIR + "data/"
SPRITES_DIR = GRAPHICS_DIR + "sprites/"

TILE_SIZE = 20
SIZE = (500, 500)
MAP_SIZE = 20
 
screen = pygame.display.set_mode(SIZE)

class Point:
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def __str__(self):
    return "<Point x:%d y:%d>" % (self.x, self.y)

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
    self.img = get_tilesheet_image(SPRITES_DIR + file_name, file_pos_x, file_pos_y, img_sz)

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

  def get_all(self, func):
    return [entity for entity in self.entities if func(entity)]

  def delete_all(self, func):
    """Delete all enetities E such that func(E) == True """

    entities_remaining = []
    for entity in entities:
      if not func(entity):
        entities_remaining.append(entity)

    self.entities = entities_remaining

class Entity:
  def touches_point(self, point):
    return self.x <= point.x <= self.x + self.size and\
           self.y <= point.y <= self.y + self.size

  def touches_entity(self, other):
    assert self.x is not None
    assert other.x is not None

    points = [ (self.x, self.y)
             , (self.x + self.size, self.y)
             , (self.x,             self.y + self.size)
             , (self.x + self.size, self.y + self.size)
             ]

    points = [Point(*p) for p in points]

    for point in points:
      if other.touches_point(point):
        print point
        return True

    return False

  def __init__(self, x, y, size):
    self.x = x
    self.y = y
    self.size = size

  def update(self, entities):
    raise NotImplementedException

  def render(self, screen):
    raise NotImplementedException

class Character(Entity):
  def __init__(self, x, y, size):
    Entity.__init__(self, x, y, size)

    self.x = x
    self.y = y

    self.sprite = Image("tiles.png", 0, 0, self.x, self.y, TILE_SIZE)

  def update(self, entities):
    keys = pygame.key.get_pressed()

    vx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]

    self.x += vx

    if len(entities.get_all(lambda e: hasattr(e, "wall") and e.touches_entity(self))) > 0:
      print "Touching wall"

    self.sprite.set_position((self.x,self.y))

  def render(self, screen):
    self.sprite.render(screen)

  def depth(self):
    return 0

class Tile(Entity):
  def type_to_image(self, type):
    if type == 0:
      return Image("tiles.png", 0, 1, 30, 30, TILE_SIZE)
    elif type == 1:
      self.wall = True
      return Image("tiles.png", 1, 0, 30, 30, TILE_SIZE)
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

class Map:
  def __init__(self, img_sz):
    self.img_sz = img_sz

  def new_map(self, entity_manager):
    #TODO: Destroy all old Tiles.
    self.map = self.make_map()

    for tile_row in self.map:
      for tile in tile_row:
        entity_manager.add(tile)

  #TODO: This method is totally bogus
  def make_map(self):
    map_data = [[Tile((x * self.img_sz, y * self.img_sz), 0, self.img_sz) for x in range(MAP_SIZE)] for y in range(MAP_SIZE)]

    for x in range(MAP_SIZE):
      map_data[18][x] = Tile(map_data[18][x].get_position(), 1, self.img_sz)

    return map_data

class Game:
  def __init__(self):
    self.entities = EntityManager()

    self.entities.add(Character(30, 330, 20))
    self.map = Map(TILE_SIZE)
    self.map.new_map(self.entities)

  def main_loop(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          exit(0)

      self.entities.update()

      screen.fill((0,0,0))
      self.entities.render(screen)
      pygame.display.flip()

def main():
  game = Game()

if __name__ == "__main__":
  game = Game()
  game.main_loop()
