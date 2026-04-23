import datetime
import argparse
import random
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
    if config.seed is not None:
        random.seed(config.seed)

    objects = FlightFactory.generate_scenario(
        scheduled_traffic=config.fleet.scheduled_traffic,
        unscheduled_traffic=config.fleet.unscheduled_traffic,
        transient_phenomena=0,
        area=config.area,
        restrict_airport_pairs_to_area=config.fleet.restrict_airport_pairs_to_area,
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

    # Разнос времени старта объектов, чтобы все не "взлетали" одновременно.
    if config.runtime.startup_spread_seconds > 0:
        for obj in objects:
            offset = random.uniform(0, config.runtime.startup_spread_seconds)
            obj.activation_time = start_time + datetime.timedelta(seconds=offset)
    else:
        for obj in objects:
            obj.activation_time = start_time

    activation_offsets = []
    for obj in objects:
        if obj.activation_time is None:
            continue
        activation_offsets.append((obj.activation_time - start_time).total_seconds())
    if activation_offsets:
        print(
            "startup | "
            f"objects={len(objects)} | "
            f"activation_spread_sec=[{min(activation_offsets):.1f}..{max(activation_offsets):.1f}] | "
            f"simultaneous_start={'yes' if max(activation_offsets) == 0 else 'no'}"
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

    def progress_log(step: int, total_events: int, elapsed_real_seconds: float, eng: SimulationEngine):
        sim_elapsed_seconds = step * config.time.tick_seconds
        sim_hours = sim_elapsed_seconds / 3600.0
        eps = total_events / elapsed_real_seconds if elapsed_real_seconds > 0 else 0.0
        print(
            f"progress | step={step}/{config.time.max_steps} | "
            f"sim_hours={sim_hours:.2f} | elapsed_real={elapsed_real_seconds:.1f}s | "
            f"eps={eps:.0f} | active_objects={len(eng.objects)}"
        )

    try:
        if config.runtime.realtime:
            stats = run_realtime(
                engine,
                steps=config.time.max_steps,
                time_scale=config.time.time_scale,
                progress_every_steps=config.runtime.progress_every_steps,
                progress_cb=progress_log,
            )
        else:
            stats = run_fast(
                engine,
                steps=config.time.max_steps,
                progress_every_steps=config.runtime.progress_every_steps,
                progress_cb=progress_log,
            )
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
