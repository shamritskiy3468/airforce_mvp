import datetime
import argparse
from pathlib import Path

from domain.flight import Flight
from domain.playback_object import PlaybackObject
from configs import build_config
from generator.flight_factory import FlightFactory
from helpers.helpers import Helpers
from helpers.scenario_loader import ScenarioLoader
from engine.engine import SimulationEngine
from engine.navigation.playback_policy import PlaybackNavigationPolicy
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.sinks import JsonlSink
from engine.runtime import run_fast, run_realtime


def main(args):
    if args.clean:
        Helpers.drop_output_files()

    config = build_config(args.profile)

    objects = FlightFactory.generate_scenario(
        scheduled_traffic=config.fleet.scheduled_traffic,
        unscheduled_traffic=config.fleet.unscheduled_traffic,
        transient_phenomena=0,
        area=config.area,
    )

    start_time = datetime.datetime.now(datetime.timezone.utc)
    if args.scenario:
        objects.extend(
            ScenarioLoader.load_objects(
                paths=args.scenario,
                start_time=start_time,
            )
        )

    for obj in objects:
        if obj.latest_position() is not None:
            continue
        if isinstance(obj, PlaybackObject):
            continue
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
        if isinstance(obj, PlaybackObject) and obj.track is not None:
            navigation_policies[obj.object_id] = PlaybackNavigationPolicy()
        elif isinstance(obj, Flight) and obj.route is not None:
            navigation_policies[obj.object_id] = RouteNavigationPolicy()
        else:
            navigation_policies[obj.object_id] = RandomNavigationPolicy(area=config.area)

    sink = Helpers.create_sink(args.sink)
    if args.store_dots and not isinstance(sink, JsonlSink):
        raise ValueError("--store-dots requires --sink json")

    json_sink_filename = sink._path if isinstance(sink, JsonlSink) else None

    engine = SimulationEngine(
        config=config,
        objects=objects,
        navigation_policies=navigation_policies,
        sink=sink,
        start_time=start_time,
    )

    stats = None
    interrupted = False
    try:
        if config.runtime.realtime:
            stats = run_realtime(engine, steps=config.time.max_steps, time_scale=config.time.time_scale)
        else:
            stats = run_fast(engine, steps=config.time.max_steps)
    except KeyboardInterrupt:
        interrupted = True
        print("\ninterrupted | exporting partial waypoints from generated events")
    finally:
        if (
            args.store_dots
            and json_sink_filename is not None
            and Path(json_sink_filename).exists()
        ):
            Helpers.export_dots(input_path=json_sink_filename, output_dir="output/waypoints/", limit=50)

    if stats is not None:
        print(
            f"done | steps={stats.steps} | events={stats.events} | "
            f"elapsed={stats.elapsed_real_seconds:.2f}s | eps={stats.events_per_second:.0f} | "
            f"active_objects={len(engine.objects)} | "
            f"avg_lag_ms={stats.avg_step_lag_seconds * 1000:.2f} | "
            f"max_lag_ms={stats.max_step_lag_seconds * 1000:.2f}"
        )
    elif interrupted:
        print(f"partial_run | active_objects={len(engine.objects)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["debug", "realtime_demo", "load"],
        default="debug",
        help="Simulation config profile",
    )
    parser.add_argument("--sink",
                        required=True,
                        choices=["json", "console", "null"],
                        help="Output sink type")
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Path to a manual scenario JSON file. Can be passed multiple times.",
    )
    parser.add_argument("--store-dots", 
                        action="store_true",
                        help="(DEBUG only) Generate CSV file in output/waypoints/ for loading in QGIS")
    parser.add_argument("--clean", 
                        action="store_true", 
                        help="(DEBUG only) Remove old output (events/waypoints) files before running")
    args = parser.parse_args()
    main(args)
