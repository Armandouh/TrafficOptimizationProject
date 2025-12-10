import random
import pygame
from config import MAX_ACTIVE_CARS, SPAWN_INTERVAL_MS, MAX_SPAWN_TRIES, CAR_COLORS, ROAD_MAP
from pathfinding import bfs_find_path
from car import Car


class Simulation:
    def __init__(self, traffic_lights, portals):
        self.cars = []
        self.traffic_lights = traffic_lights
        self.portals = portals
        self.portal_ids = list(portals.keys())
        self.last_spawn_time = pygame.time.get_ticks()

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

    def update(self, dt):
        now = pygame.time.get_ticks()

        if len(self.cars) < MAX_ACTIVE_CARS and now - self.last_spawn_time >= SPAWN_INTERVAL_MS:
            car = self.spawn_car_random()
            if car:
                self.cars.append(car)
            self.last_spawn_time = now

        for car in self.cars:
            car.update(dt, self.cars)

        self.cars = [c for c in self.cars if not c.reached]

        for tl in self.traffic_lights:
            tl.update(dt)

    def draw(self, surface):
        for car in self.cars:
            car.draw(surface)
        for tl in self.traffic_lights:
            tl.draw(surface)
