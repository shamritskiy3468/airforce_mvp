import argparse
import datetime

from domain.flight import Flight
from generator.flight_factory import FlightFactory
from engine.config import AreaConfig, FleetConfig, RuntimeConfig, SimulationConfig, TimeConfig, TransientConfig
from engine.engine import SimulationEngine
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.runtime import run_fast
from helpers.helpers import Helpers

def main(args):
    # Бенчмарк "потолка" CPU: без спавна шумов, без печати, без записи в файл.
    config = SimulationConfig(
        seed=42,
        time=TimeConfig(
            tick_seconds=1,
            time_scale=1.0,
            max_steps=0,
        ),
        area=AreaConfig(min_lat=53.0, max_lat=55.0, min_lon=27.0, max_lon=30.0),
        transient=TransientConfig(enabled=False, initial_objects=0, spawn_rate_per_tick=0.0),
        fleet=FleetConfig(scheduled_traffic=20, unscheduled_traffic=200),
        runtime=RuntimeConfig(realtime=False),
    )

    objects = FlightFactory.generate_scenario(
        scheduled_traffic=config.fleet.scheduled_traffic,
        unscheduled_traffic=config.fleet.unscheduled_traffic,
        transient_phenomena=0,
        area=config.area,
    )

    start_time = datetime.datetime.now(datetime.timezone.utc)
    for obj in objects:
        if isinstance(obj, Flight) and obj.route is not None:
            obj.update_position(
                lat=obj.route.origin.lat,
                lon=obj.route.origin.lon,
                altitude=obj.route.origin.altitude,
                timestamp=start_time,
            )
        else:
            obj.update_position(lat=54.0, lon=28.0, altitude=0.0, timestamp=start_time)

    sink = Helpers.create_sink(args.sink)

    navigation_policies = {}
    for obj in objects:
        if isinstance(obj, Flight) and obj.route is not None:
            navigation_policies[obj.object_id] = RouteNavigationPolicy()
        else:
            navigation_policies[obj.object_id] = RandomNavigationPolicy(area=config.area)
    engine = SimulationEngine(
        config=config,
        objects=objects,
        navigation_policies=navigation_policies,
        sink=sink,
        start_time=start_time,
    )

    stats = run_fast(engine, steps=500)
    print(
        f"steps={stats.steps} | events={stats.events} | "
        f"elapsed={stats.elapsed_real_seconds:.3f}s | "
        f"events/sec={stats.events_per_second:.0f}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sink",
        required=True,
        choices=["json", "console", "null"],
        help="Output sink type"
    )
    args = parser.parse_args()
    main(args)
