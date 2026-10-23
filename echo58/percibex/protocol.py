"""Control interpretation of existing WSP16 on the existing sensor socket."""
import struct

SCHOOL, FREEZE, TICK, RECEIPT, ACK, ACTION = range(1, 7)
INSPECT = 1
LAYOUT = struct.Struct('<BBBBbbbbbbBBBBBB')


def packet(op, seq, value=0):
    if type(op) is not int or op not in range(1, 7): raise ValueError('opcode')
    if type(seq) is not int or not 1 <= seq <= 255: raise ValueError('sequence')
    if type(value) is not int or value not in (0, 1): raise ValueError('value')
    return LAYOUT.pack(2, 14, 31, 8, 0, 0, 0, 0, 0, 0, 0, 7, 5, op, value, seq)


def unpack(raw):
    if type(raw) is not bytes or len(raw) != 16: raise ValueError('WSP16 required')
    v = LAYOUT.unpack(raw)
    if raw != packet(v[13], v[15], v[14]): raise ValueError('control envelope')
    return v[13], v[15], v[14]


def family_key(family):
    """64 injective IDs/signatures; bit4 is zero, avoiding MEMX auto masks."""
    if type(family) is not int or not 0 <= family < 64: raise ValueError('family')
    return family+1, (family & 15) | ((family & 48) << 1)
