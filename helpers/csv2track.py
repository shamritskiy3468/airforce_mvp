import csv

from domain.scenario import TrackPointSpec, TrackSpec


class Csv2Track:
    def __init__(self, filename: str):
        self.track_spec = self._parse_csv(filename)

    @staticmethod
    def _parse_csv(filename: str) -> TrackSpec:
        points: list[TrackPointSpec] = []

        with open(filename, newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                points.append(
                    TrackPointSpec(
                        timestamp=row.get("timestamp") or None,
                        offset_seconds=(
                            float(row["offset_seconds"])
                            if row.get("offset_seconds") not in (None, "")
                            else None
                        ),
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        altitude=float(row.get("altitude", 0.0)),
                        speed_kmh=(
                            float(row["speed_kmh"])
                            if row.get("speed_kmh") not in (None, "")
                            else None
                        ),
                        heading_deg=(
                            float(row["heading_deg"])
                            if row.get("heading_deg") not in (None, "")
                            else None
                        ),
                    )
                )

        track_spec = TrackSpec(points=points)
        track_spec.validate()
        return track_spec
