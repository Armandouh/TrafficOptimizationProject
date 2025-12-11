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

    # -----------------------------
    # CLEAN HELPER FUNCTIONS
    # -----------------------------
    def get_queue_near_light(self, tl, radius=80):
        queue = 0
        lx, ly = tl.stop_point
        for car in self.cars:
            if not car.has_cleared_light:
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
                car = Car(start_tile, goal_tile, color, self.traffic_lights)
                return car

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

        # update cars
        for car in self.cars:
            car.update(dt, self.cars)

        # remove reached
        self.cars = [c for c in self.cars if not c.reached]

        # -------------------------
        # RL LOOP FOR EACH LIGHT
        # -------------------------
        for tl in self.traffic_lights:

            # --- ADVANCED STATE ---
            queue = self.get_queue_near_light(tl)
            opp_queue = self.get_queue_near_light(tl, radius=130)
            time_since = min(tl.time_since_switch, 10)
            is_green = int(tl.green)

            state = (
                min(queue, 5),
                min(opp_queue, 5),
                time_since,
                is_green
            )

            # ACTION
            action = self.rl_agent.choose_action(state)

            # APPLY ACTION
            tl.update_with_rl(action)

            # --- ADVANCED REWARD ---
            old_queue = queue
            new_queue = self.get_queue_near_light(tl)
            cleared = self.get_cars_cleared(old_queue, new_queue)
            blocked = self.is_intersection_blocked()

            reward = (
                cleared * 2
                - new_queue
                - opp_queue * 0.5
                - (2 if tl.time_since_switch == 0 else 0)
                - (5 if blocked else 0)
            )

            # --- Store cumulative score ---
            if not hasattr(tl, "total_reward"):
                tl.total_reward = 0
            tl.total_reward += reward

            # --- Store penalty breakdown for visualization ---
            tl.penalties = {
                "queue": -new_queue,
                "opp": -opp_queue * 0.5,
                "switch": -(2 if tl.time_since_switch == 0 else 0),
                "block": -(5 if blocked else 0),
                "clear": cleared * 2
            }

            # visual debugging
            tl.debug_info = (action, new_queue, int(reward))

            # --- NEXT STATE ---
            next_queue = min(new_queue, 5)
            next_opp_queue = min(self.get_queue_near_light(tl, radius=130), 5)
            next_time_since = min(tl.time_since_switch, 10)
            next_green = int(tl.green)

            next_state = (
                next_queue,
                next_opp_queue,
                next_time_since,
                next_green
            )

            # Q-UPDATE
            self.rl_agent.update(state, action, reward, next_state)

    # -----------------------------
    # DRAW FUNCTION
    # -----------------------------
    def draw(self, surface):

        # ---------------------------------------------------------
        # 1) DRAW CARS AND TRAFFIC LIGHTS ON THE MAP
        # ---------------------------------------------------------
        for car in self.cars:
            car.draw(surface)

        for tl in self.traffic_lights:
            tl.draw(surface)

        # ---------------------------------------------------------
        # 2) RL PANEL (TOP-RIGHT, CLEAN & COMPACT)
        # ---------------------------------------------------------

        font = pygame.font.SysFont("consolas", 14)
        title_font = pygame.font.SysFont("consolas", 16, bold=True)

        line_height = 18
        panel_width = 600  # compact width
        panel_height = line_height * (len(self.traffic_lights) * 2 + 2)

        # panel position (shift left & up)
        panel_x = surface.get_width() - panel_width - 50
        panel_y = 15

        # background surface (slightly transparent)
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((20, 20, 20, 220))
        surface.blit(s, (panel_x, panel_y))

        # ---------------------------------------------------------
        # TITLE
        # ---------------------------------------------------------
        title = title_font.render("RL Traffic Light Status", True, (255, 255, 255))
        surface.blit(title, (panel_x + 14, panel_y + 2))

        y_offset = 27  # start text just below title

        # ---------------------------------------------------------
        # LOOP THROUGH TRAFFIC LIGHTS AND DISPLAY THEIR INFO
        # ---------------------------------------------------------
        for tl in self.traffic_lights:

            # --- MAIN RL LINE ---
            if hasattr(tl, "debug_info"):
                action, queue, reward = tl.debug_info
                color = (0, 200, 0) if action == "stay" else (230, 80, 80)

                text = (
                    f"Light {tl.name:<5} | A:{action:<6} | "
                    f"Q:{queue:<2} | R:{reward:<3} | Score:{int(tl.total_reward):<6}"
                )
                line = font.render(text, True, color)

            else:
                text = f"Light {tl.name:<5} | A:---- | Q:-- | R:-- | Score:----"
                line = font.render(text, True, (200, 200, 200))

            surface.blit(line, (panel_x + 14, panel_y + y_offset))
            y_offset += line_height

            # --- PENALTIES LINE ---
            if hasattr(tl, "penalties"):
                p = tl.penalties
                penalty_text = (
                    f"      ↳ Penalties: "
                    f"Q:{p['queue']}   "
                    f"Opp:{p['opp']}   "
                    f"Sw:{p['switch']}   "
                    f"Bl:{p['block']}   "
                    f"Cl:{p['clear']}"
                )
                penalty_line = font.render(penalty_text, True, (220, 220, 220))
                surface.blit(penalty_line, (panel_x + 20, panel_y + y_offset))
                y_offset += line_height

            # small spacing between lights
            y_offset += 4