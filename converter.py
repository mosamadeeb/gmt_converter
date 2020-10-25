from typing import List
from copy import deepcopy
from os.path import basename
from pyquaternion import Quaternion

from read import read_file
from write import write_file
from util.dicts import *
from util.binary import BinaryReader
from util.read_cmt import read_cmt_file
from util.write_cmt import write_cmt_file
from util.read_gmd import GMDBone, read_gmd_bones, get_face_bones, find_gmd_bone
from structure.types.format import CurveFormat, curve_array_to_quat
from structure.file import GMTFile
from structure.header import GMTHeader
from structure.animation import Animation
from structure.bone import Bone, find_bone
from structure.curve import *
from structure.graph import *
from structure.name import Name
from structure.version import *


class Translation:
    def __init__(self, rp: bool, fc: bool, hn: bool, bd: bool, sgmd: str, tgmd: str, rst: bool, rhct: bool, aoff: float):
        self.reparent = rp
        self.face = fc
        self.hand = hn
        self.body = bd
        self.sourcegmd = sgmd
        self.targetgmd = tgmd

        self.reset = rst
        self.resethact = rhct
        self.offset = (0, 0, 0)
        self.add_offset = float(aoff) if aoff else 0.0

    def has_operation(self):
        return self.reparent or self.face or self.hand or self.body

    def has_reset(self):
        return self.reset or self.resethact

# returns converted file as bytearray


