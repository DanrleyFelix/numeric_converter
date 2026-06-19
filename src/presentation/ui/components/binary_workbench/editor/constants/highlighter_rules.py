PSX_MIPS_BRANCH_MNEMONICS = ["beq", "bne", "bgtz", "blez", "bltz", "bgez", "beqz", "bnez"]
PSX_MIPS_JUMP_MNEMONICS = ["j", "jal", "jr", "jalr"]
PSX_MIPS_DELAY_SLOT_LOAD_MNEMONICS = ["lb", "lbu", "lh", "lhu", "lw", "lwl", "lwr"]
PSX_MIPS_HI_LO_TRANSFER_MNEMONICS = ["mfhi", "mflo", "mfho", "mthi", "mtlo"]
PSX_MIPS_SPECIAL_INSTRUCTION_MNEMONICS = ["break", "syscall", "byte", "half", "word", "nop", "li"]
PSX_MIPS_OTHER_INSTRUCTION_MNEMONICS = ["add", "addi", "addiu", "addu", "and", "andi", "div", "divu", "lui", "mult", "multu", "nor", "or", "ori", "sb", "sh", "sll", "sllv", "slt", "slti", "sltiu", "sra", "srav", "srl", "srlv", "sub", "subu", "sw", "swl", "swr", "xor", "xori, li"]
PSX_MIPS_ARGUMENT_VALUE_REGISTERS = ["a0", "a1", "a2", "a3", "v0", "v1"]
PSX_MIPS_TEMPORARY_SAVED_VALUE_REGISTERS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9",
]
PSX_MIPS_POINTER_REGISTERS = ["at", "gp", "sp", "fp"]
PSX_MIPS_SPECIAL_REGISTERS = ["zero", "ra", "k0", "k1", "hi", "lo"]

PSX_MIPS_KNOWN_MNEMONICS = {
    *PSX_MIPS_BRANCH_MNEMONICS,
    *PSX_MIPS_DELAY_SLOT_LOAD_MNEMONICS,
    *PSX_MIPS_HI_LO_TRANSFER_MNEMONICS,
    *PSX_MIPS_JUMP_MNEMONICS,
    *PSX_MIPS_OTHER_INSTRUCTION_MNEMONICS,
    *PSX_MIPS_SPECIAL_INSTRUCTION_MNEMONICS,
}


PSX_MIPS_HIGHLIGHTER = {
    "mnemonic": [
        [PSX_MIPS_BRANCH_MNEMONICS, "#FF7A59"],
        [PSX_MIPS_JUMP_MNEMONICS, "#FF7A59"],
        [PSX_MIPS_DELAY_SLOT_LOAD_MNEMONICS, "#FF6F91"],
        [PSX_MIPS_HI_LO_TRANSFER_MNEMONICS, "#F4A261"],
        [PSX_MIPS_OTHER_INSTRUCTION_MNEMONICS, "#A0DC45"],
        [PSX_MIPS_SPECIAL_INSTRUCTION_MNEMONICS, "#D5CBDE"],

    ],
    "registers": [
        [PSX_MIPS_ARGUMENT_VALUE_REGISTERS, "#D4AF37"],
        [PSX_MIPS_TEMPORARY_SAVED_VALUE_REGISTERS, "#41C1EC"],
        [PSX_MIPS_POINTER_REGISTERS, "#AF57DF"],
        [PSX_MIPS_SPECIAL_REGISTERS, "#8FA6FF"],
    ],
    "hex": "#62C6A1",
    "label": "#FFD166",
    "equate": "#FF4FD8",
    "variable": "#FF4FD8",
    "command": "#4F6DFF",
    "invalid_instruction": "#CD1C1C",
    "comment": "#7F879B",
}
