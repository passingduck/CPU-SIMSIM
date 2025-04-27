from .registers import Registers
from .memory import Memory

class CPU:
    """
    LC-3 하드웨어 동작을 최소-단위로 모사한 소프트-CPU.
    ─────────────────────────────────────────────────────
    • fetch()  : 메모리에서 16-bit 명령어 읽고 PC++
    • decode_execute(): opcode 해석 → 각 명령 수행
    • step()   : 한 사이클 실행 (fetch → decode/exec)
    • reset()  : 레지스터/메모리 초기화
    """

    def __init__(self):
        self.reg = Registers()   # R0..R7, PC, CPSR, SSP/USP 등
        self.mem = Memory()      # 64 KiB 메모리 + MMIO hook
        self.running = False

    # ───────────────────────────── fetch ─────────────────────────────
    def fetch(self):
        """현재 PC 위치에서 16-bit 명령어를 읽어 IR에 저장, PC += 1"""
        self.reg.ir = self.mem.read(self.reg.pc)
        self.reg.pc = (self.reg.pc + 1) & 0xFFFF  # 16-bit wrap-around

    # ───────────────────── helpers (sign-extend / CC) ─────────────────
    @staticmethod
    def sext(val: int, bits: int) -> int:
        """
        bits-bit two’s-complement 값을 16-bit 정수로 부호 확장.
        예) sext(0b11111,5) == -1
        """
        sign = 1 << (bits - 1)
        return (val & (sign - 1)) - (val & sign)

    def setcc(self, value: int):
        """NZP 플래그(PSR[2:0])를 value(16-bit) 값으로 갱신"""
        self.reg.cpsr &= ~0x7                  # N,Z,P 클리어
        if value & 0x8000:   self.reg.cpsr |= 0x4   # N
        elif value == 0:     self.reg.cpsr |= 0x2   # Z
        else:                self.reg.cpsr |= 0x1   # P

    # ───────────────────────── decode / execute ──────────────────────
    def decode_execute(self):
        instr = self.reg.ir
        op = (instr >> 12) & 0xF               # bits[15:12]

        # ───────────── ADD (0001) ─────────────
        if op == 0b0001:
            rd  = (instr >> 9) & 0x7
            rs1 = (instr >> 6) & 0x7
            if (instr >> 5) & 1:               # imm5 사용
                imm5 = self.sext(instr & 0x1F, 5)
                result = (self.reg[rs1] + imm5) & 0xFFFF
            else:                              # 레지스터-레지스터
                rs2 = instr & 0x7
                result = (self.reg[rs1] + self.reg[rs2]) & 0xFFFF
            self.reg[rd] = result
            self.setcc(result)

        # ───────────── AND (0101) ─────────────
        elif op == 0b0101:
            rd  = (instr >> 9) & 0x7
            rs1 = (instr >> 6) & 0x7
            if (instr >> 5) & 1:
                imm5 = self.sext(instr & 0x1F, 5)
                result = self.reg[rs1] & imm5
            else:
                rs2 = instr & 0x7
                result = self.reg[rs1] & self.reg[rs2]
            result &= 0xFFFF
            self.reg[rd] = result
            self.setcc(result)

        # ───────────── BR (0000) ──────────────
        elif op == 0b0000:
            n, z, p = (instr >> 11) & 1, (instr >> 10) & 1, (instr >> 9) & 1
            offset9 = self.sext(instr & 0x1FF, 9)
            N = (self.reg.cpsr >> 2) & 1
            Z = (self.reg.cpsr >> 1) & 1
            P =  self.reg.cpsr       & 1
            if (n and N) or (z and Z) or (p and P):
                # incremented PC(reg.pc) + SignExt(offset9)
                self.reg.pc = (self.reg.pc + offset9) & 0xFFFF

        # ───────────── JMP / RET (1100) ───────
        elif op == 0b1100:
            baser = (instr >> 6) & 0x7          # BaseR or R7(RET)
            self.reg.pc = self.reg[baser]

        # ───────────── JSR / JSRR (0100) ──────
        elif op == 0b0100:
            self.reg[7] = self.reg.pc           # 링크(증가된 PC)
            if (instr >> 11) & 1:               # JSR (PC+off11)
                off11 = self.sext(instr & 0x7FF, 11)
                self.reg.pc = (self.reg.pc + off11) & 0xFFFF
            else:                              # JSRR (BaseR)
                baser = (instr >> 6) & 0x7
                self.reg.pc = self.reg[baser]

        # ───────────── LD (0010) ──────────────
        elif op == 0b0010:
            dr   = (instr >> 9) & 0x7
            off9 = self.sext(instr & 0x1FF, 9)
            addr = (self.reg.pc + off9) & 0xFFFF
            val  = self.mem.read(addr)
            self.reg[dr] = val
            self.setcc(val)

        # ───────────── LDI (1010) ─────────────
        elif op == 0b1010:
            dr   = (instr >> 9) & 0x7
            off9 = self.sext(instr & 0x1FF, 9)
            ptr  = self.mem.read((self.reg.pc + off9) & 0xFFFF)
            val  = self.mem.read(ptr & 0xFFFF)
            self.reg[dr] = val
            self.setcc(val)

        # ───────────── LDR (0110) ─────────────
        elif op == 0b0110:
            dr   = (instr >> 9) & 0x7
            baser= (instr >> 6) & 0x7
            off6 = self.sext(instr & 0x3F, 6)
            addr = (self.reg[baser] + off6) & 0xFFFF
            val  = self.mem.read(addr)
            self.reg[dr] = val
            self.setcc(val)

        # ───────────── LEA (1110) ─────────────
        elif op == 0b1110:
            dr   = (instr >> 9) & 0x7
            off9 = self.sext(instr & 0x1FF, 9)
            addr = (self.reg.pc + off9) & 0xFFFF
            self.reg[dr] = addr
            self.setcc(addr)

        # ───────────── NOT (1001) ─────────────
        elif op == 0b1001:
            dr = (instr >> 9) & 0x7
            sr = (instr >> 6) & 0x7
            val = (~self.reg[sr]) & 0xFFFF
            self.reg[dr] = val
            self.setcc(val)

        # ───────────── ST (0011) ──────────────
        elif op == 0b0011:
            sr   = (instr >> 9) & 0x7
            off9 = self.sext(instr & 0x1FF, 9)
            addr = (self.reg.pc + off9) & 0xFFFF
            self.mem.write(addr, self.reg[sr])

        # ───────────── STI (1011) ─────────────
        elif op == 0b1011:
            sr   = (instr >> 9) & 0x7
            off9 = self.sext(instr & 0x1FF, 9)
            ptr  = self.mem.read((self.reg.pc + off9) & 0xFFFF)
            self.mem.write(ptr & 0xFFFF, self.reg[sr])

        # ───────────── STR (0111) ─────────────
        elif op == 0b0111:
            sr   = (instr >> 9) & 0x7
            baser= (instr >> 6) & 0x7
            off6 = self.sext(instr & 0x3F, 6)
            self.mem.write((self.reg[baser] + off6) & 0xFFFF,
                           self.reg[sr])

        # ───────────── RTI (1000) ─────────────
        elif op == 0b1000:
            if (self.reg.cpsr >> 15) & 1:
                raise RuntimeError("RTI in user mode")
            # PC ← pop, PSR ← pop
            sp = self.reg[6]; new_pc = self.mem.read(sp); self.reg[6]=(sp+1)&0xFFFF
            sp = self.reg[6]; new_psr= self.mem.read(sp); self.reg[6]=(sp+1)&0xFFFF
            self.reg.pc, self.reg.cpsr = new_pc, new_psr
            # User-mode 복귀 시 스택 포인터 교체
            if (new_psr >> 15) & 1:
                self.reg.saved_ssp = self.reg[6]
                self.reg[6]        = self.reg.saved_usp

        # ───────────── TRAP (1111) ────────────
        elif op == 0b1111:
            trapvect8 = instr & 0xFF
            old_psr = self.reg.cpsr
            # User → Supervisor 스택 전환
            if (old_psr >> 15) & 1:
                self.reg.saved_usp = self.reg[6]
                self.reg[6]        = self.reg.saved_ssp
            # PSR, PC push (PSR 먼저)
            self.reg[6] = (self.reg[6] - 1) & 0xFFFF
            self.mem.write(self.reg[6], old_psr)
            self.reg[6] = (self.reg[6] - 1) & 0xFFFF
            self.mem.write(self.reg[6], self.reg.pc)
            # Supervisor 모드 진입
            self.reg.cpsr &= ~(1 << 15)
            # Trap vector 테이블 진입
            vector_addr = trapvect8               # ZEXT
            self.reg.pc = self.mem.read(vector_addr) & 0xFFFF

        # ───────────── Illegal opcode (1101) ──
        elif op == 0b1101:
            raise RuntimeError("Illegal-opcode exception (1101)")

        else:
            raise RuntimeError(f"Unknown opcode {op:04b}")

    # ───────────────────────────── runner ─────────────────────────────
    def step(self):
        """한 명령어 사이클(fetch-decode-exec) 실행"""
        self.fetch()
        self.decode_execute()

    def reset(self):
        """CPU/레지스터/메모리를 초기 상태로 되돌림"""
        self.__init__()
