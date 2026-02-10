import datetime
import time

from generator.flight_factory import FlightFactory
from engine.simulation_loop import SimulationLoop
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.navigation.random_policy import RandomNavigationPolicy


def main():
    objects = FlightFactory.generate_scenario(
        num_passenger=3,
        num_random=2,
    )

    start_time = datetime.datetime.utcnow()

    # начальная позиция
    for obj in objects:
        obj.update_position(
            lat=54.011422,
            lon=28.128171,
            altitude=0.0,
            timestamp=start_time,
        )

    # Политики движения обьектов
    navigation_policies = {}

    for obj in objects:
        if obj.type.value == "passenger_plane":
            navigation_policies[obj.object_id] = RouteNavigationPolicy()
        else:
            navigation_policies[obj.object_id] = RandomNavigationPolicy()

    loop = SimulationLoop(
        objects=objects,
        navigation_policies=navigation_policies,
        tick_seconds=30,
        start_time=start_time,
    )

    for _ in range(20):
        loop.step()
        iter = 0
        for obj in objects:
            pos = obj.positions[-1]
            print(
                f"{loop.current_time.isoformat()} | "
                f"{obj.type.value:<12} | "
                f"lat={pos.lat:.4f}, lon={pos.lon:.4f}, alt={pos.altitude:>5.0f}"
            )
            iter
        print("-" * 80 + f" ({iter})")
        time.sleep(1)


if __name__ == "__main__":
    main()
