* virtual_memory_range 0x80000000 0x801DFFFF
* import current_file 0x8000F800
* import slot_
* import data_file deck_entry_bytes.asm 0x801A7E20
* define $sp 0x801FFF00
* define $pc 0x8000F858
* define $gp 0x8009AF08

addiu $a0, $zero, 0x14
JAL    # Test
addiu $a1, $zero, 0x0
nop
nop