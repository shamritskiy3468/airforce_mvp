import datetime
import time

from generator.flight_factory import FlightFactory
from engine.simulation_loop import SimulationLoop


def main():
    objects = FlightFactory.generate_scenario(
        num_passenger=2,
        num_random=2,
    )

    start_time = datetime.datetime.utcnow()

    # стартовая точка
    for obj in objects:
        obj.update_position(
            lat=50.0,
            lon=10.0,
            altitude=0.0,
            timestamp=start_time,
        )

    loop = SimulationLoop(
        objects=objects,
        tick_seconds=5,
        start_time=start_time,
    )

    for _ in range(10):
        loop.step()
        for obj in objects:
            pos = obj.positions[-1]
            print(
                f"{loop.current_time.isoformat()} | "
                f"{obj.type.value:<18} | "
                f"lat={pos.lat:.4f}, lon={pos.lon:.4f}, alt={pos.altitude:>5.0f}"
            )
        print("-" * 80)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
