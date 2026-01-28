import datetime
from typing import List

class SimulationLoop:
    def __init__(self, objects, navigation_policies, tick_seconds, start_time):
        self.objects = objects
        self.navigation_policies = navigation_policies
        self.tick_seconds = tick_seconds
        self.current_time = start_time

    def step(self):
        for obj in self.objects:
            policy = self.navigation_policies.get(obj.object_id)
            if policy:
                policy.move(obj, self.tick_seconds, self.current_time)

        self.current_time += datetime.timedelta(seconds=self.tick_seconds)
