from typing import List, Any

from .graph import *
from .types.format import CurveFormat


class Curve:
    def __init__(self):
        self.values = []
    
    curve_format: CurveFormat
    values: List[Any]
    
    graph: Graph
    anm_data_offset: int
    property_fmt: int
    format: int
    
    def __horizontal_pos(self):
        if self.curve_format == CurveFormat.POS_VEC3:
            return [[x[0], 0.0, x[2]] for x in self.values]
        elif self.curve_format == CurveFormat.POS_Y:
            return [[0.0] for x in self.values]
        else:
            return self.values
    
    def __vertical_pos(self):
        if self.curve_format == CurveFormat.POS_VEC3:
            return [[0.0, x[1], 0.0] for x in self.values]
        elif self.curve_format in [CurveFormat.POS_X, CurveFormat.POS_Z]:
            return [[0.0] for x in self.values]
        else:
            return self.values
    
    def __neutralize_pos(self):
        if not self.curve_format == CurveFormat.POS_VEC3:
            if 'X' in self.curve_format.name:
                self.values = [[v[0], 0.0, 0.0] for v in self.values]
            elif 'Y' in self.curve_format.name:
                self.values = [[0.0, v[0], 0.0] for v in self.values]
            elif 'Z' in self.curve_format.name:
                self.values = [[0.0, 0.0, v[0]] for v in self.values]
            self.curve_format = CurveFormat.POS_VEC3
    
    def __neutralize_rot(self):
        if not 'QUAT' in self.curve_format.name:
            if 'X' in self.curve_format.name:
                self.values = [[v[0], 0.0, 0.0, v[1]] for v in self.values]
            elif 'Y' in self.curve_format.name:
                self.values = [[0.0, v[0], 0.0, v[1]] for v in self.values]
            elif 'Z' in self.curve_format.name:
                self.values = [[0.0, 0.0, v[0], v[1]] for v in self.values]
        self.curve_format = CurveFormat.ROT_QUAT_SCALED if self.curve_format.value[2] == 2 else CurveFormat.ROT_QUAT_HALF_FLOAT
    
    def neutralize(self):
        if 'POS' in self.curve_format.name:
            self.__neutralize_pos()
        elif 'ROT' in self.curve_format.name:
            self.__neutralize_rot()
    
    def add_pos(self, pos):
        if not self.curve_format == CurveFormat.POS_VEC3:
            if 'X' in self.curve_format.name:
                self.values = [[v[0], 0.0, 0.0] for v in self.values]
            elif 'Y' in self.curve_format.name:
                self.values = [[0.0, v[0], 0.0] for v in self.values]
            elif 'Z' in self.curve_format.name:
                self.values = [[0.0, 0.0, v[0]] for v in self.values]
            self.curve_format = CurveFormat.POS_VEC3
        if not pos.curve_format == CurveFormat.POS_VEC3:
            if 'X' in pos.curve_format.name:
                pos.values = [[v[0], 0.0, 0.0] for v in pos.values]
            elif 'Y' in pos.curve_format.name:
                pos.values = [[0.0, v[0], 0.0] for v in pos.values]
            elif 'Z' in pos.curve_format.name:
                pos.values = [[0.0, 0.0, v[0]] for v in pos.values]
            pos.curve_format = CurveFormat.POS_VEC3
        # TODO: should use map() with lambda instead
        return [[v[0] + a[0], v[1] + a[1], v[2] + a[2]] for v, a in zip(self.values, pos.values)]
    
    def to_horizontal(self):
        new_curve = self
        new_curve.values = self.__horizontal_pos()
        return new_curve

    def to_vertical(self):
        new_curve = self
        new_curve.values = self.__vertical_pos()
        return new_curve
    
def add_curve(curve1, curve2):
    new_values = []
    if len(curve1.values) > len(curve2.values):
        for f in curve1.graph.keyframes:
            kf = f
            if kf not in curve2.graph.keyframes:
                kf = [k for k in curve2.graph.keyframes if k < kf][-1]
            new_values.append(curve2.values[curve2.graph.keyframes.index(kf)])
        curve2.values = new_values
    else:
        for f in curve2.graph.keyframes:
            kf = f
            if kf not in curve1.graph.keyframes:
                kf = [k for k in curve1.graph.keyframes if k < kf][-1]
            new_values.append(curve1.values[curve1.graph.keyframes.index(kf)])
        curve1.values = new_values
        curve1.graph = curve2.graph
    curve1.values = curve1.add_pos(curve2)
    return curve1

def new_pos_curve():
    pos = Curve()
    pos.graph = zero_graph()
    pos.curve_format = CurveFormat.POS_VEC3
    pos.values = [(0, 0, 0)]
    return pos
    
def new_rot_curve():
    rot = Curve()
    rot.graph = zero_graph()
    rot.curve_format = CurveFormat.ROT_QUAT_SCALED
    rot.values = [(0, 0, 0, 1)]
    return rot