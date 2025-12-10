import pygame
from config import ROAD_GRAY, LANE_LINE, PORTAL_COL, BLACK, WHITE, TILE, ROWS, COLS, ROAD_MAP
from utils import tile_rect, world_center

def draw_map(surface):
    for y in range(ROWS):
        for x in range(COLS):
            val = ROAD_MAP[y][x]
            r = tile_rect(x,y)
            if val == 0:
                continue

            pygame.draw.rect(surface, ROAD_GRAY, r)

            cx, cy = world_center(x,y)
            horiz = (x+1 < COLS and ROAD_MAP[y][x+1]!=0) or (x-1>=0 and ROAD_MAP[y][x-1]!=0)
            vert  = (y+1 < ROWS and ROAD_MAP[y+1][x]!=0) or (y-1>=0 and ROAD_MAP[y-1][x]!=0)

            if horiz and not vert:
                pygame.draw.line(surface, LANE_LINE, (x*TILE, cy-6), (x*TILE+TILE, cy-6), 2)
                pygame.draw.line(surface, LANE_LINE, (x*TILE, cy+6), (x*TILE+TILE, cy+6), 2)
            elif vert and not horiz:
                pygame.draw.line(surface, LANE_LINE, (cx-6, y*TILE), (cx-6, y*TILE+TILE), 2)
                pygame.draw.line(surface, LANE_LINE, (cx+6, y*TILE), (cx+6, y*TILE+TILE), 2)
            else:
                pygame.draw.line(surface, LANE_LINE, (x*TILE+8, y*TILE+8), (x*TILE+TILE-8, y*TILE+TILE-8), 2)
                pygame.draw.line(surface, LANE_LINE, (x*TILE+8, y*TILE+TILE-8), (x*TILE+TILE-8, y*TILE+8), 2)

            if val > 1:
                pygame.draw.rect(surface, PORTAL_COL, r.inflate(-TILE//4, -TILE//4))
                font = pygame.font.SysFont(None, 20)
                txt = font.render(str(val), True, BLACK)
                surface.blit(txt, (x*TILE+6, y*TILE+6))

            pygame.draw.rect(surface, BLACK, r, 2)

def draw_debug_paths(surface, cars):
    for car in cars:
        if not car.path:
            continue
        pts = [(int(px), int(py)) for px, py in car.path]
        if len(pts) >= 2:
            pygame.draw.lines(surface, (120,120,255), False, pts, 2)
        for p in pts:
            pygame.draw.circle(surface, (255,255,255), p, 3)
