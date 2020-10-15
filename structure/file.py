from typing import List

from .header import GMTHeader
from .name import Name
from .animation import Animation
from .bone import Bone
from .curve import Curve
from .graph import Graph


class GMTFile:
    def __init__(self):
        pass
 
    header: GMTHeader
    names: List[Name]
    
    animations: List[Animation]
    bones: List[Bone]
    graphs: List[Graph]
    curves: List[Curve]
    
    def __update_animations(self):
        for a in self.animations:
            a.bone_map_count = len(a.bones)
            
            a.curves = []
            for b in a.bones:
                a.curves.extend(b.curves)
            a.curve_count = len(a.curves)
            
            a.graphs = []
            for c in a.curves:
                if c.graph.keyframes not in [g.keyframes for g in a.graphs]:
                    a.graphs.append(c.graph)
            a.graph_count = len(a.graphs)
            
            frame_count = 0
            for g in a.graphs:
                frame_count = max(frame_count, len(g.keyframes))
            a.frame_count = frame_count
    
    def __update_bones(self):
        self.bones = []
        for a in self.animations:
            self.bones.extend(a.bones)
    
    def __update_curves(self):
        self.curves = []
        for b in self.bones:
            self.curves.extend(b.curves)
    
    def __update_graphs(self):
        self.graphs = []
        for c in self.curves:
            if c.graph.keyframes not in [g.keyframes for g in self.graphs]:
                self.graphs.append(c.graph)
    
    def __update_names(self):
        self.names = [a.name for a in self.animations]
        for a in self.animations:
            self.names.extend([b.name for b in a.bones])
    
    def __update_header(self):
        self.header.anm_count = len(self.animations)
        self.header.bone_map_count = len(self.bones)
        self.header.name_count = len(self.names)
        self.header.curve_count = len(self.curves)
        self.header.graph_count = len(self.graphs)
    
    def update(self):
        self.__update_animations()
        self.__update_bones()
        self.__update_curves()
        self.__update_graphs()
        self.__update_names()
        self.__update_header()
    
    def merge(self, other):
        anm_s = self.animations[0]
        anm_o = other.animations[0]
        bones = []
        
        if anm_s.longest_graph().keyframes[-1] + anm_o.longest_graph().keyframes[-1] > 65_535:
            return -1
        
        for b_s, b_o in zip(anm_s.bones, anm_o.bones):
            curves = []
            for c_s, c_o in zip(b_s.curves, b_o.curves):
                c_s.neutralize()
                c_o.neutralize()
                o_frames = list(map(lambda x: x + c_s.graph.keyframes[-1] + 1, c_o.graph.keyframes))
                c_s.values.extend(c_o.values)
                c_s.graph.keyframes.extend(o_frames)
                curves.append(c_s)
            b_s.curves = curves
            bones.append(b_s)
        self.animations[0].bones = bones
        self.update()
        return 0
