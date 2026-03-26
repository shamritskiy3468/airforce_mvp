import datetime
import time

from domain.flight import Flight
from generator.flight_factory import FlightFactory
from engine.config import (
    AreaConfig,
    FleetConfig,
    NoiseConfig,
    SimulationConfig,
    TimeConfig,
    RuntimeConfig,
)
from engine.engine import SimulationEngine
from engine.navigation.route_policy import RouteNavigationPolicy
from engine.navigation.random_policy import RandomNavigationPolicy
from engine.sinks import JsonlSink # ConsoleSink, NullSink
from engine.runtime import run_fast, run_realtime
from helpers.csv2route import Csv2Route

def main():
    # Конфиг симуляции (один источник правды).
    config = SimulationConfig(
        seed=42, # 42 — это классическое значение для воспроизводимости, можно менять для разных сценариев.
        time=TimeConfig(
            tick_seconds=5, # Имитационные секунлы на тик. 20 секунд — это уже заметный шаг, можно уменьшать для более плавного движения, но будет больше событий и нагрузка.
            time_scale=15.0, # Ускорение симуляции относительно реального времени. 1.0 = realtime, >1 ускорение, <1 замедление. Важно для режима realtime, в режиме fast не влияет.
            max_steps=5000, # Шаги симуляции
        ),
        area=AreaConfig(
            # грубо "окрестности Минска"
            min_lat=53.0,
            max_lat=55.0,
            min_lon=27.0,
            max_lon=30.0,
        ),
        noise=NoiseConfig(
            enabled=True,
            spawn_rate_per_tick=0.05,
            ttl_seconds_min=30,
            ttl_seconds_max=180,
            travel_km_min=3.0,
            travel_km_max=10.0,
        ),
        fleet=FleetConfig(
            planned_flights=100,
            random_objects=30,
        ),
        runtime=RuntimeConfig(
            realtime=False,
        ),
    )

    # Базовый сценарий: шумовые цели + (опционально) рейсы из CSV маршрутов.
    objects = FlightFactory.generate_scenario(
        num_passenger=config.fleet.planned_flights,
        num_random=config.fleet.random_objects,
    )

    # Можно добавить один или несколько маршрутов из CSV.
    # Формат CSV: заголовки lat, lon, altitude

    # route_csv_files = [
    #     "./input/dubai_minst_linear_route.csv", # настройки для линейного маршрута
    # ]

    # for csv_path in route_csv_files:
    #     route = Csv2Route(csv_path).route
    #     flight = FlightFactory.create_passenger_flight(
    #         origin=route.origin,
    #         destination=route.destination,
    #         route=route,
    #     )
    #     objects.append(flight)

    # Используем timezone-aware UTC, чтобы не ловить предупреждения и путаницу со временем.
    start_time = datetime.datetime.now(datetime.timezone.utc)

    # начальная позиция
    for obj in objects:
        # Для рейса — стартуем из origin маршрута.
        if isinstance(obj, Flight) and obj.route is not None:
            obj.update_position(
                lat=obj.route.origin.lat,
                lon=obj.route.origin.lon,
                altitude=obj.route.origin.altitude,
                timestamp=start_time,
            )
        else:
            # Для “шумовых” объектов — произвольная стартовая точка (можно улучшать).
            # Желательно сделать конфиг для выбора рандомных точек из заданной области
            obj.update_position(
                lat=54.011422,
                lon=28.128171,
                altitude=0.0,
                timestamp=start_time,
            )

    # Политики движения обьектов
    navigation_policies = {}

    # Создаем политики движения для каждого объекта в симуляции
    for obj in objects:
        if obj.type.value == "passenger_plane":
            navigation_policies[obj.object_id] = RouteNavigationPolicy()
        else:
            navigation_policies[obj.object_id] = RandomNavigationPolicy()

    # Sink: сейчас выводим редко, чтобы не убивать производительность.
    # sink = ConsoleSink(every_n_events=50)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sink = JsonlSink(path=f"./output/events_{timestamp}.json")
    # sink = NullSink()  # включи, если хочешь просто нагрузку без вывода

    engine = SimulationEngine(
        config=config,
        objects=objects,
        navigation_policies=navigation_policies,
        sink=sink,
        start_time=start_time,
    )

    # Основной цикл: либо realtime (1:1 или ускоренный), либо максимально быстро.
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