def convert(path, src_game, dst_game, motion, translation) -> bytearray:
    in_file = read_file(path)
    src_gmt = GMTProperties(GAME[src_game])
    dst_gmt = GMTProperties(GAME[dst_game])

    in_file.header.version = dst_gmt.version

    if src_gmt.version != dst_gmt.version:
        if src_gmt.version == GMTProperties('KENZAN').version:
            # convert 0x2 format quaternions from float to scaled
            for anm in in_file.animations:
                for b in anm.bones:
                    for c in b.curves:
                        if c.curve_format in FLOAT_TO_SCALED:
                            c.curve_format = FLOAT_TO_SCALED[c.curve_format]

        if dst_gmt.version < GMTProperties('YAKUZA_5').version:
            if src_gmt.version >= GMTProperties('YAKUZA_5').version:
                # convert 0x1E format to 0x2
                # not needed cause we'll always change it
                for anm in in_file.animations:
                    for b in anm.bones:
                        for c in b.curves:
                            if c.curve_format == CurveFormat.ROT_QUAT_INT_SCALED:
                                c.curve_format = CurveFormat.ROT_QUAT_SCALED

            if dst_gmt.version == GMTProperties('KENZAN').version:
                # convert 0x2 format quaternions from scaled to float
                for anm in in_file.animations:
                    for b in anm.bones:
                        for c in b.curves:
                            if c.curve_format in SCALED_TO_FLOAT:
                                c.curve_format = SCALED_TO_FLOAT[c.curve_format]

    if dst_gmt.new_bones:
        # rename to new
        for anm in in_file.animations:
            for bone in anm.bones:
                bone.name.update(NEW_BONES.get(
                    bone.name.string(), bone.name.string()))
        if dst_gmt.is_dragon_engine:
            # rename to de
            for anm in in_file.animations:
                for bone in anm.bones:
                    bone.name.update(DE_FACE.get(
                        bone.name.string(), bone.name.string()))
        """
        # add scale bone
        for anm in in_file.animations:
            if not len([b for b in anm.bones if b.name.string() == "scale"]):
                anm.bones = add_scale_bone(anm.bones, anm.graphs)
        """
    else:
        for anm in in_file.animations:
            for bone in anm.bones:
                bone.name.update(OLD_BONES.get(
                    bone.name.string(), bone.name.string()))
                bone.name.update(DE_FACE_OLD.get(
                    bone.name.string(), bone.name.string()))

    if translation.reset:
        for anm in in_file.animations:
            anm.bones = reset_vector(
                anm.bones, src_gmt.new_bones, motion=motion)
    elif translation.resethact:
        for anm in in_file.animations:
            anm.bones = reset_vector(anm.bones, src_gmt.new_bones, is_de=src_gmt.is_dragon_engine,
                                     offset=translation.offset, add_offset=translation.add_offset)

    if src_gmt.new_bones:
        if not dst_gmt.new_bones or (src_gmt.is_dragon_engine and not dst_gmt.is_dragon_engine):
            # convert new bones to old bones (remove _c_n and add vector (and sync) to center)
            for anm in in_file.animations:
                anm.bones = new_to_old_bones(
                    anm.bones, src_gmt.is_dragon_engine, dst_gmt.new_bones, motion, translation.targetgmd)
        elif not src_gmt.is_dragon_engine and dst_gmt.is_dragon_engine:
            # convert post-Y5 bones to DE bones (copy center movement to vector)
            for anm in in_file.animations:
                anm.bones = old_to_new_bones(
                    anm.bones, src_gmt.new_bones, dst_gmt.is_dragon_engine, motion, translation.targetgmd)

    elif dst_gmt.new_bones:
        # convert old bones to new bones (add _c_n and copy center movement to vector (and sync) accordingly)
        for anm in in_file.animations:
            anm.bones = old_to_new_bones(
                anm.bones, src_gmt.new_bones, dst_gmt.is_dragon_engine, motion, translation.targetgmd)

    if dst_gmt.new_bones and not dst_gmt.is_dragon_engine:
        # if not translation.targetgmd:
        #    print("Target GMD path is required for hand pattern fixing")
        #    translation.targetgmd = input("Target GMD path: ")
        for anm in in_file.animations:
            anm.bones = finger_pos(anm.bones, translation.targetgmd)

    if src_gmt.is_dragon_engine:
        if not dst_gmt.is_dragon_engine:
            # convert values in kosi to be direct child of center
            for anm in in_file.animations:
                anm.bones = de_to_old_kosi(anm.bones)
    elif dst_gmt.is_dragon_engine:
        # convert values in kosi to be direct child of ketu
        for anm in in_file.animations:
            anm.bones = old_to_de_kosi(anm.bones)

    if translation.has_operation():
        if not translation.sourcegmd or not translation.targetgmd:
            print(
                "Source and target GMD paths are required for bone translation/reparenting")
            translation.sourcegmd = input("Source GMD path: ")
            translation.targetgmd = input("Target GMD path: ")
        for anm in in_file.animations:
            anm.bones = transform_bones(
                anm.bones, dst_gmt.new_bones, dst_gmt.is_dragon_engine, translation)

    """
    for b in in_file.animations[0].bones:
        if b.name.string() != "center_c_n" and b.name.string() != "vector_c_n":
            print(b.name.string())
            if len(b.position_curves()):
                b.curves.remove(b.position_curves()[0])
    """
    """
    if hand:
        for anm in in_file.animations:
            anm.bones = reset_hand_pos(anm.bones)
    """

    return write_file(in_file, dst_gmt.version)


def old_to_de_kosi(bones: List[Bone]) -> List[Bone]:
    # convert rotations to make kosi child to ketu
    # convert positions: set kosi position to 0
    ketu = [b for b in bones if 'ketu' in b.name.string()]
    kosi = [b for b in bones if 'kosi' in b.name.string()]
    if not (len(ketu) and len(kosi)):
        return bones
    ketu = ketu[0]
    #ketu_index = bones.index(ketu)
    kosi = kosi[0]
    kosi_index = bones.index(kosi)

    positions = []
    for ko in kosi.position_curves():
        ko.values = [[0 for x in value] for value in ko.values]
        positions.append(deepcopy(ko))
    kosi_curves = positions

    rotations = []
    if not len(kosi.rotation_curves()):
        curves = ketu.rotation_curves()
        for c in curves:
            c.values = [[0, 0, 0, 1] for v in c.values]
        kosi.curves.extend(curves)
    for ke, ko in zip(ketu.rotation_curves(), kosi.rotation_curves()):
        i = 0
        ko.neutralize()
        for f in ko.graph.keyframes:
            kf = f
            if kf not in ke.graph.keyframes:
                kf = [k for k in ke.graph.keyframes if k < kf][-1]
            # TODO: if original value was two axes, can we export as 4 axes?
            ke_value = curve_array_to_quat(
                ke.curve_format, ke.values[ke.graph.keyframes.index(kf)])
            ko_value = curve_array_to_quat(ko.curve_format, ko.values[i])
            quat = (ke_value.inverse * ko_value)
            ko.values[i] = [quat.x, quat.y, quat.z, quat.w]
            i += 1
        rotations.append(deepcopy(ko))
    kosi_curves.extend(rotations)
    bones[kosi_index].curves = deepcopy(kosi_curves)
    # append rotation curves to list of curves
    return bones


