import datetime

from domain.flight import Flight
from generator.flight_factory import FlightFactory
from engine.config import (
    AreaConfig,
    EventConfig,
    FleetConfig,
    NoiseConfig,
    SimulationConfig,
    TimeConfig,
    RuntimeConfig,
)
from engine.engine import SimulationEngine
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.sinks import JsonlSink
from engine.runtime import run_fast, run_realtime

def main():
    config = SimulationConfig(
        seed=42,
        time=TimeConfig(
            tick_seconds=5,
            time_scale=15.0,
            max_steps=5000,
        ),
        area=AreaConfig(
            min_lat=53.0,
            max_lat=55.0,
            min_lon=27.0,
            max_lon=30.0,
        ),
        noise=NoiseConfig(
            enabled=False,
            spawn_rate_per_tick=0.05,
            ttl_seconds_min=30,
            ttl_seconds_max=180,
            travel_km_min=3.0,
            travel_km_max=10.0,
        ),
        fleet=FleetConfig(
            planned_flights=1,
            random_objects=0,
        ),
        runtime=RuntimeConfig(
            realtime=False,
        ),
        events=EventConfig(
            emit_interval_seconds_by_type={
                "passenger_plane": 3, # чаще спамить, чтобы было больше данных для отладки + быстро меняют позицию
                "fighter": 3, # чаще спамить, чтобы было больше данных для отладки + быстро меняют позицию
                "helicopter": 5, # просто на посмотреть как часто вообще будут
                "drone": 1, # часто спамить, т.к. могут быть быстрыми и маневренными
                "uav": 10,
                "jammer": 10,
                "bird": 5,
                "cloud": 15,
            },
            emit_when_stationary=False,
        ),
    )

    objects = FlightFactory.generate_scenario(
        num_passenger=config.fleet.planned_flights,
        num_random=config.fleet.random_objects,
        area=config.area,
    )

    # route_csv_files = [
    #     "./input/dubai_minst_linear_route.csv",
    # ]

    # for csv_path in route_csv_files:
    #     route = Csv2Route(csv_path).route
    #     flight = FlightFactory.create_passenger_flight(
    #         origin=route.origin,
    #         destination=route.destination,
    #         route=route,
    #     )
    #     objects.append(flight)

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
                object_type=obj.type,
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
        if obj.type.value == "passenger_plane":
            navigation_policies[obj.object_id] = RouteNavigationPolicy()
        else:
            navigation_policies[obj.object_id] = RandomNavigationPolicy()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sink = JsonlSink(path=f"./output/events_{timestamp}.json")
    # sink = ConsoleSink(every_n_events=100)

    engine = SimulationEngine(
        config=config,
        objects=objects,
        navigation_policies=navigation_policies,
        sink=sink,
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


if __name__ == "__main__":
    main()
