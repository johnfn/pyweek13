import pygame
import spritesheet
import os

# Convention: directories will always have trailing slash.
ROOT_DIR = os.getcwd() + "/../"
GRAPHICS_DIR = ROOT_DIR + "data/sprites/"

TILE_SIZE = 20
SIZE = (500, 500)
MAP_SIZE = 20
 
screen = pygame.display.set_mode(SIZE)

#TODO: Move to map class once we actually start developing that functionality.
def make_map():
  map = [[0 for x in range(MAP_SIZE)] for y in range(MAP_SIZE)]

  for x in range(20):
    map[18][x] = 1



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
    self.img = get_tilesheet_image(file_name, file_pos_x, file_pos_y, img_sz)

    #Pygame makes you hangle images and their rects separately, it's kinda stupid.
    self.rect = self.img.get_rect()
    self.rect.x = my_x
    self.rect.y = my_y

  def get_position(self):
    return (self.rect.x, self.rect.y)

  def set_position(self, x, y):
    self.rect.x = x
    self.rect.y = y

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
      entity.update()

  #TODO: (maybe) Sort by depth.
  def render(self, screen):
    for entity in self.entities:
      entity.render(screen)

class Entity:
  def update(self):
    raise NotImplementedException

  def render(self, screen):
    raise NotImplementedException

class Character(Entity):
  def __init__(self):
    self.sprite = Image(GRAPHICS_DIR + "tiles.png", 0, 0, 30, 30, TILE_SIZE)

  def update(self):
    #look for keys...blabla
    pass

  def render(self, screen):
    self.sprite.render(screen)

class Game:
  def __init__(self):
    self.map = make_map()
    self.entities = EntityManager()

    self.entities.add(Character())

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