def de_to_old_kosi(bones: List[Bone]) -> List[Bone]:
    # convert rotations to make kosi and ketu siblings
    # convert positions: set kosi position to ketu position
    ketu = [b for b in bones if 'ketu' in b.name.string()]
    kosi = [b for b in bones if 'kosi' in b.name.string()]
    if not (len(ketu) and len(kosi)):
        return bones
    ketu = ketu[0]
    #ketu_index = bones.index(ketu)
    kosi = kosi[0]
    kosi_index = bones.index(kosi)

    positions = []
    if not len(kosi.position_curves()):
        positions = ketu.position_curves()
    for ke, ko in zip(ketu.position_curves(), kosi.position_curves()):
        i = 0
        for f in ko.graph.keyframes:
            kf = f
            if kf not in ke.graph.keyframes:
                kf = [k for k in ke.graph.keyframes if k < kf][-1]
            ko.values[i] = ke.values[ke.graph.keyframes.index(kf)]
            i += 1
        # TODO: if something break, it's probably because this does check for the curve order
        # order should be (pos, rot) and it assumes that there is only one curve for each
        positions.append(ko)
    kosi_curves = positions

    rotations = []
    if not len(kosi.rotation_curves()):
        curves = ketu.rotation_curves()
        for c in curves:
            c.values = [[0, 0, 0, 1] for v in c.values]
        kosi.curves.extend(curves)
    for ke, ko in zip(ketu.rotation_curves(), kosi.rotation_curves()):
        i = 0
        ko.neutralize()
        for f in ko.graph.keyframes:
            kf = f
            if kf not in ke.graph.keyframes:
                kf = [k for k in ke.graph.keyframes if k < kf][-1]
            # TODO: if original value was two axes, can we export as 4 axes?
            ke_value = curve_array_to_quat(
                ke.curve_format, ke.values[ke.graph.keyframes.index(kf)])
            ko_value = curve_array_to_quat(ko.curve_format, ko.values[i])
            quat = (ke_value * ko_value)
            ko.values[i] = [quat.x, quat.y, quat.z, quat.w]
            i += 1
        rotations.append(ko)
    kosi_curves.extend(rotations)
    bones[kosi_index].curves = kosi_curves

    return bones


def old_to_new_bones(bones: List[Bone], src_new, dst_de, motion, gmd_path) -> List[Bone]:

    c_index = 0
    center_bone = find_bone('center', bones)
    if center_bone[0]:
        center, c_index = center_bone

        vector_bone = find_bone('vector', bones)
        if vector_bone[0]:
            vector, v_index = vector_bone
        else:
            vector = Bone()
            vector.name = Name("vector_c_n")
            v_index = -1

        if dst_de:
            # Use only vector
            if not motion:
                c_pos = center.position_curves()
                if len(c_pos):
                    x, y, z = (0.0, 1.14, 0.0)
                    if gmd_path:
                        gmd = read_gmd_bones(gmd_path)
                        gmd_center, _ = find_gmd_bone('center', gmd)
                        if gmd_center:
                            x, y, z, _ = gmd_center.global_pos
                    c_pos = c_pos[0]
                    c_pos.neutralize()
                    c_pos.values = list(
                        map(lambda p: (p[0] - x, p[1] - y, p[2] - z), c_pos.values))
                    center.curves[0] = c_pos
                    vector.curves = center.curves
                    center.curves = []
            elif not src_new:
                vector.curves = center.curves
                center.curves = [c.to_vertical()
                                 for c in deepcopy(center.position_curves())]

        else:
            # Use both center and vector
            vector.curves = [c.to_horizontal()
                             for c in deepcopy(center.position_curves())]
            vector.curves.extend(deepcopy(center.rotation_curves()))

            if motion:
                center.curves = [c.to_vertical()
                                 for c in deepcopy(center.position_curves())]

        if v_index != -1:
            bones[v_index] = deepcopy(vector)
        else:
            bones.insert(c_index + 1, deepcopy(vector))
        bones[c_index] = deepcopy(center)

    return bones


