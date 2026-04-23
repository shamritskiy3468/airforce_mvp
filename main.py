import datetime
import argparse
import random
from collections import Counter
from dataclasses import replace
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
    if args.tick_seconds is not None or args.time_scale is not None or args.max_steps is not None or args.infinite:
        config = replace(
            config,
            time=replace(
                config.time,
                tick_seconds=args.tick_seconds if args.tick_seconds is not None else config.time.tick_seconds,
                time_scale=args.time_scale if args.time_scale is not None else config.time.time_scale,
                max_steps=(
                    None
                    if args.infinite
                    else (args.max_steps if args.max_steps is not None else config.time.max_steps)
                ),
            ),
        )
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
    print(f"run | run_id={engine.run_id} | profile={args.profile}")

    stats = None
    interrupted = False
    progress_state = {
        "last_step": 0,
        "last_events": 0,
        "last_elapsed_real_seconds": 0.0,
    }

    def format_counter(counter: Counter[str], limit: int = 3, aliases: dict[str, str] | None = None) -> str:
        if not counter:
            return "-"
        parts = []
        for key, value in counter.most_common(limit):
            label = aliases.get(key, key) if aliases is not None else key
            parts.append(f"{label}:{value}")
        return ",".join(parts)

    def format_rate(value: float) -> str:
        if value >= 10:
            return f"{value:.0f}"
        if value >= 1:
            return f"{value:.1f}"
        return f"{value:.2f}"

    def progress_log(step: int, total_events: int, elapsed_real_seconds: float, eng: SimulationEngine):
        sim_elapsed_seconds = step * config.time.tick_seconds
        sim_hours = sim_elapsed_seconds / 3600.0
        eps = total_events / elapsed_real_seconds if elapsed_real_seconds > 0 else 0.0
        step_delta = step - progress_state["last_step"]
        events_delta = total_events - progress_state["last_events"]
        elapsed_delta = elapsed_real_seconds - progress_state["last_elapsed_real_seconds"]
        recent_eps = events_delta / elapsed_delta if elapsed_delta > 0 else 0.0
        max_steps_label = "inf" if config.time.max_steps is None else str(config.time.max_steps)

        active_objects = []
        pending_objects = 0
        for obj in eng.objects:
            if obj.activation_time is not None and eng.current_time < obj.activation_time:
                pending_objects += 1
                continue
            active_objects.append(obj)

        bucket_counter = Counter(obj.scenario_bucket.value for obj in active_objects)
        platform_counter = Counter(obj.platform_class.value for obj in active_objects)
        flight_state_counter = Counter(
            obj.state.value
            for obj in active_objects
            if isinstance(obj, Flight)
        )

        bucket_aliases = {
            "scheduled_traffic": "sch",
            "unscheduled_traffic": "uns",
            "transient_phenomena": "trn",
        }

        print(
            f"progress | sim_time={eng.current_time.isoformat()} | "
            f"step={step}/{max_steps_label} (+{step_delta}) | "
            f"sim_hours={sim_hours:.2f} | "
            f"events=+{events_delta}/{total_events} | "
            f"eps={format_rate(recent_eps)} recent, {format_rate(eps)} avg | "
            f"world=active:{len(active_objects)} pending:{pending_objects} | "
            f"buckets={format_counter(bucket_counter, limit=3, aliases=bucket_aliases)} | "
            f"platforms={format_counter(platform_counter, limit=3)} | "
            f"flight_states={format_counter(flight_state_counter, limit=3)}"
        )
        progress_state["last_step"] = step
        progress_state["last_events"] = total_events
        progress_state["last_elapsed_real_seconds"] = elapsed_real_seconds

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
            f"run_id={engine.run_id} | "
            f"avg_lag_ms={stats.avg_step_lag_seconds * 1000:.2f} | "
            f"max_lag_ms={stats.max_step_lag_seconds * 1000:.2f}"
        )
    elif interrupted:
        print(f"partial_run | active_objects={len(engine.objects)} | run_id={engine.run_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["debug", "realtime_demo", "load", "stream"],
        default="debug",
        help="Simulation config profile",
    )
    parser.add_argument(
        "--tick-seconds",
        type=int,
        help="Override simulation tick size in simulation seconds",
    )
    parser.add_argument(
        "--time-scale",
        type=float,
        help="Override realtime scale: 1.0 means 1 real second = 1 simulation second",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        help="Override maximum step count",
    )
    parser.add_argument(
        "--infinite",
        action="store_true",
        help="Run indefinitely until interrupted",
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
