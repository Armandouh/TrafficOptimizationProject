from collections import deque
import math
from config import TILE, ROAD_MAP
from utils import world_center

# ------------------------------------------------------------
# Road encoding (negative = special roads, >1 = portals)
# ------------------------------------------------------------
#  0  = empty
#  1  = normal two-way road (1 lane per direction)
# -10 = two-way road (2 lanes per direction)
# -1  = one-way EAST  (only move +x)
# -2  = one-way WEST  (only move -x)
# -3  = one-way SOUTH (only move +y)
# -4  = one-way NORTH (only move -y)

DIRS4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def is_drivable(val: int) -> bool:
    # roads (1, negatives) and portals (>1) are drivable
    return val != 0


def allows_exit(tile_val: int, dx: int, dy: int) -> bool:
    """Return True if a move (dx,dy) is allowed when leaving a tile."""
    if tile_val == -1:   # one-way east
        return (dx, dy) == (1, 0)
    if tile_val == -2:   # one-way west
        return (dx, dy) == (-1, 0)
    if tile_val == -3:   # one-way south
        return (dx, dy) == (0, 1)
    if tile_val == -4:   # one-way north
        return (dx, dy) == (0, -1)
    return True  # two-way roads / portals


# ------------------------------------------------------------
# BFS tile path with one-way constraints
# ------------------------------------------------------------
def bfs_find_path(start, goal, grid):
    sx, sy = start
    gx, gy = goal
    ROWS = len(grid)
    COLS = len(grid[0])

    if not (0 <= sx < COLS and 0 <= sy < ROWS):
        return []
    if not (0 <= gx < COLS and 0 <= gy < ROWS):
        return []

    if not is_drivable(grid[sy][sx]) or not is_drivable(grid[gy][gx]):
        return []

    q = deque([(sx, sy)])
    parent = {(sx, sy): None}
    visited = {(sx, sy)}

    while q:
        cx, cy = q.popleft()
        if (cx, cy) == (gx, gy):
            break

        cur_val = grid[cy][cx]

        for dx, dy in DIRS4:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS:
                if (nx, ny) in visited:
                    continue

                nxt_val = grid[ny][nx]
                if not is_drivable(nxt_val):
                    continue

                # one-way constraints:
                # - current tile must allow leaving in (dx,dy)
                # - next tile must allow entering from (-dx,-dy)
                if not allows_exit(cur_val, dx, dy):
                    continue
                if not allows_exit(nxt_val, -dx, -dy):
                    continue

                visited.add((nx, ny))
                parent[(nx, ny)] = (cx, cy)
                q.append((nx, ny))

    if (gx, gy) not in parent:
        return []

    # reconstruct
    path = []
    cur = (gx, gy)
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


# ------------------------------------------------------------
# Lane-aware geometry (+ multi-lane offsets + curves)
# ------------------------------------------------------------
def lanes_per_direction(tile_val: int) -> int:
    # -10 means 2 lanes each direction
    if tile_val == -10:
        return 2
    # otherwise 1 lane per direction
    return 1


def _lane_offset(tile_val: int, lane_index: int) -> float:
    """
    Returns lane offset (px) from centerline for right-side traffic.
    lane_index: 0..lanes-1
    """
    base = TILE * 0.25
    lanes = lanes_per_direction(tile_val)
    if lanes <= 1:
        return base

    lane_spacing = TILE * 0.14
    # right-side: lane 0 is closest to center, lane 1 slightly further
    return base + lane_index * lane_spacing


def tile_path_to_lane_points(tile_path, lane_index: int = 0):
    """
    Convert tile path to world points.
    - lane_index: pick 0..(lanes-1) for 2-lane roads, else ignored
    """
    if not tile_path:
        return []

    # smoother curves
    CURVE_RADIUS = TILE * 0.40
    CURVE_STEPS = 12

    points = []

    for i in range(len(tile_path)):
        x, y = tile_path[i]
        cx, cy = world_center(x, y)

        # determine forward direction at this node
        if i < len(tile_path) - 1:
            nx, ny = tile_path[i + 1]
            dx = nx - x
            dy = ny - y
        else:
            px, py = tile_path[i - 1]
            dx = x - px
            dy = y - py

        # offset depends on this tile type
        tile_val = ROAD_MAP[y][x]
        OFFSET = _lane_offset(tile_val, lane_index)

        # apply lane offset for right-side traffic
        # moving east => drive slightly lower (positive y)
        # moving west => drive slightly higher (negative y)
        # moving south => drive slightly left (negative x)
        # moving north => drive slightly right (positive x)
        if dx == 1:
            cy += OFFSET
        elif dx == -1:
            cy -= OFFSET
        elif dy == 1:
            cx -= OFFSET
        elif dy == -1:
            cx += OFFSET

        # detect turn and generate curve instead of sharp corner
        if 0 < i < len(tile_path) - 1:
            px, py = tile_path[i - 1]
            nx, ny = tile_path[i + 1]

            dx1, dy1 = x - px, y - py
            dx2, dy2 = nx - x, ny - y

            turning = (dx1, dy1) != (dx2, dy2)
            if turning:
                # entry and exit points near corner
                ex = cx - dx1 * CURVE_RADIUS
                ey = cy - dy1 * CURVE_RADIUS
                lx = cx + dx2 * CURVE_RADIUS
                ly = cy + dy2 * CURVE_RADIUS

                # slight bias so curve stays inside the lane on turns
                turn = dx1 * dy2 - dy1 * dx2
                perp_x = -dy1
                perp_y = dx1

                if turn > 0:
                    ex += perp_x * OFFSET
                    ey += perp_y * OFFSET
                    lx += perp_x * (OFFSET * 0.5)
                    ly += perp_y * (OFFSET * 0.5)
                else:
                    ex -= perp_x * OFFSET
                    ey -= perp_y * OFFSET
                    lx -= perp_x * (OFFSET * 0.5)
                    ly -= perp_y * (OFFSET * 0.5)

                # cubic Bezier control points (keep your original style)
                ctrl1 = (ex, ey)
                ctrl2 = (lx, ly)

                for t_i in range(CURVE_STEPS + 1):
                    t = t_i / CURVE_STEPS
                    bx = (
                        (1 - t) ** 3 * ex
                        + 3 * (1 - t) ** 2 * t * ctrl1[0]
                        + 3 * (1 - t) * t ** 2 * ctrl2[0]
                        + t ** 3 * lx
                    )
                    by = (
                        (1 - t) ** 3 * ey
                        + 3 * (1 - t) ** 2 * t * ctrl1[1]
                        + 3 * (1 - t) * t ** 2 * ctrl2[1]
                        + t ** 3 * ly
                    )
                    points.append((bx, by))
                continue

        points.append((cx, cy))

    return points