def finger_pos(bones: List[Bone], gmd_path=None) -> List[Bone]:
    if gmd_path:
        gmd = read_gmd_bones(gmd_path)

    for finger in [b for b in bones if b.name.string() in HAND.values()]:
        index = bones.index(finger)
        if not len(finger.position_curves()):
            if gmd_path:
                gmd_finger = [b for b in gmd if finger.name.string()[
                    :-3] + 'r_n' in b.name]
                if not len(gmd_finger):
                    continue
                gmd_finger = gmd_finger[0]
                x, y, z, _ = gmd_finger.local_pos
            else:
                x, y, z = KIRYU_HAND[b.name.string()]
            pos = new_pos_curve()
            pos.values = [(x, y, z)]
            finger.curves.insert(0, pos)
        bones[index] = deepcopy(finger)

    return bones


# FIXME: This has not been updated. Fixes needed.
def new_to_old_bones(bones: List[Bone], src_de, dst_new, motion, gmd_path) -> List[Bone]:

    center_bone = find_bone('center', bones)
    if center_bone[0]:
        center, index = center_bone

        vector, _ = find_bone('vector', bones)
        if not vector:
            # TODO: Add an actual error here
            return bones

        if src_de:
            center = vector
            center.name.update('center_c_n')
        else:
            pos = [c.to_vertical() for c in center.position_curves()]
            v_pos = vector.position_curves()
            center.curves = [add_curve(c, v) for c, v in zip(pos, v_pos)]
            center.curves.extend(vector.rotation_curves())

        bones[index] = deepcopy(center)
        if not dst_new:
            bones.remove(vector)

    sync, _ = find_bone('sync_c_n', bones)
    if sync:
        bones.remove(sync)

    return bones


def reset_vector(bones: List[Bone], new_bones, is_de=True, motion=False, offset=None, add_offset=0.0):
    if not offset:
        offset = vector_org('', bones)

    names = ['center']
    if new_bones:
        names = ['vector']
        if not is_de:
            names.append('center')

    for name in names:

        # TODO: get actual center height
        height = add_offset
        if not is_de:
            height += 1.14
            if name == 'vector':
                height = offset[1]

        if motion:
            height += offset[1]

        vector = [b for b in bones if name in b.name.string()]
        if not len(vector):
            return bones
        vector = vector[0]
        v_index = bones.index(vector)

        v_pos = vector.position_curves()
        if not len(v_pos):
            return bones
        v_pos = v_pos[0]

        v_pos.neutralize()
        v_pos.values = list(map(lambda v: (
            v[0] - offset[0], v[1] - offset[1] + height, v[2] - offset[2]), v_pos.values))

        bones[v_index] = vector
    return bones


