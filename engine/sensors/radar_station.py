# engine/sensors/radar_station.py

import random
import math

import datetime
from typing import List

from engine.sensors.radar_observation import RadarObservation
from domain.air_object import AirObject
from engine.navigation.math import haversine_distance_km

# Предположительно RadarObeservation - главный ивент который будет стримиться. может быть расширен в будущем, например, добавлением типа объекта, скорости и т.д.
# Как минимум, он должен определять по скорости и высоте тип объекта (самолет, вертолет, дрон, птица и т.п.). 
# Это может быть полезно для фильтрации и анализа данных. Но для простоты сейчас оставим только базовые поля. Учитывая "реализм"
# он может быть неопознанным (object_id=None) и с ошибками измерения (lat_error, lon_error, altitude_error).

class RadarStation:
    def __init__(
        self,
        radar_id: str, # Их у нас ограниченное количество, так что можно просто строкой идентифицировать
        lat: float, # Х - Точка где стоит РЛСка
        lon: float, # У - Точка где стоит РЛСка
        range_km: float = 300.0, # Дистанция обнаружения станции (~300-400km)
        detection_probability: float = 0.9, # Вероятность обнаружения
        noise_std: float = 0.01,  # Ошибка по дальности обнаружения ~1km
    ):
        self.radar_id = radar_id
        self.lat = lat
        self.lon = lon
        self.range_km = range_km
        self.detection_probability = detection_probability
        self.noise_std = noise_std

    def scan(
        self,
        objects: List[AirObject],
        timestamp: datetime.datetime,
    ) -> List[RadarObservation]:

        observations: List[RadarObservation] = []

        for obj in objects:
            pos = obj.latest_position()
            if not pos:
                continue

            # 1. Проверка дальности - достает ли до цели
            if not self._in_range(pos.lat, pos.lon):
                continue

            # 2. Вероятность обнаружения (пропуски) - даже если цель в зоне, она может не быть обнаружена из-за помех, погодных условий и т.п.
            if random.random() > self.detection_probability:
                continue

            # 3. Генерация наблюдения с шумом - добавляем случайные ошибки к реальной позиции для имитации неточности измерений РЛС.
            obs = self._make_observation(obj, pos, timestamp)
            observations.append(obs)

        return observations

    def _in_range(self, lat: float, lon: float) -> bool:
        distance = haversine_distance_km(
            self.lat,
            self.lon,
            lat,
            lon,
        )
        return distance <= self.range_km

    def _make_observation(self, obj, pos, timestamp) -> RadarObservation:
        # добавляем шум. Для простоты используем гауссовский шум, но можно экспериментировать с другими моделями ошибок.
        lat_noise = random.gauss(0, self.noise_std)
        lon_noise = random.gauss(0, self.noise_std)
        alt_noise = random.gauss(0, self.noise_std * 1000)

        return RadarObservation(
            radar_id=self.radar_id,
            object_id=obj.object_id,
            timestamp=timestamp,
            lat=pos.lat + lat_noise,
            lon=pos.lon + lon_noise,
            altitude=pos.altitude + alt_noise,
            lat_error=lat_noise,
            lon_error=lon_noise,
            altitude_error=alt_noise,
        )