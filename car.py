import pygame
import math
import random
from config import TILE, ROAD_MAP
from utils import world_center
from pathfinding import bfs_find_path, tile_path_to_lane_points


# ============================================================
# Line intersection helper (needed by raycast)
# ============================================================
def lines_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    A = (x1, y1)
    B = (x2, y2)
    C = (x3, y3)
    D = (x4, y4)
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


# ============================================================
# Raycast helper
# ============================================================
def raycast_to_rect(x1, y1, x2, y2, rect):
    lines = [
        ((rect.left, rect.top), (rect.right, rect.top)),
        ((rect.right, rect.top), (rect.right, rect.bottom)),
        ((rect.right, rect.bottom), (rect.left, rect.bottom)),
        ((rect.left, rect.bottom), (rect.left, rect.top)),
    ]

    for (ax, ay), (bx, by) in lines:
        if lines_intersect(x1, y1, x2, y2, ax, ay, bx, by):
            return True
    return False


class Car:
    def __init__(self, start_tile, goal_tile, color, traffic_lights):
        self.start_tile = start_tile
        self.goal_tile = goal_tile
        self.color = color
        self.traffic_lights = traffic_lights

        # --- jam stability state ---
        self.blocked_by_car = False

        # defaults (will be overridden/randomized)
        self.block_gap = 55
        self.release_gap = 70

        self.width = 36
        self.height = 18

        self.max_speed = 110.0
        self.speed = self.max_speed * 0.5

        self.prev_dir = (0, 0)
        self.accel = 220.0
        self.brake = 500.0
        self.drag = 0.98
        self.safe_distance = 36.0
        self.reached = False

        # Randomize size + speed personality
        self._randomize_appearance_and_physics()

        # traffic light association (optional logic you already had)
        self.control_light = self.assign_control_light(start_tile)
        self.has_cleared_light = False

        # Path
        tile_path = bfs_find_path(start_tile, goal_tile, ROAD_MAP)
        self.tile_path = tile_path
        self.path = tile_path_to_lane_points(tile_path)

        if len(tile_path) > 1:
            self.x, self.y, self.angle = self.compute_spawn(tile_path[0], tile_path[1])
            self.target_index = 0
        else:
            cx, cy = world_center(*start_tile)
            self.x, self.y = cx, cy
            self.angle = 0
            self.target_index = 0

        if not self.path:
            self.reached = True

    # ------------------------------------------------------------
    # Random car models (size/speed) to make traffic feel real
    # ------------------------------------------------------------
    def _randomize_appearance_and_physics(self):
        car_types = [
            {"name": "compact", "w": (30, 38), "h": (15, 18), "speed": (105, 125)},
            {"name": "sedan",   "w": (38, 48), "h": (16, 20), "speed": (100, 118)},
            {"name": "suv",     "w": (45, 58), "h": (18, 24), "speed": (95, 112)},
            {"name": "van",     "w": (55, 72), "h": (20, 28), "speed": (85, 102)},
        ]
        t = random.choice(car_types)
        self.car_type = t["name"]

        self.width = random.randint(*t["w"])
        self.height = random.randint(*t["h"])

        self.max_speed = random.uniform(*t["speed"])
        self.speed = self.max_speed * random.uniform(0.35, 0.6)

        # scale jam spacing with car length (prevents pixel pushing)
        self.block_gap = max(getattr(self, "block_gap", 55), self.width * 1.4)
        self.release_gap = max(getattr(self, "release_gap", 70), self.width * 1.9)

    # ------------------------------------------------------------
    # Traffic light helpers
    # ------------------------------------------------------------
    def assign_control_light(self, start_tile):
        sx, sy = start_tile
        for tl in self.traffic_lights:
            if (sx, sy) in tl.controlled_tiles:
                return tl
        return None

    def compute_spawn(self, start_tile, next_tile):
        sx, sy = start_tile
        nx, ny = next_tile
        dir_x = nx - sx
        dir_y = ny - sy
        cx, cy = world_center(sx, sy)

        OFFSET = TILE * 0.25
        SPAWN_DISTANCE = TILE * 0.6

        if dir_x == 1:
            return cx - SPAWN_DISTANCE, cy + OFFSET, 0
        if dir_x == -1:
            return cx + SPAWN_DISTANCE, cy - OFFSET, 180
        if dir_y == 1:
            return cx - OFFSET, cy - SPAWN_DISTANCE, 90
        if dir_y == -1:
            return cx + OFFSET, cy + SPAWN_DISTANCE, 270
        return cx, cy, 0

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------
    def update(self, dt, all_cars):
        if self.reached:
            return

        # 1) target
        if self.target_index >= len(self.path):
            self.reached = True
            return

        tx, ty = self.path[self.target_index]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 0.001:
            move_dx = dx / dist
            move_dy = dy / dist
        else:
            move_dx = move_dy = 0

        dir_dx = 1 if move_dx > 0.1 else (-1 if move_dx < -0.1 else 0)
        dir_dy = 1 if move_dy > 0.1 else (-1 if move_dy < -0.1 else 0)

        is_turn = (dir_dx, dir_dy) != self.prev_dir and self.prev_dir != (0, 0)
        if self.speed > 10:
            self.prev_dir = (dir_dx, dir_dy)

        # 2) traffic lights
        stop_for_light = False
        STOP_DISTANCE = 55

        for tl in self.traffic_lights:
            lx, ly = tl.stop_point
            vec_x = lx - self.x
            vec_y = ly - self.y
            dist_to_light = math.hypot(vec_x, vec_y)

            if dist_to_light < STOP_DISTANCE:
                projection = vec_x * move_dx + vec_y * move_dy
                if projection > 0:
                    if not tl.car_can_pass(self, dir_dx, dir_dy):
                        stop_for_light = True
                        break

        # 2.5) clear own light
        if self.control_light and not self.has_cleared_light:
            lx, ly = self.control_light.stop_point
            vec_x = self.x - lx
            vec_y = self.y - ly
            passed_projection = vec_x * move_dx + vec_y * move_dy
            if passed_projection > 20:
                self.has_cleared_light = True

        # 3) collision avoidance (raycasts) + spacing hysteresis
        slow_factor = 1.0
        nearest_ahead = None

        RAY_ANGLE_SPREAD = 15
        RAY_LENGTH = max(80, int(self.width * 2.2))  # scale with car length

        desired_heading = math.degrees(math.atan2(move_dy, move_dx)) if (move_dx or move_dy) else self.angle
        angles = [desired_heading,
                  desired_heading - RAY_ANGLE_SPREAD,
                  desired_heading + RAY_ANGLE_SPREAD]

        for ang in angles:
            ray_end_x = self.x + math.cos(math.radians(ang)) * RAY_LENGTH
            ray_end_y = self.y + math.sin(math.radians(ang)) * RAY_LENGTH

            for o in all_cars:
                if o is self or o.reached:
                    continue

                rect = pygame.Rect(
                    o.x - o.width // 2,
                    o.y - o.height // 2,
                    o.width,
                    o.height
                )

                if raycast_to_rect(self.x, self.y, ray_end_x, ray_end_y, rect):
                    d = math.hypot(o.x - self.x, o.y - self.y)

                    if nearest_ahead is None or d < nearest_ahead:
                        nearest_ahead = d

                    if d < 90:
                        slow_factor = min(slow_factor, 0.6)
                    if d < 60:
                        slow_factor = min(slow_factor, 0.25)
                    if d < 40:
                        slow_factor = min(slow_factor, 0.01)

        # spacing hysteresis: stop creeping/pushing in jams
        if nearest_ahead is not None:
            if nearest_ahead < self.block_gap:
                self.blocked_by_car = True

            if self.blocked_by_car:
                if nearest_ahead > self.release_gap:
                    self.blocked_by_car = False
                else:
                    slow_factor = 0.0
        else:
            self.blocked_by_car = False

        # 4) speed control
        if stop_for_light or self.blocked_by_car:
            desired = 0.0
        else:
            desired = self.max_speed * slow_factor

        if is_turn:
            desired = min(desired, self.max_speed * 0.45)

        self.speed += (desired - self.speed) * 0.12
        self.speed = max(0, min(self.speed, self.max_speed))

        blocked = stop_for_light or self.blocked_by_car or (slow_factor <= 0.3 and self.speed < 15)

        # 5) steering (do NOT rotate in place when blocked)
        if dist > 0.001 and not blocked:
            target_angle = math.degrees(math.atan2(dy, dx))
            diff = (target_angle - self.angle + 540) % 360 - 180
            self.angle += diff * min(1, 6 * dt)

        # 6) move
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed * dt
        self.y += math.sin(rad) * self.speed * dt
        self.speed *= self.drag

        # 7) waypoint reached
        if dist < 8:
            self.target_index += 1
            if self.target_index >= len(self.path):
                self.reached = True

    # ------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------
    def draw(self, surf):
        if self.reached:
            return

        car_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        car_surf.fill(self.color)

        # scaled "nose" arrow so longer cars look right
        nose = max(6, int(self.width * 0.18))
        nose_back = max(12, int(self.width * 0.45))
        pad = max(3, int(self.height * 0.20))
        pygame.draw.polygon(
            car_surf, (255, 240, 240),
            [
                (self.width - nose, self.height // 2),
                (self.width - nose_back, pad),
                (self.width - nose_back, self.height - pad),
            ]
        )

        rot = pygame.transform.rotate(car_surf, -self.angle)
        rect = rot.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(rot, rect)

        # OPTIONAL DEBUG: draw rays (comment out if you want clean visuals)
        # desired_heading = self.angle
        # for ang in [desired_heading, desired_heading - 15, desired_heading + 15]:
        #     rx = self.x + math.cos(math.radians(ang)) * max(80, int(self.width * 2.2))
        #     ry = self.y + math.sin(math.radians(ang)) * max(80, int(self.width * 2.2))
        #     pygame.draw.line(surf, (255, 255, 255), (self.x, self.y), (rx, ry), 1)
