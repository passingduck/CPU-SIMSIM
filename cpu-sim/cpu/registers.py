from dataclasses import dataclass, field
from typing import List

GENERAL_REGS = 16         # R0–R15
SPECIAL_REGS = ["PC", "IR", "CPSR", "LR"]  # LR=return reg


@dataclass
class Registers:
    gpr: List[int] = field(default_factory=lambda: [0]*GENERAL_REGS)
    pc: int = 0
    ir: int = 0
    cpsr: int = 0
    lr: int = 0

    def __getitem__(self, idx: int) -> int:
        if 0 <= idx < GENERAL_REGS:
            return self.gpr[idx]
        raise IndexError("Invalid register index")

    def __setitem__(self, idx: int, value: int) -> None:
        if 0 <= idx < GENERAL_REGS:
            self.gpr[idx] = value & 0xFFFFFFFF
        else:
            raise IndexError("Invalid register index")
