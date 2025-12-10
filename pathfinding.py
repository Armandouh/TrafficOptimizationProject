from collections import deque
import math
from config import TILE, ROAD_MAP
from utils import world_center

# BFS tile path
def bfs_find_path(start, goal, grid):
    sx, sy = start
    gx, gy = goal
    ROWS = len(grid)
    COLS = len(grid[0])

    q = deque([(sx, sy)])
    parent = {(sx, sy): None}
    visited = {(sx, sy)}
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]

    while q:
        cx, cy = q.popleft()
        if (cx, cy) == (gx, gy):
            break
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS:
                if (nx, ny) not in visited and grid[ny][nx] != 0:
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))

    if (gx, gy) not in parent:
        return []

    path = []
    cur = (gx, gy)
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


# Convert tile path to lane-aware world points
def tile_path_to_lane_points(tile_path):
    if not tile_path:
        return []

    OFFSET = TILE * 0.25
    CURVE_RADIUS = TILE * 0.30
    CURVE_STEPS = 8
    points = []

    for i in range(len(tile_path)):
        x, y = tile_path[i]
        cx, cy = world_center(x, y)

        # determine direction
        if i < len(tile_path)-1:
            nx, ny = tile_path[i+1]
            dx = nx - x
            dy = ny - y
        else:
            px, py = tile_path[i-1]
            dx = x - px
            dy = y - py

        # apply lane offset
        if dx == 1: cy += OFFSET
        elif dx == -1: cy -= OFFSET
        elif dy == 1: cx -= OFFSET
        elif dy == -1: cx += OFFSET

        # detect turn
        if 0 < i < len(tile_path)-1:
            px, py = tile_path[i-1]
            nx, ny = tile_path[i+1]

            dx1, dy1 = x - px, y - py
            dx2, dy2 = nx - x, ny - y

            turning = (dx1, dy1) != (dx2, dy2)
            if turning:
                ex = cx - dx1 * CURVE_RADIUS
                ey = cy - dy1 * CURVE_RADIUS
                lx = cx + dx2 * CURVE_RADIUS
                ly = cy + dy2 * CURVE_RADIUS

                turn = dx1 * dy2 - dy1 * dx2
                perp_x = -dy1
                perp_y = dx1

                if turn > 0:
                    ex += perp_x * OFFSET
                    ey += perp_y * OFFSET
                    lx += perp_x * (OFFSET*0.5)
                    ly += perp_y * (OFFSET*0.5)
                else:
                    ex -= perp_x * OFFSET
                    ey -= perp_y * OFFSET
                    lx -= perp_x * (OFFSET*0.5)
                    ly -= perp_y * (OFFSET*0.5)

                ctrl1 = (ex, ey)
                ctrl2 = (lx, ly)

                for t_i in range(CURVE_STEPS+1):
                    t = t_i / CURVE_STEPS
                    bx = (1-t)**3 * ex + 3*(1-t)**2*t * ctrl1[0] + 3*(1-t)*t**2 * ctrl2[0] + t**3 * lx
                    by = (1-t)**3 * ey + 3*(1-t)**2*t * ctrl1[1] + 3*(1-t)*t**2 * ctrl2[1] + t**3 * ly
                    points.append((bx, by))
                continue

        points.append((cx, cy))

    return points
