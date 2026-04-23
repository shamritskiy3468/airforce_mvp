from dataclasses import dataclass
import math
import random
import string
from typing import List, Optional

from domain.air_object import AirObject
from domain.enums import (
    CooperationStatus,
    FlightCategory,
    MissionProfile,
    PlatformClass,
    ScenarioBucket,
    TruthAffiliation,
)
from domain.flight import Flight
from domain.kinematics import profile_for, sample_altitude_m, sample_speed_kmh
from domain.route import Route, Waypoint
from engine.config import AreaConfig
from engine.navigation.math import haversine_distance


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    lat: float
    lon: float


AIRPORTS: list[Airport] = [
    Airport(code="AMS", name="Amsterdam Airport Schiphol", lat=52.3086, lon=4.7639),
    Airport(code="RTM", name="Rotterdam The Hague Airport", lat=51.9569, lon=4.4372),
    Airport(code="EIN", name="Eindhoven Airport", lat=51.4501, lon=5.3745),
    Airport(code="MST", name="Maastricht Aachen Airport", lat=50.9117, lon=5.7701),
    Airport(code="GRQ", name="Groningen Airport Eelde", lat=53.1197, lon=6.5794),
    Airport(code="LHR", name="London Heathrow Airport", lat=51.4700, lon=-0.4543),
    Airport(code="LGW", name="London Gatwick Airport", lat=51.1537, lon=-0.1821),
    Airport(code="STN", name="London Stansted Airport", lat=51.8850, lon=0.2350),
    Airport(code="LTN", name="London Luton Airport", lat=51.8747, lon=-0.3683),
    Airport(code="MAN", name="Manchester Airport", lat=53.3650, lon=-2.2728),
    Airport(code="EDI", name="Edinburgh Airport", lat=55.9500, lon=-3.3725),
    Airport(code="GLA", name="Glasgow Airport", lat=55.8719, lon=-4.4331),
    Airport(code="BHX", name="Birmingham Airport", lat=52.4539, lon=-1.7480),
    Airport(code="CDG", name="Paris Charles de Gaulle Airport", lat=49.0097, lon=2.5479),
    Airport(code="ORY", name="Paris Orly Airport", lat=48.7262, lon=2.3652),
    Airport(code="NCE", name="Nice Côte d'Azur Airport", lat=43.6653, lon=7.2150),
    Airport(code="LYS", name="Lyon-Saint Exupéry Airport", lat=45.7256, lon=5.0811),
    Airport(code="MRS", name="Marseille Provence Airport", lat=43.4367, lon=5.2150),
    Airport(code="TLS", name="Toulouse-Blagnac Airport", lat=43.6293, lon=1.3633),
    Airport(code="FRA", name="Frankfurt Airport", lat=50.0379, lon=8.5622),
    Airport(code="MUC", name="Munich Airport", lat=48.3538, lon=11.7861),
    Airport(code="DUS", name="Düsseldorf Airport", lat=51.2895, lon=6.7668),
    Airport(code="BER", name="Berlin Brandenburg Airport", lat=52.3667, lon=13.5033),
    Airport(code="HAM", name="Hamburg Airport", lat=53.6304, lon=9.9882),
    Airport(code="STR", name="Stuttgart Airport", lat=48.6899, lon=9.2219),
    Airport(code="CGN", name="Cologne Bonn Airport", lat=50.8659, lon=7.1427),
    Airport(code="MAD", name="Madrid Barajas Airport", lat=40.4983, lon=-3.5676),
    Airport(code="BCN", name="Barcelona El Prat Airport", lat=41.2974, lon=2.0833),
    Airport(code="PMI", name="Palma de Mallorca Airport", lat=39.5517, lon=2.7388),
    Airport(code="AGP", name="Málaga Airport", lat=36.6749, lon=-4.4991),
    Airport(code="VLC", name="Valencia Airport", lat=39.4893, lon=-0.4816),
    Airport(code="SVQ", name="Seville Airport", lat=37.4180, lon=-5.8931),
    Airport(code="FCO", name="Rome Fiumicino Airport", lat=41.8003, lon=12.2389),
    Airport(code="MXP", name="Milan Malpensa Airport", lat=45.6301, lon=8.7281),
    Airport(code="LIN", name="Milan Linate Airport", lat=45.4451, lon=9.2767),
    Airport(code="VCE", name="Venice Marco Polo Airport", lat=45.5053, lon=12.3519),
    Airport(code="NAP", name="Naples International Airport", lat=40.8860, lon=14.2908),
    Airport(code="ZRH", name="Zurich Airport", lat=47.4581, lon=8.5555),
    Airport(code="GVA", name="Geneva Airport", lat=46.2381, lon=6.1089),
    Airport(code="VIE", name="Vienna International Airport", lat=48.1103, lon=16.5697),
    Airport(code="SZG", name="Salzburg Airport", lat=47.7933, lon=13.0043),
    Airport(code="BRU", name="Brussels Airport", lat=50.9010, lon=4.4844),
    Airport(code="CRL", name="Brussels South Charleroi Airport", lat=50.4592, lon=4.4538),
    Airport(code="CPH", name="Copenhagen Airport", lat=55.6181, lon=12.6560),
    Airport(code="BLL", name="Billund Airport", lat=55.7403, lon=9.1518),
    Airport(code="ARN", name="Stockholm Arlanda Airport", lat=59.6519, lon=17.9186),
    Airport(code="GOT", name="Gothenburg Landvetter Airport", lat=57.6628, lon=12.2798),
    Airport(code="OSL", name="Oslo Gardermoen Airport", lat=60.1976, lon=11.1004),
    Airport(code="BGO", name="Bergen Airport", lat=60.2934, lon=5.2181),
    Airport(code="HEL", name="Helsinki Airport", lat=60.3172, lon=24.9633),
    Airport(code="TMP", name="Tampere Airport", lat=61.4141, lon=23.6044),
    Airport(code="DUB", name="Dublin Airport", lat=53.4213, lon=-6.2701),
    Airport(code="ORK", name="Cork Airport", lat=51.8413, lon=-8.4911),
    Airport(code="PRG", name="Prague Airport", lat=50.1008, lon=14.2600),
    Airport(code="BRQ", name="Brno Airport", lat=49.1513, lon=16.6944),
    Airport(code="WAW", name="Warsaw Chopin Airport", lat=52.1657, lon=20.9671),
    Airport(code="KRK", name="Kraków Airport", lat=50.0777, lon=19.7848),
    Airport(code="GDN", name="Gdańsk Airport", lat=54.3776, lon=18.4662),
    Airport(code="BUD", name="Budapest Airport", lat=47.4369, lon=19.2556),
    Airport(code="ATH", name="Athens International Airport", lat=37.9364, lon=23.9475),
    Airport(code="HER", name="Heraklion Airport", lat=35.3397, lon=25.1803),
    Airport(code="IST", name="Istanbul Airport", lat=41.2753, lon=28.7519),
    Airport(code="SAW", name="Istanbul Sabiha Gökçen Airport", lat=40.8986, lon=29.3092),
    Airport(code="LIS", name="Lisbon Airport", lat=38.7742, lon=-9.1342),
    Airport(code="OPO", name="Porto Airport", lat=41.2481, lon=-8.6814),
    Airport(code="KEF", name="Keflavik International Airport", lat=63.9850, lon=-22.6056),
    Airport(code="RIX", name="Riga Airport", lat=56.9236, lon=23.9711),
    Airport(code="TLL", name="Tallinn Airport", lat=59.4133, lon=24.8328),
    Airport(code="VNO", name="Vilnius Airport", lat=54.6341, lon=25.2858),
    Airport(code="SOF", name="Sofia Airport", lat=42.6952, lon=23.4062),
    Airport(code="VAR", name="Varna Airport", lat=43.2321, lon=27.8251),
    Airport(code="OTP", name="Bucharest Henri Coandă Airport", lat=44.5711, lon=26.0850),
    Airport(code="BEG", name="Belgrade Airport", lat=44.8184, lon=20.3091),
    Airport(code="ZAG", name="Zagreb Airport", lat=45.7429, lon=16.0688),
    Airport(code="LJU", name="Ljubljana Airport", lat=46.2237, lon=14.4576),
    Airport(code="SKG", name="Thessaloniki Airport", lat=40.5197, lon=22.9709),
    Airport(code="TGD", name="Podgorica Airport", lat=42.3594, lon=19.2519),
    Airport(code="SJJ", name="Sarajevo Airport", lat=43.8246, lon=18.3315),
    Airport(code="TIA", name="Tirana Airport", lat=41.4147, lon=19.7206),
    Airport(code="EVN", name="Yerevan Zvartnots Airport", lat=40.1473, lon=44.3959),
    Airport(code="GYD", name="Baku Heydar Aliyev Airport", lat=40.4675, lon=50.0467),
    Airport(code="MSQ", name="Minsk National Airport", lat=53.8825, lon=28.0307),
    Airport(code="KIV", name="Chișinău Airport", lat=46.9277, lon=28.9310),
    Airport(code="LCA", name="Larnaca Airport", lat=34.8751, lon=33.6249),
    Airport(code="MLA", name="Malta International Airport", lat=35.8575, lon=14.4775)
]


