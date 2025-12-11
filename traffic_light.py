import pygame
from utils import world_center
from config import WHITE

class TrafficLight:
    def __init__(self, tile_pos, light_id, green_duration=4000, red_duration=4000, start_green=True):
        self.tile_pos = tile_pos
        self.light_id = light_id

        # Timer logic now unused, but kept for compatibility
        self.green_duration = green_duration
        self.red_duration = red_duration
        self.timer = 0

        self.green = start_green
        self.time_since_switch = 0
        self.prev_green = self.green
        self.controlled_tiles = [self.tile_pos]

        cx, cy = world_center(*tile_pos)
        self.stop_point = (cx, cy)

        self.name = f"({tile_pos[0]},{tile_pos[1]})"

    # NEW — Disable old timer switching
    def update(self, dt):
        pass  # RL fully controls switching

    # RL action handler
    def update_with_rl(self, action):
        self.prev_green = self.green

        if action == "switch":
            self.green = not self.green
            self.time_since_switch = 0
        else:
            self.time_since_switch += 1  # RL step counter

    def car_can_pass(self, car, car_dx, car_dy):
        if car.control_light is not self:
            return True
        if car.has_cleared_light:
            return True
        if car_dx == 0 and car_dy == 0:
            return False
        if self.green:
            return True

        lx, ly = self.stop_point
        dx = lx - car.x
        dy = ly - car.y
        approaching = (dx * car_dx + dy * car_dy) > 0
        return not approaching

    def draw(self, surf):
        cx, cy = self.stop_point
        color = (0,200,0) if self.green else (200,0,0)
        pygame.draw.circle(surf, color, (cx, cy), 10)
        font = pygame.font.SysFont(None, 20)
        txt = font.render(str(self.light_id), True, WHITE)
        surf.blit(txt, (cx-6, cy-6))
