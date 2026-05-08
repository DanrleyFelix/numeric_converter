from __future__ import annotations

REGISTERS: dict[str, int] = {
    "zero": 0,
    "at": 1,
    "v0": 2,
    "v1": 3,
    "a0": 4,
    "a1": 5,
    "a2": 6,
    "a3": 7,
    "t0": 8,
    "t1": 9,
    "t2": 10,
    "t3": 11,
    "t4": 12,
    "t5": 13,
    "t6": 14,
    "t7": 15,
    "s0": 16,
    "s1": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "t8": 24,
    "t9": 25,
    "k0": 26,
    "k1": 27,
    "gp": 28,
    "sp": 29,
    "fp": 30,
    "s8": 30,
    "ra": 31,
}
REGISTER_NAMES: dict[int, str] = {
    value: name
    for name, value in REGISTERS.items()
    if name != "s8"
}
I_OPCODES: dict[str, int] = {
    "addiu": 0x09,
    "ori": 0x0D,
    "lui": 0x0F,
    "lw": 0x23,
    "sw": 0x2B,
    "lh": 0x21,
    "lhu": 0x25,
    "sh": 0x29,
    "lb": 0x20,
    "lbu": 0x24,
    "sb": 0x28,
    "sltiu": 0x0B,
}
BRANCH_OPCODES: dict[str, int] = {
    "beq": 0x04,
    "bne": 0x05,
    "blez": 0x06,
    "bgtz": 0x07,
}
SPECIAL_BRANCH_RT: dict[str, int] = {
    "bltz": 0x00,
    "bgez": 0x01,
}
J_OPCODES: dict[str, int] = {
    "j": 0x02,
    "jal": 0x03,
}
R_FUNCTS: dict[str, int] = {
    "add": 0x20,
    "addu": 0x21,
    "subu": 0x23,
}
