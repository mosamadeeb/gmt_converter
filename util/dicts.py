from structure.types.format import CurveFormat

FLOAT_TO_SCALED = {
    CurveFormat.ROT_QUAT_HALF_FLOAT: CurveFormat.ROT_QUAT_SCALED,
    CurveFormat.ROT_XW_HALF_FLOAT: CurveFormat.ROT_XW_SCALED,
    CurveFormat.ROT_YW_HALF_FLOAT: CurveFormat.ROT_YW_SCALED,
    CurveFormat.ROT_ZW_HALF_FLOAT: CurveFormat.ROT_ZW_SCALED,
}

SCALED_TO_FLOAT = dict(map(reversed, FLOAT_TO_SCALED.items()))

def new_face(name, name_new, types):
    new = {}
    for t in types:
        new[f'_{name}_{t}'] = f'_{name_new}_{t}_n'
    return new

NEW_BONES = {
    'pattern_n': 'pattern_c_n',
    'center_n': 'center_c_n',
    'ketu_n': 'ketu_c_n',
    'kosi_n': 'kosi_c_n',
    'mune_n': 'mune_c_n',
    'kubi_n': 'kubi_c_n',
    'face': 'face_c_n',
    #'ude1_r2_n': 'kata_pad_r_sup',
    #'ude1_l2_n': 'kata_pad_l_sup',
    #'ude1_r2_n': 'waki_r_sup', # TODO: this isn't correct. they're in the same place but their functions are different
    # actual ude1_r2_n should be kata_pad_r_sup, but they are in different places
    #'ude1_l2_n': 'waki_l_sup',
    'ude3_r2_n': 'ude2_twist_r_sup',
    'ude3_l2_n': 'ude2_twist_l_sup',
    'buki_r_n': 'buki1_r_n',
    'buki_l_n': 'buki1_l_n'
}

HAND = {
    'kou_r': 'kou_r_n',
    'kou_l': 'kou_l_n'
}

for b in ['naka', 'hito', 'oya', 'koyu', 'kusu']:
    for i in range(1,4):
        for d in ['r', 'l']:
            HAND[f'{b}{i}_{d}'] = f'{b}{i}_{d}_n'

FACE = {
    '_brow': '_brow_c_n',
    '_eyebrow_r2': '_eyebrow2_r_n',
    '_eyebrow_l2': '_eyebrow2_l_n',
    '_jaw': '_jaw_c_n',
    '_chin': '_chin_c_n',
    '_throat': '_throat_c_n'
}

# TODO: add the rest of the bones, even though they may look bad because they're not in the same place
FACE.update(new_face('eyebrow', 'eyebrow', ['r', 'l']))
FACE.update(new_face('temple', 'eyebrow3', ['r', 'l']))
FACE.update(new_face('eyelid', 'eyelid', ['r', 'l']))
FACE.update(new_face('eyelid_und', 'eyelid_und', ['r', 'l']))
FACE.update(new_face('eye', 'eye', ['r', 'l']))
FACE.update(new_face('nose_side', 'cheek1', ['r', 'l']))
FACE.update(new_face('cheek', 'cheek3', ['r', 'l']))
FACE.update(new_face('cheek2', 'cheek2', ['r', 'l']))
FACE.update(new_face('puff', 'cheek_btm1', ['r', 'l']))
#FACE.update(new_face('nose_top', 'nose_top', ['c'])) # TODO: should probably remove this
FACE.update(new_face('nostril', 'nose_side', ['r', 'l']))
FACE.update(new_face('lip_top', 'lip_top', ['r', 'l', 'c']))
FACE.update(new_face('lip_top_side', 'lip_side', ['r', 'l']))
FACE.update(new_face('lip_btm', 'lip_btm', ['r', 'l', 'c']))
FACE.update(new_face('lip_btm_side', 'lip_side2', ['r', 'l']))

DE_FACE = {
    '_lip_top_c_n': '_lip_top1_c_n',
    '_lip_top_r_n': '_lip_top1_r_n',
    '_lip_top_l_n': '_lip_top1_l_n',
    '_lip_side_r_n': '_lip_top_side1_r_n',
    '_lip_side_l_n': '_lip_top_side1_l_n',
    '_lip_btm_c_n': '_lip_btm1_c_n',
    '_lip_btm_r_n': '_lip_btm1_r_n',
    '_lip_btm_l_n': '_lip_btm1_l_n',
    '_lip_side2_r_n': '_lip_btm_side1_r_n',
    '_lip_side2_l_n': '_lip_btm_side1_l_n'
}

NEW_BONES.update(HAND)
NEW_BONES.update(FACE)

OLD_BONES = dict(map(reversed, NEW_BONES.items()))
DE_FACE_OLD = dict(map(reversed, DE_FACE.items()))

"""
PATTERN = [
    CurveFormat.PAT1_LEFT_HAND,
    CurveFormat.PAT1_RIGHT_HAND,
    CurveFormat.PAT1_UNK2,
    CurveFormat.PAT1_UNK3,
    CurveFormat.PAT2
]
"""

KIRYU_HAND = {
    'kou_l_n': (0.014080047607421875, 0.008924007415771484, -0.014490000903606415),
    'koyu1_l_n': (0.08051425218582153, 0.006762027740478516, -0.01835399866104126),
    'koyu2_l_n': (0.03976333141326904, -0.004830002784729004, 0.0),
    'koyu3_l_n': (0.017862439155578613, 0.0, 0.0),
    'kusu1_l_n': (0.08727425336837769, 0.015456080436706543, 0.002898000180721283),
    'kusu2_l_n': (0.048453330993652344, -0.0019320249557495117, 0.0),
    'kusu3_l_n': (0.023639976978302002, 0.0, 0.0),
    'naka1_l_n': (0.10585004091262817, 0.033074021339416504, 0.013524003326892853),
    'naka2_l_n': (0.053464293479919434, -0.004830002784729004, 0.0),
    'naka3_l_n': (0.029133319854736328, 0.0, 0.0),
    'hito1_l_n': (0.10199004411697388, 0.0282440185546875, 0.0396059975028038),
    'hito2_l_n': (0.045734286308288574, 0.0, 0.0),
    'hito3_l_n': (0.026233315467834473, 0.0, 0.0),
    'oya1_l_n': (0.009250044822692871, -0.004599928855895996, 0.031877998262643814),
    'oya2_l_n': (0.07181420922279358, 0.0, 0.00000004377216100692749),
    'oya3_l_n': (0.034933388233184814, 0.0, -0.00000009778887033462524)
}
KIRYU_HAND_R = dict()
for l in KIRYU_HAND:
    right = l[:-3] + 'r_n'
    KIRYU_HAND_R[right] = KIRYU_HAND[l][0] * -1, KIRYU_HAND[l][1], KIRYU_HAND[l][2]
KIRYU_HAND.update(KIRYU_HAND_R)
