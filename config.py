import pygame

# ============================================
# Settings
# ============================================
WIDTH, HEIGHT = 1000, 800
TILE = 110
FPS = 60
# road encodings (negative = road, >1 = portal)
ROAD_TWOWAY_1LANE = 1        # keep your current road as 1 (works)
ROAD_TWOWAY_2LANE = 10      # 2 lanes per direction

ONEWAY_E = 1
ONEWAY_W = -2
ONEWAY_S = -3
ONEWAY_N = -4

# Car/Spawner
MAX_ACTIVE_CARS = 100
SPAWN_INTERVAL_MS = 1500
MAX_SPAWN_TRIES = 12

# Colors
BG = (40, 40, 40)
ROAD_GRAY = (60, 60, 60)
LANE_LINE = (200, 200, 200)
PORTAL_COL = (200, 140, 20)
CAR_COLORS = [(220,30,30), (30,220,30), (30,30,220), (220,220,30), (220,30,220)]
BLACK = (0,0,0)
WHITE = (240,240,240)

# ============================================
# Road map
# ============================================
ROAD_MAP = [
    [5,   1,  1,  1,  1,  1,  1,  1,  2,   0],
    [0,   1,  0,  1,  0,  1,  0,   0,   0,   0],
    [0,   1,  0,  1,  0,  1,  0,   0,   0,   0],
    [4,   1, 1, 1,  0,  1,  0,   0,   0,   0],
    [0,    0,  1,  0,   0,  1,  0,   0,   0,   0],
    [0,    0,  1, 1, 1, 1,  0,   0,   0,   0],
    [0,    0,   0,   0,   0,  1,  0,   0,   0,   0],
    [0,    0,   0,   0,   0,   3,   0,   0,   0,   0],
]


ROWS = len(ROAD_MAP)
COLS = len(ROAD_MAP[0])

LANE_OFFSET = TILE // 4
