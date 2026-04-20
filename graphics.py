import numpy as np
import pygame
from numpy._typing import ArrayLike
from pygame import Surface, Rect


class GraphicsContext:
    """
    Wrapper around pygame's surface drawing function, supporting translating globally.
    """

    surface: pygame.Surface
    offset: np.ndarray
    scale: float

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.offset = np.asarray([0.0, 0.0])
        self.scale = 1.0

        self.font = pygame.font.Font("font.ttf", 22)

    def transform(self, offset: ArrayLike, scale: float):
        before_offset = self.offset.copy()
        before_scale = self.scale
        class TransformContext:
            def __init__(self, graphics_context: GraphicsContext, offset: ArrayLike, scale: float):
                self.graphics_context = graphics_context
                self.offset = np.asarray(offset)
                self.scale = scale

            def __enter__(self):
                self.graphics_context.offset += self.offset
                self.graphics_context.scale *= self.scale

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.graphics_context.offset = before_offset
                self.graphics_context.scale = before_scale

        return TransformContext(self, offset=offset, scale=scale)

    def translate(self, offset: ArrayLike):
        return self.transform(offset=offset * self.scale, scale=1.0)

    def scale_by(self, scale: float):
        return self.transform(offset=[0.0, 0.0], scale=scale)

    def blit(self, source: Surface, dest: ArrayLike | Rect | None = None, smooth_scale: bool = True):
        if self.scale != 1.0:
            if smooth_scale:
                source = pygame.transform.smoothscale_by(source, self.scale)
            else:
                source = pygame.transform.scale_by(source, self.scale)

        if isinstance(dest, Rect):
            self.surface.blit(source, dest.move(*self.offset))
        elif dest is not None:
            self.surface.blit(source, self.scale * dest + self.offset)
        else:
            self.surface.blit(source, self.offset)

    def draw_aaline(self, color, start_pos, end_pos):
        pygame.draw.aaline(
            self.surface, color=color,
            start_pos=self.scale * start_pos + self.offset, end_pos=self.scale * end_pos + self.offset,
        )

    def draw_aalines(self, color, closed: bool, points: ArrayLike):
        points = np.asarray(points)
        pygame.draw.aalines(
            self.surface, color=color, closed=closed,
            points=self.scale * points + self.offset,
        )

    def draw_circle(self, color, center: ArrayLike, radius: float, width: int = 0):
        center = np.asarray(center)
        pygame.draw.circle(
            self.surface, color=color,
            center=self.scale * center + self.offset, radius=self.scale * radius, width=width,
        )

    def draw_line(self, color, start_pos: ArrayLike, end_pos: ArrayLike, width: float):
        start_pos = np.asarray(start_pos)
        end_pos = np.asarray(end_pos)
        pygame.draw.line(
            self.surface, color=color,
            start_pos=self.scale * start_pos + self.offset, end_pos=self.scale * end_pos + self.offset,
            width=max(round(self.scale * width), 1),
        )

    def draw_polygon(self, color, points: ArrayLike):
        pygame.draw.polygon(
            self.surface, color=color, points=np.asarray(points) * self.scale + self.offset[None, :]
        )
