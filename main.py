import datetime
import argparse

from domain.flight import Flight
from generator.flight_factory import FlightFactory
from engine.config import (
    AreaConfig,
    EventConfig,
    FleetConfig,
    SimulationConfig,
    TimeConfig,
    TransientConfig,
    RuntimeConfig,
)
# тока для дебага
from helpers.helpers import Helpers
from engine.engine import SimulationEngine
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.sinks import JsonlSink
from engine.runtime import run_fast, run_realtime


def main(args):
    if args.clean:
        Helpers.drop_output_files()

    config = SimulationConfig(
        seed=42,
        time=TimeConfig(
            tick_seconds=1, # 1.0 = realtime (1 sec real = 1 sec sim), >1 ускорение, <1 замедление
            time_scale=1.0, # ускорение симуляции (только для realtime режима)
            max_steps=5000,
        ),
        # QGIS selector для Европы (по границам примерно) + чуть больше, чтобы было 
        # видно объекты, которые только входят/уходят из зоны
        area=AreaConfig(
            min_lat=51.293,
            max_lat=56.285,
            min_lon=23.140,
            max_lon=33.313,
        ),
        transient=TransientConfig(
            enabled=False, ### ВЫКЛЮЧИЛ РАДИ ДЕБУГА
            initial_objects=2,
            spawn_rate_per_tick=0.07,
            ttl_seconds_min=30,
            ttl_seconds_max=300,
            travel_km_min=3.0,
            travel_km_max=10.0,
        ),
        fleet=FleetConfig(
            scheduled_traffic=5,
            unscheduled_traffic=2,
        ),
        runtime=RuntimeConfig(
            realtime=True,
        ),
        events=EventConfig(
            emit_interval_seconds_by_type={
                "fixed_wing_aircraft": 15,
                "rotary_wing_aircraft": 5,
                "multirotor_uav": 5,
                "fixed_wing_uav": 10,
                "balloon": 20,
                "bird_flock": 5,
                "weather_cell": 15,
            },
            emit_when_stationary=False,  # нужно ли спамить стоячие объекты
        ),
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
            lat, lon, altitude, speed, heading = FlightFactory.sample_object_position(
                area=config.area,
                platform_class=obj.platform_class,
            )
            obj.update_position(
                lat=lat,
                lon=lon,
                altitude=altitude,
                speed=speed,
                heading=heading,
                timestamp=start_time,
            )

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
        sink=Helpers.create_sink(args.sink),
        start_time=start_time,
    )

    if config.runtime.realtime:
        stats = run_realtime(engine, steps=config.time.max_steps, time_scale=config.time.time_scale)
    else:
        stats = run_fast(engine, steps=config.time.max_steps)

    print(
        f"done | steps={stats.steps} | events={stats.events} | "
        f"elapsed={stats.elapsed_real_seconds:.2f}s | eps={stats.events_per_second:.0f} | "
        f"active_objects={len(engine.objects)}"
    )

    if args.store_dots:
        Helpers.export_dots(input_path=json_sink_filename, output_dir="output/waypoints/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sink",
                        required=True,
                        choices=["json", "console", "null"],
                        help="Output sink type")
    parser.add_argument("--store-dots", 
                        action="store_true",
                        help="(DEBUG only) Generate CSV file in output/waypoints/ for loading in QGIS")
    parser.add_argument("--clean", 
                        action="store_true", 
                        help="(DEBUG only) Remove old output (events/waypoints) files before running")
    args = parser.parse_args()
    main(args)
