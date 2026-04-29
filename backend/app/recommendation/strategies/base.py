# Abstract base class for all recommendation strategies.

from abc import ABC, abstractmethod


class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, user_id: str) -> list[str]:
        ...
