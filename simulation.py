import math
import random
import pygame

from config import MAX_ACTIVE_CARS, SPAWN_INTERVAL_MS, MAX_SPAWN_TRIES, CAR_COLORS, ROAD_MAP
from pathfinding import bfs_find_path
from car import Car
from rl_agent import RLLightAgent


class Simulation:
    def __init__(self, traffic_lights, portals):
        self.cars = []
        self.traffic_lights = traffic_lights
        self.portals = portals
        self.portal_ids = list(portals.keys())
        self.last_spawn_time = pygame.time.get_ticks()

        self.rl_agent = RLLightAgent(actions=["stay", "switch"])

        self.last_sa = {}  # tl -> (state, action)
        self.episode_crashes = 0

        # Make sure panel does not crash at start
        for tl in self.traffic_lights:
            if not hasattr(tl, "total_reward"):
                tl.total_reward = 0
            tl.debug_info = ("init", 0, 0)
            tl.penalties = {"queue": 0, "opp": 0, "switch": 0, "block": 0, "clear": 0}

    # -----------------------------
    # HELPERS
    # -----------------------------
    def detect_crash(self):
        n = len(self.cars)
        for i in range(n):
            a = self.cars[i]
            if getattr(a, "reached", False):
                continue
            ra = a.get_rect()
            for j in range(i + 1, n):
                b = self.cars[j]
                if getattr(b, "reached", False):
                    continue
                if ra.colliderect(b.get_rect()):
                    return a, b
        return None, None

    def reset_episode(self):
        self.cars.clear()
        self.last_spawn_time = pygame.time.get_ticks()
        self.last_sa.clear()

        for tl in self.traffic_lights:
            # If you added tl.reset(...) use it, otherwise fallback
            if hasattr(tl, "reset"):
                tl.reset(start_green=random.choice([True, False]))
            else:
                tl.green = random.choice([True, False])
                tl.prev_green = tl.green
                tl.time_since_switch = 0

            if not hasattr(tl, "total_reward"):
                tl.total_reward = 0

            # Always initialize these so draw never crashes
            tl.debug_info = ("reset", 0, 0)
            tl.penalties = {"queue": 0, "opp": 0, "switch": 0, "block": 0, "clear": 0}

    def get_queue_near_light(self, tl, radius=80):
        queue = 0
        lx, ly = tl.stop_point
        for car in self.cars:
            if not getattr(car, "has_cleared_light", False):
                if math.hypot(car.x - lx, car.y - ly) < radius:
                    queue += 1
        return queue

    def get_cars_cleared(self, old_q, new_q):
        return max(0, old_q - new_q)

    def is_intersection_blocked(self):
        for car in self.cars:
            if 250 < car.x < 450 and 250 < car.y < 450:
                if car.speed < 10:
                    return True
        return False

    def spawn_car_random(self):
        if len(self.portal_ids) < 2:
            return None

        tries = 0
        while tries < MAX_SPAWN_TRIES:
            start_id = random.choice(self.portal_ids)
            goal_id = random.choice(self.portal_ids)
            if start_id == goal_id:
                tries += 1
                continue

            start_tile = random.choice(self.portals[start_id])
            goal_tile = random.choice(self.portals[goal_id])

            tile_path = bfs_find_path(start_tile, goal_tile, ROAD_MAP)
            if tile_path:
                color = random.choice(CAR_COLORS)
                return Car(start_tile, goal_tile, color, self.traffic_lights)

            tries += 1

        return None

    # -----------------------------
    # MAIN UPDATE LOOP
    # -----------------------------
    def update(self, dt):
        now = pygame.time.get_ticks()

        # spawn cars
        if len(self.cars) < MAX_ACTIVE_CARS and now - self.last_spawn_time >= SPAWN_INTERVAL_MS:
            car = self.spawn_car_random()
            if car:
                self.cars.append(car)
            self.last_spawn_time = now

        # -------------------------
        # RL LOOP FOR EACH LIGHT
        # Decide actions first, then move cars, then detect crash
        # -------------------------
        for tl in self.traffic_lights:
            queue = self.get_queue_near_light(tl)
            opp_queue = self.get_queue_near_light(tl, radius=130)
            time_since = min(getattr(tl, "time_since_switch", 0), 10)
            is_green = int(getattr(tl, "green", True))

            state = (min(queue, 5), min(opp_queue, 5), time_since, is_green)

            action = self.rl_agent.choose_action(state)
            self.last_sa[tl] = (state, action)

            # Apply action
            tl.update_with_rl(action)

            # Reward
            old_queue = queue
            new_queue = self.get_queue_near_light(tl)
            cleared = self.get_cars_cleared(old_queue, new_queue)
            blocked = self.is_intersection_blocked()

            reward = (
                cleared * 2
                - new_queue
                - opp_queue * 0.5
                - (2 if getattr(tl, "time_since_switch", 0) == 0 else 0)
                - (5 if blocked else 0)
            )

            if not hasattr(tl, "total_reward"):
                tl.total_reward = 0
            tl.total_reward += reward

            tl.penalties = {
                "queue": -new_queue,
                "opp": -opp_queue * 0.5,
                "switch": -(2 if getattr(tl, "time_since_switch", 0) == 0 else 0),
                "block": -(5 if blocked else 0),
                "clear": cleared * 2,
            }

            tl.debug_info = (action, new_queue, int(reward))

            next_queue = min(new_queue, 5)
            next_opp_queue = min(self.get_queue_near_light(tl, radius=130), 5)
            next_time_since = min(getattr(tl, "time_since_switch", 0), 10)
            next_green = int(getattr(tl, "green", True))
            next_state = (next_queue, next_opp_queue, next_time_since, next_green)

            self.rl_agent.update(state, action, reward, next_state)

        # update cars
        for car in self.cars:
            car.update(dt, self.cars)

        # remove reached
        self.cars = [c for c in self.cars if not getattr(c, "reached", False)]

        # crash detection after movement
        a, b = self.detect_crash()
        if a is not None:
            self.episode_crashes += 1

            crash_penalty = -200.0
            for tl in self.traffic_lights:
                sa = self.last_sa.get(tl)
                if sa is not None:
                    s, act = sa
                    self.rl_agent.update(s, act, crash_penalty, s)

            self.reset_episode()
            return

    # -----------------------------
    # DRAW FUNCTION
    # -----------------------------
    def draw(self, surface):
        # draw cars and lights
        for car in self.cars:
            car.draw(surface)

        for tl in self.traffic_lights:
            tl.draw(surface)

        # RL panel
        font = pygame.font.SysFont("consolas", 14)
        title_font = pygame.font.SysFont("consolas", 16, bold=True)

        line_height = 18
        panel_width = 600
        panel_height = line_height * (len(self.traffic_lights) * 2 + 4)

        panel_x = surface.get_width() - panel_width - 50
        panel_y = 15

        bg = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        bg.fill((20, 20, 20, 220))
        surface.blit(bg, (panel_x, panel_y))

        title = title_font.render("RL Traffic Light Status", True, (255, 255, 255))
        surface.blit(title, (panel_x + 14, panel_y + 2))

        crash_text = font.render(f"Crashes: {self.episode_crashes}", True, (220, 220, 220))
        surface.blit(crash_text, (panel_x + 420, panel_y + 4))

        y_offset = 27

        for tl in self.traffic_lights:
            dbg = getattr(tl, "debug_info", None)
            if dbg is None:
                action, queue, reward = "reset", 0, 0
            else:
                try:
                    action, queue, reward = dbg
                except Exception:
                    action, queue, reward = "reset", 0, 0

            if not hasattr(tl, "total_reward"):
                tl.total_reward = 0

            color = (0, 200, 0) if action == "stay" else (230, 80, 80)

            main_text = (
                f"Light {getattr(tl, 'name', '?'):<5} | "
                f"A:{str(action):<6} | "
                f"Q:{int(queue):<2} | "
                f"R:{int(reward):<3} | "
                f"Score:{int(tl.total_reward):<6}"
            )
            line = font.render(main_text, True, color)
            surface.blit(line, (panel_x + 14, panel_y + y_offset))
            y_offset += line_height

            p = getattr(tl, "penalties", None)
            if not isinstance(p, dict):
                p = {"queue": 0, "opp": 0, "switch": 0, "block": 0, "clear": 0}

            penalty_text = (
                f"      -> Penalties: "
                f"Q:{p.get('queue', 0)}   "
                f"Opp:{p.get('opp', 0)}   "
                f"Sw:{p.get('switch', 0)}   "
                f"Bl:{p.get('block', 0)}   "
                f"Cl:{p.get('clear', 0)}"
            )
            penalty_line = font.render(penalty_text, True, (220, 220, 220))
            surface.blit(penalty_line, (panel_x + 20, panel_y + y_offset))
            y_offset += line_height + 4
