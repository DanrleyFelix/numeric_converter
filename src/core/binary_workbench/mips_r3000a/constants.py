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
    "addi": 0x08,
    "addiu": 0x09,
    "slti": 0x0A,
    "sltiu": 0x0B,
    "andi": 0x0C,
    "ori": 0x0D,
    "xori": 0x0E,
    "lui": 0x0F,
    "lb": 0x20,
    "lh": 0x21,
    "lwl": 0x22,
    "lw": 0x23,
    "lbu": 0x24,
    "lhu": 0x25,
    "lwr": 0x26,
    "sb": 0x28,
    "sh": 0x29,
    "swl": 0x2A,
    "sw": 0x2B,
    "swr": 0x2E,
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
    "sll": 0x00,
    "srl": 0x02,
    "sra": 0x03,
    "sllv": 0x04,
    "srlv": 0x06,
    "srav": 0x07,
    "mfhi": 0x10,
    "mthi": 0x11,
    "mflo": 0x12,
    "mtlo": 0x13,
    "mult": 0x18,
    "multu": 0x19,
    "div": 0x1A,
    "divu": 0x1B,
    "add": 0x20,
    "addu": 0x21,
    "sub": 0x22,
    "subu": 0x23,
    "and": 0x24,
    "or": 0x25,
    "xor": 0x26,
    "nor": 0x27,
    "slt": 0x2A,
    "sltu": 0x2B,
}

R_SHIFT_IMMEDIATE = {"sll", "srl", "sra"}
R_SHIFT_VARIABLE = {"sllv", "srlv", "srav"}
R_MOVE_FROM_HILO = {"mfhi", "mflo"}
R_MOVE_TO_HILO = {"mthi", "mtlo"}
R_MULT_DIV = {"mult", "multu", "div", "divu"}
R_CODE_FUNCTS = {"syscall": 0x0C, "break": 0x0D}

R_JUMP_FUNCTS: dict[str, int] = {
    "jr": 0x08,
    "jalr": 0x09,
}