import csv

from domain.route import Route, Waypoint

class Csv2Route:
    def __init__(self, filename: str, default_altitude_m: float = 0.0):
        """Load and return Route object from CSV file"""
        self.route = self._parse_csv(filename, default_altitude_m=default_altitude_m)
    
    @staticmethod
    def _parse_csv(filename: str, default_altitude_m: float = 0.0) -> Route:
        """Parse CSV file and return Route object"""
        waypoints = []
        
        with open(filename, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                altitude_raw = row.get("altitude")
                waypoints.append(
                    Waypoint(
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        altitude=float(altitude_raw) if altitude_raw not in (None, "") else float(default_altitude_m)
                    )
                )
        if len(waypoints) < 2:
            raise ValueError(
                f"Route CSV must contain at least 2 points (origin and destination). Got {len(waypoints)}"
            )
        
        return Route(
            origin=waypoints[0],
            destination=waypoints[-1],
            waypoints=waypoints[1:-1]
        )
    
if __name__ == "__main__":
    # Мини-тест: `python helpers/csv2route.py`
    route_object = Csv2Route("./input/dubai_minst_linear_route.csv").route
    print(route_object)
