from typing import List
from os.path import basename

from .binary import BinaryReader
from .read_cmt import *


def write_animations(cmt: CMTFile):
    buf = BinaryReader(bytearray())
    i = 1
    prev_count = 0
    for anm in cmt.animations:
        buf.write_float(anm.frame_rate)
        buf.write_uint32(anm.frame_count)
        buf.write_uint32(0x20 + (i * 0x10) + (prev_count * 0x20))
        buf.write_uint32(anm.format)
        prev_count = anm.frame_count
        i += 1
    return buf.buffer()

def write_anm_data(cmt: CMTFile):
    buf = BinaryReader(bytearray())
    for anm in cmt.animations:
        for data in anm.anm_data:
            buf.write_float(data.pos_x)
            buf.write_float(data.pos_y)
            buf.write_float(data.pos_z)
            buf.write_float(data.fov)
            
            buf.write_float(data.foc_x)
            buf.write_float(data.foc_y)
            buf.write_float(data.foc_z)
            buf.write_float(data.rot)
    return buf.buffer()

def write_cmt_file(cmt: CMTFile, version: int) -> CMTFile:
    file = BinaryReader(bytearray())
    
    anm_data = write_anm_data(cmt)
    
    animations = write_animations(cmt)
    
    # write header
    file.write_str("CMTP", length=4)
    file.write_int8(-1)
    file.write_uint8(1)
    file.write_uint16(0)
    file.write_uint32(version)
    # file_size
    file.write_uint32(0)
    
    file.write_uint32(cmt.header.anm_count)
    file.write_uint32(cmt.header.unk1)
    file.write_uint32(cmt.header.unk2)
    file.write_uint32(cmt.header.unk3)
    
    file.extend(animations)
    
    file.extend(anm_data)
    
    file.seek(0, from_end=True)
    file_size = file.pos()
    file.seek(0xC)
    file.write_uint32(file_size)
    
    return file.buffer()