# TODO: change this to be flexible: choose a combination of face, hands, body, or all of them
# this should be called after re-parenting has been done
def translate_face_bones(anm_bones: List[Bone], source, target):
    face_s, jaw_s = get_face_bones(read_gmd_bones(source))
    face_t, jaw_t = get_face_bones(read_gmd_bones(target))

    for s, t in zip((face_s, jaw_s), (face_t, jaw_t)):
        for b_s in s.children:
            b_t = [bone for bone in t.children if bone.name == b_s.name]
            if not len(b_t):
                continue
            b_t = b_t[0]

            gmt_bone = [bone for bone in anm_bones if bone.name.string()
                        == b_s.name]
            if not len(gmt_bone):
                continue
            gmt_bone = gmt_bone[0]
            gmt_index = anm_bones.index(gmt_bone)

            pos_curve = gmt_bone.position_curves()
            if not len(pos_curve):
                continue
            pos_curve = pos_curve[0]

            s_pos = tuple(
                map(lambda x, y: x - y, s.global_pos, b_s.global_pos))
            t_pos = tuple(
                map(lambda x, y: -x + y, t.global_pos, b_t.global_pos))

            pos_curve.values = list(map(lambda f: [
                                    f[0] + s_pos[0] + t_pos[0], f[1] + s_pos[1] + t_pos[1], f[2] + s_pos[2] + t_pos[2]], pos_curve.values))

            gmt_bone.curves[0] = deepcopy(pos_curve)
            anm_bones[gmt_index] = deepcopy(gmt_bone)

    return anm_bones


