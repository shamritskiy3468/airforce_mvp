from abc import ABC, abstractmethod
from domain.air_object import AirObject


class NavigationPolicy(ABC):
    @abstractmethod
    def move(self, obj: AirObject, dt_seconds: int, current_time):
        """
        Обновляет положение объекта на один тик
        """
        pass