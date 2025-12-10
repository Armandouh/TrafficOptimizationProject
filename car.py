import pygame
import math
import random
from config import CAR_COLORS, TILE, ROAD_MAP
from utils import world_center
from pathfinding import bfs_find_path, tile_path_to_lane_points
from traffic_light import TrafficLight

# TRAFFIC_LIGHTS is imported in simulation.py and passed to cars

class Car:
    def __init__(self, start_tile, goal_tile, color, traffic_lights):
        self.start_tile = start_tile
        self.goal_tile = goal_tile
        self.color = color
        self.traffic_lights = traffic_lights

        self.control_light = self.assign_control_light(start_tile)
        self.has_cleared_light = False

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

        self.max_speed = 110.0
        self.speed = self.max_speed * 0.5
        self.prev_dir = (0,0)
        self.accel = 220.0
        self.brake = 500.0
        self.drag = 0.98
        self.safe_distance = 36.0
        self.reached = False
        self.width = 36
        self.height = 18

        if not self.path:
            self.reached = True

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

    def update(self, dt, all_cars):
        if self.reached:
            return

        # 1) movement direction
        if self.target_index >= len(self.path):
            self.reached = True
            return

        tx, ty = self.path[self.target_index]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 0.001:
            move_dx = dx/dist
            move_dy = dy/dist
        else:
            move_dx = move_dy = 0

        dir_dx = 1 if move_dx>0.1 else (-1 if move_dx<-0.1 else 0)
        dir_dy = 1 if move_dy>0.1 else (-1 if move_dy<-0.1 else 0)

        is_turn = (dir_dx, dir_dy) != self.prev_dir and self.prev_dir != (0,0)
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
            passed_projection = vec_x*move_dx + vec_y*move_dy
            if passed_projection > 20:
                self.has_cleared_light = True

        # 3) collision avoidance
        slow_factor = 1.0
        for o in all_cars:
            if o is self or o.reached:
                continue
            od = math.hypot(o.x - self.x, o.y - self.y)
            if od < self.safe_distance:
                slow_factor = 0.4

        # 4) speed control
        if stop_for_light:
            desired = 0.0
        else:
            desired = self.max_speed

        if is_turn:
            desired = min(desired, self.max_speed*0.45)

        self.speed += (desired - self.speed)*0.12
        self.speed = max(0, min(self.speed, self.max_speed))

        # 5) steering
        if dist > 0.001:
            target_angle = math.degrees(math.atan2(dy, dx))
            diff = (target_angle - self.angle + 540)%360 - 180
            self.angle += diff * min(1, 6*dt)

        # 6) move
        rad = math.radians(self.angle)
        self.x += math.cos(rad)*self.speed*dt
        self.y += math.sin(rad)*self.speed*dt
        self.speed *= self.drag

        # 7) waypoint reached
        if dist < 8:
            self.target_index += 1
            if self.target_index >= len(self.path):
                self.reached = True

    def draw(self, surf):
        if self.reached:
            return
        car_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        car_surf.fill(self.color)
        pygame.draw.polygon(car_surf, (255,240,240),
                            [(self.width-6, self.height//2),
                             (self.width-16, 4),
                             (self.width-16, self.height-4)])
        rot = pygame.transform.rotate(car_surf, -self.angle)
        rect = rot.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(rot, rect)
