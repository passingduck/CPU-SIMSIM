MEM_SIZE = 256

class Memory:
    def __init__(self):
        self.mem = [0]*MEM_SIZE

    def read(self, addr: int) -> int:
        return self.mem[addr & 0xFF]

    def write(self, addr: int, value: int):
        self.mem[addr & 0xFF] = value & 0xFFFFFFFF
