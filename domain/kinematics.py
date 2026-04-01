from __future__ import annotations

import random
from dataclasses import dataclass

from .enums import PlatformClass


@dataclass(frozen=True)
class KinematicsProfile:
    cruise_speed_kmh: float
    min_speed_kmh: float
    max_speed_kmh: float
    cruise_altitude_m: float
    min_altitude_m: float
    max_altitude_m: float
    climb_rate_mps: float
    descent_rate_mps: float
    max_turn_rate_deg: float


KINEMATICS_BY_PLATFORM: dict[PlatformClass, KinematicsProfile] = {
    PlatformClass.FIXED_WING_AIRCRAFT: KinematicsProfile(
        cruise_speed_kmh=820.0,
        min_speed_kmh=240.0,
        max_speed_kmh=930.0,
        cruise_altitude_m=10_500.0,
        min_altitude_m=0.0,
        max_altitude_m=12_500.0,
        climb_rate_mps=12.0,
        descent_rate_mps=15.0,
        max_turn_rate_deg=4.0,
    ),
    PlatformClass.ROTARY_WING_AIRCRAFT: KinematicsProfile(
        cruise_speed_kmh=180.0,
        min_speed_kmh=0.0,
        max_speed_kmh=280.0,
        cruise_altitude_m=1_200.0,
        min_altitude_m=20.0,
        max_altitude_m=4_500.0,
        climb_rate_mps=6.0,
        descent_rate_mps=6.0,
        max_turn_rate_deg=12.0,
    ),
    PlatformClass.MULTIROTOR_UAV: KinematicsProfile(
        cruise_speed_kmh=90.0,
        min_speed_kmh=20.0,
        max_speed_kmh=160.0,
        cruise_altitude_m=300.0,
        min_altitude_m=20.0,
        max_altitude_m=1_600.0,
        climb_rate_mps=4.0,
        descent_rate_mps=4.0,
        max_turn_rate_deg=18.0,
    ),
    PlatformClass.FIXED_WING_UAV: KinematicsProfile(
        cruise_speed_kmh=220.0,
        min_speed_kmh=120.0,
        max_speed_kmh=320.0,
        cruise_altitude_m=3_000.0,
        min_altitude_m=200.0,
        max_altitude_m=7_000.0,
        climb_rate_mps=8.0,
        descent_rate_mps=8.0,
        max_turn_rate_deg=10.0,
    ),
    PlatformClass.BALLOON: KinematicsProfile(
        cruise_speed_kmh=25.0,
        min_speed_kmh=5.0,
        max_speed_kmh=60.0,
        cruise_altitude_m=4_000.0,
        min_altitude_m=200.0,
        max_altitude_m=18_000.0,
        climb_rate_mps=2.0,
        descent_rate_mps=2.0,
        max_turn_rate_deg=2.0,
    ),
    PlatformClass.BIRD_FLOCK: KinematicsProfile(
        cruise_speed_kmh=45.0,
        min_speed_kmh=15.0,
        max_speed_kmh=90.0,
        cruise_altitude_m=120.0,
        min_altitude_m=5.0,
        max_altitude_m=1_500.0,
        climb_rate_mps=2.0,
        descent_rate_mps=3.0,
        max_turn_rate_deg=35.0,
    ),
    PlatformClass.WEATHER_CELL: KinematicsProfile(
        cruise_speed_kmh=35.0,
        min_speed_kmh=10.0,
        max_speed_kmh=80.0,
        cruise_altitude_m=3_500.0,
        min_altitude_m=500.0,
        max_altitude_m=9_000.0,
        climb_rate_mps=0.5,
        descent_rate_mps=0.5,
        max_turn_rate_deg=3.0,
    ),
    PlatformClass.UNKNOWN: KinematicsProfile(
        cruise_speed_kmh=220.0,
        min_speed_kmh=50.0,
        max_speed_kmh=600.0,
        cruise_altitude_m=2_000.0,
        min_altitude_m=100.0,
        max_altitude_m=10_000.0,
        climb_rate_mps=5.0,
        descent_rate_mps=5.0,
        max_turn_rate_deg=12.0,
    ),
}


def profile_for(platform_class: PlatformClass) -> KinematicsProfile:
    return KINEMATICS_BY_PLATFORM.get(platform_class, KINEMATICS_BY_PLATFORM[PlatformClass.UNKNOWN])


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sample_altitude_m(platform_class: PlatformClass) -> float:
    profile = profile_for(platform_class)
    low = max(profile.min_altitude_m, profile.cruise_altitude_m * 0.6)
    high = min(profile.max_altitude_m, profile.cruise_altitude_m * 1.2)
    if low > high:
        low, high = profile.min_altitude_m, profile.max_altitude_m
    return random.uniform(low, high)


def sample_speed_kmh(platform_class: PlatformClass) -> float:
    profile = profile_for(platform_class)
    low = max(profile.min_speed_kmh, profile.cruise_speed_kmh * 0.75)
    high = min(profile.max_speed_kmh, profile.cruise_speed_kmh * 1.15)
    if low > high:
        low, high = profile.min_speed_kmh, profile.max_speed_kmh
    return random.uniform(low, high)


def move_altitude_towards(
    current_altitude_m: float,
    target_altitude_m: float,
    dt_seconds: int,
    climb_rate_mps: float,
    descent_rate_mps: float,
) -> float:
    delta = target_altitude_m - current_altitude_m
    if delta >= 0:
        max_delta = climb_rate_mps * dt_seconds
        return current_altitude_m + min(delta, max_delta)

    max_delta = descent_rate_mps * dt_seconds
    return current_altitude_m + max(delta, -max_delta)
