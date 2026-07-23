from __future__ import annotations

import argparse
import datetime as dt
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REGIONS = [
    "europe_west",
    "europe_east",
    "caucasus",
    "central_asia",
    "arctic",
]


@dataclass(frozen=True)
class GeneratorSpec:
    index: int
    producer_id: str
    region_id: str
    seed: int
    object_id_prefix: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch multiple simulator producers into one Kafka topic."
    )
    parser.add_argument("--generators", type=int, default=3, help="Number of generator processes.")
    parser.add_argument("--profile", default="stream", help="Simulator profile passed to main.py.")
    parser.add_argument(
        "--sink",
        choices=["kafka", "kafka-avro"],
        default="kafka-avro",
        help="Kafka sink type passed to main.py.",
    )
    parser.add_argument(
        "--cluster-id",
        default=None,
        help="Shared run_id for all generator processes. Defaults to timestamped local cluster id.",
    )
    parser.add_argument("--base-seed", type=int, default=42000, help="First generator seed.")
    parser.add_argument(
        "--regions",
        default=",".join(DEFAULT_REGIONS),
        help="Comma-separated region ids. Reused cyclically if generators exceed regions.",
    )
    parser.add_argument("--bootstrap-servers", default="localhost:9094")
    parser.add_argument("--topic", default="airforce.truth.raw.avro.v1")
    parser.add_argument("--schema-registry-url", default="http://localhost:8081")
    parser.add_argument("--tick-seconds", type=int, default=None)
    parser.add_argument("--time-scale", type=float, default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--infinite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run generators indefinitely until interrupted.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without starting them.")
    return parser.parse_args()


def build_specs(args: argparse.Namespace) -> list[GeneratorSpec]:
    regions = [item.strip() for item in args.regions.split(",") if item.strip()]
    if not regions:
        raise ValueError("--regions must contain at least one region id")

    specs = []
    for index in range(args.generators):
        region_id = regions[index % len(regions)]
        producer_id = f"{region_id}-generator-{index + 1:02d}"
        specs.append(
            GeneratorSpec(
                index=index,
                producer_id=producer_id,
                region_id=region_id,
                seed=args.base_seed + index,
                object_id_prefix=f"{producer_id}:",
            )
        )
    return specs


def build_command(repo_root: Path, args: argparse.Namespace, spec: GeneratorSpec) -> list[str]:
    command = [
        sys.executable,
        str(repo_root / "main.py"),
        "--profile",
        args.profile,
        "--sink",
        args.sink,
        "--run-id",
        args.cluster_id,
        "--seed",
        str(spec.seed),
        "--object-id-prefix",
        spec.object_id_prefix,
        "--producer-id",
        spec.producer_id,
        "--region-id",
        spec.region_id,
    ]
    if args.tick_seconds is not None:
        command.extend(["--tick-seconds", str(args.tick_seconds)])
    if args.time_scale is not None:
        command.extend(["--time-scale", str(args.time_scale)])
    if args.max_steps is not None:
        command.extend(["--max-steps", str(args.max_steps)])
    if args.infinite:
        command.append("--infinite")
    return command


def build_env(args: argparse.Namespace, spec: GeneratorSpec) -> dict[str, str]:
    env = os.environ.copy()
    env["SIM_KAFKA_BOOTSTRAP_SERVERS"] = args.bootstrap_servers
    env["SIM_KAFKA_TOPIC"] = args.topic
    env["SIM_SCHEMA_REGISTRY_URL"] = args.schema_registry_url
    env["SIM_KAFKA_CLIENT_ID"] = spec.producer_id
    return env


def terminate_children(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    args = parse_args()
    if args.generators < 1:
        raise ValueError("--generators must be >= 1")

    repo_root = Path(__file__).resolve().parents[1]
    if args.cluster_id is None:
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.cluster_id = f"cluster-{timestamp}"

    specs = build_specs(args)
    print(
        "cluster_start | "
        f"cluster_id={args.cluster_id} | generators={len(specs)} | "
        f"profile={args.profile} | sink={args.sink} | topic={args.topic}"
    )

    commands = [(spec, build_command(repo_root, args, spec)) for spec in specs]
    for spec, command in commands:
        print(
            "generator_plan | "
            f"producer_id={spec.producer_id} | region_id={spec.region_id} | "
            f"seed={spec.seed} | object_id_prefix={spec.object_id_prefix} | "
            f"cmd={' '.join(command)}"
        )

    if args.dry_run:
        return 0

    processes: list[subprocess.Popen[bytes]] = []

    def handle_signal(signum: int, _frame: object) -> None:
        print(f"\ncluster_stop | signal={signum} | terminating={len(processes)}")
        terminate_children(processes)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    for spec, command in commands:
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            env=build_env(args, spec),
        )
        processes.append(process)
        print(f"generator_started | producer_id={spec.producer_id} | pid={process.pid}")

    exit_code = 0
    try:
        for process in processes:
            code = process.wait()
            if code != 0:
                exit_code = code
    finally:
        terminate_children(processes)

    print(f"cluster_done | cluster_id={args.cluster_id} | exit_code={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