def transform_bones(anm_bones: List[Bone], new_bones, is_de, translation):
    source_gmd = read_gmd_bones(translation.sourcegmd)
    target_gmd = read_gmd_bones(translation.targetgmd)
    # TODO: now loop over all bones to check for their children
    # if you find a common child (after the gmt rename, be sure to update the names),
    # reparent its positions and rotations like you did with ketu and kosi
    # then accordingly, reparent its children too etc

    def rename_bone(bone):
        if new_bones:
            bone.name = NEW_BONES.get(bone.name, bone.name)
            if is_de:
                bone.name = DE_FACE.get(bone.name, bone.name)
        else:
            bone.name = OLD_BONES.get(bone.name, bone.name)
            if is_de:
                bone.name = DE_FACE_OLD.get(bone.name, bone.name)
        return bone

    source_gmd = list(map(lambda b: rename_bone(b), source_gmd))
    #target_gmd = list(map(lambda b: rename_bone(b), target_gmd))

    if translation.reparent:
        """
        print("source bones:")
        for b in source_gmd:
            print(f"    {b.name}")
        print("target bones:")
        for b in target_gmd:
            print(f"    {b.name}")
        """
        for bone_t in target_gmd:
            bone_s = [b for b in source_gmd if b.name == bone_t.name]
            anm_bone = [b for b in anm_bones if b.name.string() == bone_t.name]

            s_index = -1
            if len(bone_s):
                bone_s = bone_s[0]
                s_index = source_gmd.index(bone_s)
            else:
                bone_s = GMDBone()

            if not len(anm_bone):
                continue
            anm_bone = anm_bone[0]
            gmt_index = anm_bones.index(anm_bone)

            parent_s = bone_s.parent_recursive
            parent_t = bone_t.parent_recursive
            parent_s = parent_s[0] if len(parent_s) else GMDBone()
            parent_t = parent_t[0] if len(parent_t) else GMDBone()

            parent_new = [p for p in source_gmd if p.name == parent_t.name]
            parent_new = parent_new[0] if len(parent_new) else parent_t

            """
            if bone_t.name == '_lip_top_side1_r_n':
                print(f"\nanm_bone.name.string(): {anm_bone.name.string()}")
                print(f"anm_bone.curves[0].values[0]: {anm_bone.curves[0].values[0]}")
                print(f"bone_s.global_pos: {bone_s.global_pos}")
                print(f"bone_t.global_pos: {bone_t.global_pos}\n")
                
                print(f"parent_s.name: {parent_s.name}")
                print(f"parent_s.global_pos: {parent_s.global_pos}")
                print(f"parent_t.name: {parent_t.name}")
                print(f"parent_t.global_pos: {parent_t.global_pos}")
                print(f"parent_new.name: {parent_new.name}")
                print(f"parent_new.global_pos: {parent_new.global_pos}\n")
            """

            if s_index != -1:
                source_gmd[s_index].parent_recursive.insert(0, parent_new)

            # positions
            pos_curve = anm_bone.position_curves()
            if len(pos_curve):
                pos_curve = pos_curve[0]
                pos_curve.neutralize()
                s_pos = tuple(
                    map(lambda x, y: x - y, parent_s.global_pos, bone_s.global_pos))
                s_pos_new = tuple(
                    map(lambda x, y: -x + y, parent_new.global_pos, bone_s.global_pos))

                pos_curve.values = list(map(lambda f:
                                            [f[0] + s_pos[0] + s_pos_new[0],
                                             f[1] + s_pos[1] + s_pos_new[1],
                                                f[2] + s_pos[2] + s_pos_new[2]], pos_curve.values))
                anm_bones[gmt_index].curves[0] = deepcopy(pos_curve)

            """
            #rotations
            rot_curve = anm_bone.rotation_curves()
            if len(rot_curve):
                rot_curve = rot_curve[0]
                
                for p in bone_s.parent_recursive:
                    anm_p = [b for b in anm_bones if b.name == p.name]
            """

    # FIXME: translation doesn't work correctly after reparenting
    # possible fix: source_gmd should get updated with other fixes

    # more correct fix: it should be updated with predicted bone position, not parent_t
    def translate(start: str, stop=[]):
        start_s = [b for b in source_gmd if start in b.name]

        if not len(start_s):
            return

        stop_children = []
        if len(stop):
            for st in stop:
                stop_s = [b for b in source_gmd if st in b.name]
                if len(stop_s):
                    stop_s = stop_s[0]
                    stop_s.get_children_recursive()
                    stop_children.extend(
                        list(map(lambda b: b.name, stop_s.children_recursive)))
                else:
                    stop_s = []

        start_s = start_s[0]
        start_s.get_children_recursive()

        for b_s in start_s.children_recursive:
            if b_s.name in stop_children:
                continue
            b_t = [bone for bone in target_gmd if bone.name == b_s.name]
            if not len(b_t):
                continue
            b_t = b_t[0]

            p_s = b_s.parent_recursive
            p_t = b_t.parent_recursive
            p_s = p_s[0] if len(p_s) else GMDBone()
            p_t = p_t[0] if len(p_t) else GMDBone()

            if find_gmd_bone(p_s.name, b_t.parent_recursive)[0]:
                p_t, _ = find_gmd_bone(p_s.name, b_t.parent_recursive)

            gmt_bone = [bone for bone in anm_bones if bone.name.string()
                        == b_s.name]
            if not len(gmt_bone):
                continue
            gmt_bone = gmt_bone[0]
            gmt_index = anm_bones.index(gmt_bone)

            pos_curve = gmt_bone.position_curves()
            if not len(pos_curve):
                continue
            pos_curve = pos_curve[0]
            pos_curve.neutralize()
            """
            print(f"\ngmt_bone.name.string(): {gmt_bone.name.string()}")
            print(f"gmt_bone.curves[0].values[0]: {gmt_bone.curves[0].values[0]}")
            print(f"b_s.global_pos: {b_s.global_pos}")
            print(f"b_t.global_pos: {b_t.global_pos}\n")
            
            print(f"p_s.name: {p_s.name}")
            print(f"p_s.global_pos: {p_s.global_pos}")
            print(f"p_t.name: {p_t.name}")
            print(f"p_t.global_pos: {p_t.global_pos}")
            """
            s_pos = tuple(
                map(lambda x, y: x - y, p_s.global_pos, b_s.global_pos))
            t_pos = tuple(
                map(lambda x, y: -x + y, p_t.global_pos, b_t.global_pos))

            pos_curve.values = list(map(lambda f:
                                        [f[0] + s_pos[0] + t_pos[0],
                                         f[1] + s_pos[1] + t_pos[1],
                                            f[2] + s_pos[2] + t_pos[2]], pos_curve.values))

            anm_bones[gmt_index].curves[0] = deepcopy(pos_curve)

        if 'face' in start and is_de:
            for side_name in ['_lip_side_r_n', '_lip_side_l_n']:
                side_gmt = Bone()
                side_gmt.name = Name(side_name)
                side_pos = Curve()
                side_pos.curve_format = CurveFormat.POS_VEC3

                # TODO: we're assuming that these bones do exist
                side_t, _ = find_gmd_bone(side_name, target_gmd)
                if not side_t:
                    continue
                #side_t = [bone for bone in target_gmd if bone.name == side_name][0]

                btm_name = '_lip_btm_side1_r_n' if 'r' in side_name else '_lip_btm_side1_l_n'
                btm_gmt, _ = find_bone(btm_name, anm_bones)
                if not btm_gmt:
                    continue
                #[bone for bone in anm_bones if bone.name.string() == btm_name][0]
                btm_t, _ = find_gmd_bone(btm_name, target_gmd)
                #[bone for bone in target_gmd if bone.name == btm_name][0]

                btm_pos = btm_gmt.position_curves()
                if not len(btm_pos):
                    continue
                btm_pos = btm_pos[0]

                side_pos.graph = btm_pos.graph

                side_pos.values = list(map(lambda f:
                                           [f[0] - btm_t.global_pos[0] + side_t.global_pos[0],
                                            f[1] - btm_t.global_pos[1] +
                                            side_t.global_pos[1],
                                               f[2] - btm_t.global_pos[2] + side_t.global_pos[2]], btm_pos.values))

                side_gmt.curves.append(side_pos)
                anm_bones.append(side_gmt)

    if translation.face:
        if new_bones:
            translate('face_c_n')
        else:
            translate('face')

    if translation.hand:
        translate('ude3_r_n')
        translate('ude3_l_n')

    if translation.body:
        if new_bones:
            translate('center_c_n', ['face_c_n', 'ude3_r_n', 'ude3_l_n'])
        else:
            translate('center', ['face', 'ude3_r_n', 'ude3_l_n'])

    return anm_bones


