import abc
from abc import abstractmethod

from graphics import GraphicsContext


class Entity(abc.ABC):
    @abstractmethod
    def render(self, graphics: GraphicsContext):
        raise NotImplementedError()