class FlightFactory:
    """Scenario generator for scheduled traffic, unscheduled traffic, and transient phenomena."""

    @staticmethod
    def generate_scenario(
        scheduled_traffic: int = 2,
        unscheduled_traffic: int = 3,
        transient_phenomena: int = 0,
        area: Optional[AreaConfig] = None,
        restrict_airport_pairs_to_area: bool = True,
    ) -> List[AirObject]:
        scenario = []

        for _ in range(scheduled_traffic):
            scenario.append(
                FlightFactory.create_scheduled_traffic(
                    area,
                    restrict_airport_pairs_to_area=restrict_airport_pairs_to_area,
                )
            )

        for _ in range(unscheduled_traffic):
            scenario.append(FlightFactory.create_unscheduled_traffic(area))

        for _ in range(transient_phenomena):
            scenario.append(FlightFactory.create_transient_object())

        return scenario

    @staticmethod
    def create_scheduled_traffic(area: Optional[AreaConfig], restrict_airport_pairs_to_area: bool = True) -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.FIXED_WING_AIRCRAFT,
                PlatformClass.ROTARY_WING_AIRCRAFT,
                PlatformClass.MULTIROTOR_UAV,
            ],
            weights=[0.75, 0.15, 0.10],
            k=1,
        )[0]
        mission_profile = random.choices(
            population=[MissionProfile.TRANSIT, MissionProfile.TRAINING],
            weights=[0.85, 0.15],
            k=1,
        )[0]

        if (
            platform_class == PlatformClass.FIXED_WING_AIRCRAFT
            and mission_profile == MissionProfile.TRANSIT
            and random.random() < 0.75
        ):
            passenger = FlightFactory.create_scheduled_passenger_flight(
                area,
                restrict_airport_pairs_to_area=restrict_airport_pairs_to_area,
            )
            if passenger is not None:
                return passenger

        route = (
            FlightFactory.create_area_transit_route(area, platform_class)
            if area
            else FlightFactory.create_demo_route(platform_class)
        )
        return FlightFactory.create_routed_object(
            scenario_bucket=ScenarioBucket.SCHEDULED_TRAFFIC,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=random.choice([TruthAffiliation.CIVILIAN, TruthAffiliation.FRIENDLY]),
            cooperation_status=CooperationStatus.COOPERATIVE,
            route=route,
            callsign=FlightFactory._generate_callsign(prefix="ST"),
            flight_category=(
                FlightCategory.TRAINING
                if mission_profile == MissionProfile.TRAINING
                else FlightCategory.UTILITY
            ),
        )

    @staticmethod
    def create_scheduled_passenger_flight(area: Optional[AreaConfig], restrict_airport_pairs_to_area: bool = True) -> Flight | None:
        area_for_airports = area if restrict_airport_pairs_to_area else None
        airport_pair = FlightFactory._sample_airport_pair(area_for_airports)
        if airport_pair is None:
            return None

        origin_airport, destination_airport = airport_pair
        route = FlightFactory.create_airport_route(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            platform_class=PlatformClass.FIXED_WING_AIRCRAFT,
        )
        return FlightFactory.create_routed_object(
            scenario_bucket=ScenarioBucket.SCHEDULED_TRAFFIC,
            platform_class=PlatformClass.FIXED_WING_AIRCRAFT,
            mission_profile=MissionProfile.TRANSIT,
            truth_affiliation=TruthAffiliation.CIVILIAN,
            cooperation_status=CooperationStatus.COOPERATIVE,
            route=route,
            callsign=FlightFactory._generate_passenger_callsign(),
            flight_category=FlightCategory.PASSENGER,
            origin_label=origin_airport.code,
            destination_label=destination_airport.code,
        )

    @staticmethod
    def create_unscheduled_traffic(area: Optional[AreaConfig]) -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.FIXED_WING_AIRCRAFT,
                PlatformClass.ROTARY_WING_AIRCRAFT,
                PlatformClass.FIXED_WING_UAV,
                PlatformClass.MULTIROTOR_UAV,
            ],
            weights=[0.30, 0.20, 0.30, 0.20],
            k=1,
        )[0]

        mission_by_platform = {
            PlatformClass.FIXED_WING_AIRCRAFT: [MissionProfile.PATROL, MissionProfile.RECON, MissionProfile.BORDER_PENETRATION],
            PlatformClass.ROTARY_WING_AIRCRAFT: [MissionProfile.PATROL, MissionProfile.LOITER, MissionProfile.RECON],
            PlatformClass.FIXED_WING_UAV: [MissionProfile.RECON, MissionProfile.LOITER, MissionProfile.BORDER_PENETRATION],
            PlatformClass.MULTIROTOR_UAV: [MissionProfile.LOITER, MissionProfile.RECON],
        }
        mission_profile = random.choice(mission_by_platform[platform_class])
        truth_affiliation = random.choices(
            population=[TruthAffiliation.ADVERSARY, TruthAffiliation.NEUTRAL],
            weights=[0.7, 0.3],
            k=1,
        )[0]
        cooperation_status = random.choice([CooperationStatus.NON_COOPERATIVE, CooperationStatus.SILENT])

        should_route = area is not None and (
            platform_class in (PlatformClass.FIXED_WING_AIRCRAFT, PlatformClass.FIXED_WING_UAV)
            or mission_profile == MissionProfile.BORDER_PENETRATION
        )

        if should_route:
            route = FlightFactory.create_area_transit_route(area, platform_class)
            return FlightFactory.create_routed_object(
                scenario_bucket=ScenarioBucket.UNSCHEDULED_TRAFFIC,
                platform_class=platform_class,
                mission_profile=mission_profile,
                truth_affiliation=truth_affiliation,
                cooperation_status=cooperation_status,
                route=route,
                callsign=FlightFactory._generate_callsign(prefix="UT"),
                flight_category=FlightFactory._flight_category_for_unscheduled(platform_class),
            )

        return AirObject(
            scenario_bucket=ScenarioBucket.UNSCHEDULED_TRAFFIC,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=truth_affiliation,
            cooperation_status=cooperation_status,
            max_lifetime_seconds=FlightFactory._sample_unscheduled_free_lifetime_seconds(
                platform_class=platform_class,
                mission_profile=mission_profile,
            ),
        )

    @staticmethod
    def create_transient_object() -> AirObject:
        platform_class = random.choices(
            population=[
                PlatformClass.BIRD_FLOCK,
                PlatformClass.WEATHER_CELL,
                PlatformClass.BALLOON,
            ],
            weights=[0.5, 0.35, 0.15],
            k=1,
        )[0]

        mission_profile = (
            MissionProfile.WEATHER_DRIFT
            if platform_class in (PlatformClass.WEATHER_CELL, PlatformClass.BALLOON)
            else MissionProfile.LOITER
        )

        return AirObject(
            scenario_bucket=ScenarioBucket.TRANSIENT_PHENOMENA,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=TruthAffiliation.NEUTRAL,
            cooperation_status=CooperationStatus.SILENT,
        )

    @staticmethod
    def create_routed_object(
        scenario_bucket: ScenarioBucket,
        platform_class: PlatformClass,
        mission_profile: MissionProfile,
        truth_affiliation: TruthAffiliation,
        cooperation_status: CooperationStatus,
        route: Route,
        callsign: Optional[str] = None,
        flight_category: FlightCategory = FlightCategory.UNKNOWN,
        origin_label: str | None = None,
        destination_label: str | None = None,
    ) -> Flight:
        return Flight(
            scenario_bucket=scenario_bucket,
            platform_class=platform_class,
            mission_profile=mission_profile,
            truth_affiliation=truth_affiliation,
            cooperation_status=cooperation_status,
            route=route,
            callsign=callsign,
            flight_category=flight_category,
            origin_label=origin_label,
            destination_label=destination_label,
        )

    @staticmethod
    def _flight_category_for_unscheduled(platform_class: PlatformClass) -> FlightCategory:
        if platform_class == PlatformClass.FIXED_WING_AIRCRAFT:
            return FlightCategory.GENERAL_AVIATION
        if platform_class in (PlatformClass.FIXED_WING_UAV, PlatformClass.MULTIROTOR_UAV):
            return FlightCategory.UTILITY
        return FlightCategory.UTILITY

    @staticmethod
    def sample_object_position(
        area: AreaConfig,
        platform_class: PlatformClass,
    ) -> tuple[float, float, float, float, float]:
        return (
            random.uniform(area.min_lat, area.max_lat),
            random.uniform(area.min_lon, area.max_lon),
            sample_altitude_m(platform_class),
            sample_speed_kmh(platform_class),
            random.uniform(0, 360),
        )

    @staticmethod
    def create_demo_route(platform_class: PlatformClass) -> Route:
        cruise_altitude = profile_for(platform_class).cruise_altitude_m
        origin = Waypoint(53.0, 27.0, 0.0)
        climb = Waypoint(53.4, 27.6, cruise_altitude * 0.85)
        descent = Waypoint(54.2, 28.6, cruise_altitude * 0.85)
        destination = Waypoint(54.8, 29.5, 0.0)
        return Route(origin=origin, destination=destination, waypoints=[climb, descent])

    @staticmethod
    def create_area_transit_route(area: AreaConfig, platform_class: PlatformClass) -> Route:
        origin, destination = FlightFactory._sample_boundary_pair(area)
        return FlightFactory._build_curved_route(
            origin=origin,
            destination=destination,
            platform_class=platform_class,
            force_curve=False,
        )

    @staticmethod
    def create_airport_route(
        origin_airport: Airport,
        destination_airport: Airport,
        platform_class: PlatformClass,
    ) -> Route:
        return FlightFactory._build_curved_route(
            origin=Waypoint(origin_airport.lat, origin_airport.lon, 0.0),
            destination=Waypoint(destination_airport.lat, destination_airport.lon, 0.0),
            platform_class=platform_class,
            force_curve=True,
        )

    @staticmethod
    def _build_curved_route(
        origin: Waypoint,
        destination: Waypoint,
        platform_class: PlatformClass,
        force_curve: bool,
    ) -> Route:
        profile = profile_for(platform_class)
        distance_km = haversine_distance(origin.lat, origin.lon, destination.lat, destination.lon)

        if distance_km < 120.0:
            fractions = [0.32, 0.68]
            offset_base_km = random.uniform(6.0, 18.0)
        elif distance_km < 260.0:
            fractions = [0.22, 0.52, 0.80]
            offset_base_km = random.uniform(12.0, 35.0)
        else:
            fractions = [0.18, 0.40, 0.63, 0.84]
            offset_base_km = random.uniform(20.0, min(90.0, distance_km * 0.12))

        if force_curve and distance_km >= 180.0:
            offset_base_km = max(offset_base_km, min(110.0, distance_km * 0.10))

        if not force_curve and distance_km < 90.0:
            offset_base_km *= 0.5

        bend_sign = random.choice([-1.0, 1.0])
        waypoints: list[Waypoint] = []
        for idx, fraction in enumerate(fractions):
            altitude = FlightFactory._route_altitude_for_fraction(
                fraction=fraction,
                cruise_altitude_m=profile.cruise_altitude_m,
            )
            intensity = FlightFactory._offset_intensity(idx=idx, total=len(fractions))
            lateral_km = offset_base_km * intensity * bend_sign
            if not force_curve and abs(lateral_km) < 4.0:
                lateral_km = 0.0
            waypoints.append(
                FlightFactory._offset_interpolated_waypoint(
                    start=origin,
                    end=destination,
                    fraction=fraction,
                    altitude=altitude,
                    lateral_offset_km=lateral_km,
                )
            )

        return Route(origin=origin, destination=destination, waypoints=waypoints)

    @staticmethod
    def _sample_boundary_pair(area: AreaConfig) -> tuple[Waypoint, Waypoint]:
        edge_pairs = [
            ("west", "east"),
            ("east", "west"),
            ("north", "south"),
            ("south", "north"),
        ]
        start_edge, end_edge = random.choice(edge_pairs)
        return (
            FlightFactory._sample_boundary_waypoint(area, start_edge),
            FlightFactory._sample_boundary_waypoint(area, end_edge),
        )

    @staticmethod
    def _sample_boundary_waypoint(area: AreaConfig, edge: str, altitude: float = 0.0) -> Waypoint:
        if edge == "west":
            return Waypoint(
                lat=random.uniform(area.min_lat, area.max_lat),
                lon=area.min_lon,
                altitude=altitude,
            )
        if edge == "east":
            return Waypoint(
                lat=random.uniform(area.min_lat, area.max_lat),
                lon=area.max_lon,
                altitude=altitude,
            )
        if edge == "north":
            return Waypoint(
                lat=area.max_lat,
                lon=random.uniform(area.min_lon, area.max_lon),
                altitude=altitude,
            )
        return Waypoint(
            lat=area.min_lat,
            lon=random.uniform(area.min_lon, area.max_lon),
            altitude=altitude,
        )

    @staticmethod
    def _interpolate_waypoint(start: Waypoint, end: Waypoint, fraction: float, altitude: float) -> Waypoint:
        return Waypoint(
            lat=start.lat + (end.lat - start.lat) * fraction,
            lon=start.lon + (end.lon - start.lon) * fraction,
            altitude=altitude,
        )

    @staticmethod
    def _offset_interpolated_waypoint(
        start: Waypoint,
        end: Waypoint,
        fraction: float,
        altitude: float,
        lateral_offset_km: float,
    ) -> Waypoint:
        base = FlightFactory._interpolate_waypoint(start, end, fraction, altitude)
        if lateral_offset_km == 0.0:
            return base

        lat_delta = end.lat - start.lat
        lon_delta = end.lon - start.lon
        norm = (lat_delta ** 2 + lon_delta ** 2) ** 0.5
        if norm == 0:
            return base

        perp_lat = -lon_delta / norm
        perp_lon = lat_delta / norm
        lat_offset_deg = (lateral_offset_km / 111.0) * perp_lat
        lon_scale = max(0.2, abs(math.cos(math.radians(base.lat))))
        lon_offset_deg = (lateral_offset_km / (111.0 * lon_scale)) * perp_lon
        return Waypoint(
            lat=base.lat + lat_offset_deg,
            lon=base.lon + lon_offset_deg,
            altitude=altitude,
        )

    @staticmethod
    def _offset_intensity(idx: int, total: int) -> float:
        if total == 1:
            return 1.0
        center = (total - 1) / 2
        distance_from_center = abs(idx - center)
        max_distance = max(1.0, center)
        return max(0.25, 1.0 - 0.55 * (distance_from_center / max_distance))

    @staticmethod
    def _route_altitude_for_fraction(fraction: float, cruise_altitude_m: float) -> float:
        if fraction <= 0.25:
            return cruise_altitude_m * 0.7
        if fraction >= 0.8:
            return max(500.0, cruise_altitude_m * 0.3)
        return cruise_altitude_m

    @staticmethod
    def _sample_unscheduled_free_lifetime_seconds(
        platform_class: PlatformClass,
        mission_profile: MissionProfile,
    ) -> int:
        if platform_class == PlatformClass.MULTIROTOR_UAV:
            if mission_profile == MissionProfile.LOITER:
                low_minutes, high_minutes = 20, 55
            else:
                low_minutes, high_minutes = 15, 40
        elif platform_class == PlatformClass.FIXED_WING_UAV:
            if mission_profile == MissionProfile.RECON:
                low_minutes, high_minutes = 90, 240
            elif mission_profile == MissionProfile.LOITER:
                low_minutes, high_minutes = 70, 180
            else:
                low_minutes, high_minutes = 60, 150
        elif platform_class == PlatformClass.ROTARY_WING_AIRCRAFT:
            if mission_profile == MissionProfile.PATROL:
                low_minutes, high_minutes = 45, 120
            else:
                low_minutes, high_minutes = 35, 90
        else:
            if mission_profile == MissionProfile.RECON:
                low_minutes, high_minutes = 80, 180
            elif mission_profile == MissionProfile.PATROL:
                low_minutes, high_minutes = 60, 150
            else:
                low_minutes, high_minutes = 50, 120

        return random.randint(low_minutes * 60, high_minutes * 60)

    @staticmethod
    def _sample_airport_pair(area: Optional[AreaConfig]) -> tuple[Airport, Airport] | None:
        airports = AIRPORTS
        if area is not None:
            airports = [
                airport
                for airport in AIRPORTS
                if area.contains(airport.lat, airport.lon)
            ]
        if len(airports) < 2:
            return None

        origin, destination = random.sample(airports, 2)
        return origin, destination

    @staticmethod
    def _generate_callsign(prefix: str) -> str:
        letters = "".join(random.choices(string.ascii_uppercase, k=2))
        number = random.randint(100, 9999)
        return f"{prefix}{letters}{number}"

    @staticmethod
    def _generate_passenger_callsign() -> str:
        airline = random.choice(["B2", "BT", "LO", "LH", "W6", "FR"])
        return f"{airline}{random.randint(100, 9999)}"
