import json
import csv
import datetime
from pathlib import Path
from typing import Union, Dict, List
from engine.sinks import JsonlSink, NullSink, ConsoleSink


class Helpers:
    @staticmethod
    def export_dots(input_path: Union[str, Path],output_dir: Union[str, Path]) -> None:
        """
        Читает JSONL-файл, группирует записи по object_id
        и создаёт отдельный CSV-файл для каждого объекта.
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # удобно добавлять на карту QGIS чтоб посмотреть че там получается
        
        grouped: Dict[str, List[tuple]] = {}

        with input_path.open("r", encoding="utf-8") as infile:
            for line in infile:
                if not line.strip():
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                object_id = obj.get("object_id")
                lat = obj.get("lat")
                lon = obj.get("lon")
                event_type = obj.get("event_type")

                if event_type == "despawned":
                    continue

                if object_id and lat is not None and lon is not None:
                    grouped.setdefault(object_id, []).append((lat, lon))

        for object_id, coords in grouped.items():
            filename = output_dir / f"{object_id}_dots.csv"

            with filename.open("w", newline="", encoding="utf-8") as outfile:
                writer = csv.writer(outfile)
                writer.writerow(["lat", "lon"])

                for lat, lon in coords:
                    writer.writerow([lat, lon])
    
    @staticmethod
    def drop_output_files() -> None:
        # Почистить всё из output перед запуском
        base = Path("output")
        waypoints = base / "waypoints"

        if base.exists():
            for item in base.iterdir():
                if item.is_file():
                    item.unlink()

        if waypoints.exists():
            for item in waypoints.iterdir():
                if item.is_file():
                    item.unlink()
    
    @staticmethod
    def create_sink(sink_type: str):
        sink_type = sink_type.lower()

        if sink_type == "json":
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            json_sink_filename = f"./output/events_{timestamp}.json"
            return JsonlSink(path=json_sink_filename)
        elif sink_type == "console":
            return ConsoleSink()
        elif sink_type == "null":
            return NullSink()
        else:
            raise ValueError(f"Unknown sink type: {sink_type!r}. "
                            "Allowed: json, console, null")
