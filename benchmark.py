import datetime

from generator.flight_factory import FlightFactory
from engine.config import AreaConfig, FleetConfig, NoiseConfig, RuntimeConfig, SimulationConfig, TimeConfig
from engine.engine import SimulationEngine
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.sinks import NullSink
from engine.runtime import run_fast


def main():
    # Бенчмарк "потолка" CPU: без спавна шумов, без печати, без записи в файл.
    config = SimulationConfig(
        seed=42,
        time=TimeConfig(
            tick_seconds=1,
            time_scale=1.0,
            max_steps=0,
        ),
        area=AreaConfig(min_lat=53.0, max_lat=55.0, min_lon=27.0, max_lon=30.0),
        noise=NoiseConfig(enabled=False, spawn_rate_per_tick=0.0),
        fleet=FleetConfig(planned_flights=0, random_objects=2000),
        runtime=RuntimeConfig(realtime=False),
    )

    objects = FlightFactory.generate_scenario(
        num_passenger=config.fleet.planned_flights,
        num_random=config.fleet.random_objects,
        area=config.area,
    )

    start_time = datetime.datetime.now(datetime.timezone.utc)
    for obj in objects:
        # Стартовая позиция в одной точке (для чистого CPU бенча это ок)
        obj.update_position(lat=54.0, lon=28.0, altitude=0.0, timestamp=start_time)

    navigation_policies = {obj.object_id: RandomNavigationPolicy() for obj in objects}
    engine = SimulationEngine(
        config=config,
        objects=objects,
        navigation_policies=navigation_policies,
        sink=NullSink(),
        start_time=start_time,
    )

    stats = run_fast(engine, steps=200)
    print(
        f"steps={stats.steps} | events={stats.events} | "
        f"elapsed={stats.elapsed_real_seconds:.3f}s | "
        f"events/sec={stats.events_per_second:.0f}"
    )


if __name__ == "__main__":
    main()
