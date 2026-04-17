from __future__ import annotations

from engine.config import (
    AreaConfig,
    EventConfig,
    FleetConfig,
    RuntimeConfig,
    SimulationConfig,
    TimeConfig,
    TransientConfig,
)


def build_config(profile: str) -> SimulationConfig:
    """
    Готовые профили запуска:
      - debug: мало объектов, удобно смотреть руками
      - realtime_demo: realtime 1:1, умеренное число объектов
      - load: быстрый режим для нагрузочного прогона
    """
    profile = profile.lower()

    base_events = EventConfig(
        emit_interval_seconds_by_type={
            "fixed_wing_aircraft": 15,
            "rotary_wing_aircraft": 5,
            "multirotor_uav": 5,
            "fixed_wing_uav": 10,
            "balloon": 5,
            "bird_flock": 5,
            "weather_cell": 15,
        },
        emit_when_stationary=False,
    )

    base_area = AreaConfig(
        min_lat=51.293,
        max_lat=56.285,
        min_lon=23.140,
        max_lon=33.313,
    )

    if profile == "debug":
        return SimulationConfig(
            seed=42,
            time=TimeConfig(tick_seconds=5, time_scale=1.0, max_steps=600),
            area=base_area,
            transient=TransientConfig(
                enabled=False,
                initial_objects=0,
                spawn_rate_per_tick=0.0,
                ttl_seconds_min=30,
                ttl_seconds_max=300,
                travel_km_min=3.0,
                travel_km_max=10.0,
            ),
            fleet=FleetConfig(scheduled_traffic=2, unscheduled_traffic=3),
            runtime=RuntimeConfig(realtime=False),
            events=base_events,
        )

    if profile == "realtime_demo":
        return SimulationConfig(
            seed=42,
            time=TimeConfig(tick_seconds=5, time_scale=1.0, max_steps=120),
            area=base_area,
            transient=TransientConfig(
                enabled=True,
                initial_objects=1,
                spawn_rate_per_tick=0.03,
                ttl_seconds_min=30,
                ttl_seconds_max=300,
                travel_km_min=3.0,
                travel_km_max=10.0,
            ),
            fleet=FleetConfig(scheduled_traffic=5, unscheduled_traffic=5),
            runtime=RuntimeConfig(realtime=True),
            events=base_events,
        )

    if profile == "load":
        return SimulationConfig(
            seed=42,
            time=TimeConfig(tick_seconds=1, time_scale=20.0, max_steps=5000),
            area=base_area,
            transient=TransientConfig(
                enabled=True,
                initial_objects=50,
                spawn_rate_per_tick=0.2,
                ttl_seconds_min=30,
                ttl_seconds_max=300,
                travel_km_min=3.0,
                travel_km_max=10.0,
            ),
            fleet=FleetConfig(scheduled_traffic=100, unscheduled_traffic=400),
            runtime=RuntimeConfig(realtime=False),
            events=base_events,
        )

    raise ValueError(f"Unknown profile: {profile!r}. Allowed: debug, realtime_demo, load")

