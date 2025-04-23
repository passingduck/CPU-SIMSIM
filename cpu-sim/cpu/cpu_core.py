from .registers import Registers
from .alu import ALU
from .memory import Memory

class CPU:
    def __init__(self):
        self.reg = Registers()
        self.mem = Memory()
        self.running = False

    def fetch(self):
        self.reg.ir = self.mem.read(self.reg.pc)
        self.reg.pc = (self.reg.pc + 1) & 0xFF

    def decode_execute(self):
        instr = self.reg.ir
        op = (instr & 0xF0) >> 4      # 상위 4비트: opcode
        rd = (instr & 0x0C) >> 2      # 2bit
        rs = instr & 0x03             # 2bit
        mapping = {0x0: "AND", 0x1: "OR", 0x2: "ADD",
                   0x3: "MUL", 0x4: "DIV"}
        if op not in mapping:
            raise RuntimeError(f"Invalid opcode {op:02X}")
        result = ALU.execute(mapping[op], self.reg[rd], self.reg[rs])
        self.reg[rd] = result

    def step(self):
        self.fetch()
        self.decode_execute()

    def reset(self):
        self.__init__()