def combine(paths, ext):
    #paths = list(map(lambda x: f"\"{x}\"", paths))

    # TODO: make an indices list
    files = []
    i = 0
    if ext == 'gmt':
        gmt_file = read_file(paths[0])
        for path in paths[1:]:
            gmt_next = read_file(path)
            i += 1
            result = gmt_file.merge(gmt_next)
            if result == -1:
                files.append(
                    (write_file(gmt_file, gmt_file.header.version), i))
                gmt_file = gmt_next
                i = 0
        if result != -1:
            files.append((write_file(gmt_file, gmt_file.header.version), i))

    elif ext == 'cmt':
        files = []
        cmt_file = read_cmt_file(paths[0])
        for path in paths[1:]:
            cmt_next = read_cmt_file(path)
            result = cmt_file.merge(cmt_next)
            if result == -1:
                files.append(
                    (write_cmt_file(cmt_file, cmt_file.header.version), i))
                cmt_file = cmt_next
                i = 0
        if result != -1:
            files.append(
                (write_cmt_file(cmt_file, cmt_file.header.version), i))

    return files


def vector_org(path, bones=None):
    if not bones:
        gmt = read_file(path)
        bones = gmt.animations[0].bones

    vector = [b for b in bones if 'vector' in b.name.string()]
    center = [b for b in bones if 'center' in b.name.string()]
    c = 0.0
    if not len(vector):
        if not len(center):
            return (0, 0, 0)
        vector = center[0]
    else:
        vector = vector[0]
        if len(center):
            center = center[0]
            c_pos = center.position_curves()
            if len(c_pos):
                c_pos = c_pos[0]
                c_pos.neutralize()
                c = c_pos.values[0][1]

    v_pos = vector.position_curves()
    if not len(v_pos):
        return (0, 0, 0)
    v_pos = v_pos[0]

    v_pos.neutralize()
    pos = v_pos.values[0]
    pos = (pos[0], pos[1] + c, pos[2])
    return pos


def reset_camera(path, offset, add_offset, is_de):
    cmt = read_cmt_file(path)
    height = add_offset
    if not is_de:
        height += 1.14
    for anm in cmt.animations:
        for data in anm.anm_data:
            data.foc_x -= offset[0]
            data.foc_y -= offset[1] - height  # TODO: correct?
            data.foc_z -= offset[2]

            data.pos_x -= offset[0]
            data.pos_y -= offset[1] - height
            data.pos_z -= offset[2]

    return write_cmt_file(cmt, cmt.header.version)
