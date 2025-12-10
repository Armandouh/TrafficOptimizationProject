import pygame
from config import TILE, LANE_OFFSET

def tile_rect(tx, ty):
    return pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)

def world_center(tx, ty):
    return (tx * TILE + TILE // 2, ty * TILE + TILE // 2)

def lane_center_from_dir(cx, cy, dx, dy):
    base_x, base_y = world_center(cx, cy)
    if dx > 0:
        return base_x + LANE_OFFSET, base_y + LANE_OFFSET
    if dx < 0:
        return base_x - LANE_OFFSET, base_y - LANE_OFFSET
    if dy > 0:
        return base_x - LANE_OFFSET, base_y + LANE_OFFSET
    if dy < 0:
        return base_x + LANE_OFFSET, base_y - LANE_OFFSET
    return base_x, base_y

def rects_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return (ax < bx + bw and ax + aw > bx and
            ay < by + bh and ay + ah > by)
