import math

import numpy as np


def rotate2d(x: np.ndarray, angle: float) -> np.ndarray:
    rot_mat = np.asarray([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return rot_mat @ x

def rotate_90deg(x: np.ndarray) -> np.ndarray:
    return np.asarray([-x[1], x[0]])

