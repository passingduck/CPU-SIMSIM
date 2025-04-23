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
        op = (instr & 0xF000) >> 12    # 상위 4비트: opcode (bits 15-12)
        rd = (instr & 0x0F00) >> 8     # 4bit destination register (bits 11-8)
        rs1 = (instr & 0x00F0) >> 4    # 4bit source register 1 (bits 7-4)
        rs2 = instr & 0x000F           # 4bit source register 2 or immediate (bits 3-0)
        
        # ALU operations (0x0-0x4)
        alu_mapping = {0x0: "AND", 0x1: "OR", 0x2: "ADD",
                       0x3: "MUL", 0x4: "DIV"}
        
        # Memory and immediate operations
        # 0x5: Load immediate (LDI) - Load constant into register
        # 0x6: Load from memory (LDM) - Load from memory address in rs1 to rd
        # 0x7: Store to memory (STM) - Store rd to memory address in rs1
        # 0x8: Move to PC (MV) - Move value in rd to PC
        # 0x9: Compare with zero (CMP) - Compare rd with 0, set Z flag if equal
        # 0xA: Jump if zero (JZ) - Jump to address in rd if Z flag is set
        
        if op in alu_mapping:
            # ALU operation
            result = ALU.execute(alu_mapping[op], self.reg[rd], self.reg[rs1])
            self.reg[rd] = result
        elif op == 0x5:
            # Load immediate (LDI)
            # Format: 0x5 | rd | rs1 | immediate (4 bits)
            # For larger immediates, use rs1 as high 4 bits and rs2 as low 4 bits
            immediate = (rs1 << 4) | rs2  # Combine rs1 and rs2 for 8-bit immediate
            
            # If immediate is 0, use the next word in memory as the full immediate
            if immediate == 0:
                # Fetch the next word for the full immediate value
                next_addr = (self.reg.pc) & 0xFF
                immediate = self.mem.read(next_addr)
                # Increment PC to skip the immediate value word
                self.reg.pc = (self.reg.pc + 1) & 0xFF
            
            self.reg[rd] = immediate
        elif op == 0x6:
            # Load from memory (LDM)
            # Format: 0x6 | rd | rs1 | rs2
            # Load from memory address in rs1 to rd
            addr = self.reg[rs1]
            self.reg[rd] = self.mem.read(addr & 0xFF)
        elif op == 0x7:
            # Store to memory (STM)
            # Format: 0x7 | rd | rs1 | rs2
            # Store rd to memory address in rs1
            addr = self.reg[rs1]
            self.mem.write(addr & 0xFF, self.reg[rd])
        elif op == 0x8:
            # Move to PC (MV)
            # Format: 0x8 | rd | rs1 | rs2
            # Move value in rd to PC
            self.reg.pc = self.reg[rd] & 0xFF
        elif op == 0x9:
            # Compare with zero (CMP)
            # Format: 0x9 | rd | rs1 | rs2
            # Compare rd with 0, set Z flag if equal
            if self.reg[rd] == 0:
                # Set Z flag (bit 0) to 1
                self.reg.cpsr |= 0x1
            else:
                # Clear Z flag (bit 0) to 0
                self.reg.cpsr &= ~0x1
        elif op == 0xA:
            # Jump if zero (JZ)
            # Format: 0xA | rd | rs1 | rs2
            # Jump to address in rd if Z flag is set
            if self.reg.cpsr & 0x1:  # Check if Z flag (bit 0) is set
                self.reg.pc = self.reg[rd] & 0xFF
        else:
            raise RuntimeError(f"Invalid opcode {op:02X}")

    def step(self):
        self.fetch()
        self.decode_execute()

    def reset(self):
        self.__init__()
