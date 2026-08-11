* virtual_memory_range 0x80000000 0x801DFFFF
* import current_file 0x80000000
* define $sp 0x801FFF00
* define $pc 0x80000020
* define $gp 0x8009AF08 
; @slot_base_hi = 0x801A
; @slot_base_lo = 0x7AD8
; a0 = slot global 0x00..0x1D
; v0 = Slot*
slot_to_ptr:
SLL $t0, $a0, 5
SLL $t1, $a0, 2
SUBU $t0, $t0, $t1
LUI $v0, @slot_base_hi
ORI $v0, $v0, @slot_base_lo
JR $ra
ADDU $v0, $v0, $t0
nop
test: 
ADDIU $a0, $zero, 0x0
JAL 0xF800
