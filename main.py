import pygame
from config import WIDTH, HEIGHT, FPS, BG, ROAD_MAP
from grid import draw_map, draw_debug_paths
from traffic_light import TrafficLight
from simulation import Simulation
from utils import world_center
from config import ROWS, COLS

pygame.init()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Traffic Simulation")

# Collect portals
def collect_portals(grid):
    portals = {}
    for y, row in enumerate(grid):
        for x, val in enumerate(row):
            if val and val > 1:
                portals.setdefault(val, []).append((x,y))
    return portals

PORTALS = collect_portals(ROAD_MAP)

# Create traffic lights (same configuration as original script)
TRAFFIC_LIGHTS = [
    TrafficLight((1,0.5), light_id=7, start_green=True),
    TrafficLight((1,4), light_id=7, start_green=True),
    TrafficLight((0.5,3), light_id=7, start_green=False),
    TrafficLight((3,2.5), light_id=7, start_green=False),
]

# Assign controlled tiles
for tl in TRAFFIC_LIGHTS:
    if tl.tile_pos == (2,2): tl.controlled_tiles = [(2,0)]
    elif tl.tile_pos == (2,4): tl.controlled_tiles = [(2,6)]
    elif tl.tile_pos == (1,3): tl.controlled_tiles = [(0,3)]
    elif tl.tile_pos == (3,3): tl.controlled_tiles = [(4,3)]

simulation = Simulation(TRAFFIC_LIGHTS, PORTALS)

clock = pygame.time.Clock()
running = True

while running:
    dt_ms = clock.tick(FPS)
    dt = dt_ms / 1000.0

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False

    simulation.update(dt)

    WIN.fill(BG)
    draw_map(WIN)
    draw_debug_paths(WIN, simulation.cars)
    simulation.draw(WIN)

    pygame.display.flip()

pygame.quit()
