MEM_SIZE = 256  # Number of 16-bit words in memory

class Memory:
    def __init__(self):
        self.mem = [0]*MEM_SIZE

    def read(self, addr: int) -> int:
        """Read a 16-bit word from memory"""
        return self.mem[addr & 0xFF]

    def write(self, addr: int, value: int):
        """Write a 16-bit word to memory"""
        self.mem[addr & 0xFF] = value & 0xFFFF  # Mask to 16 bits
    
    def read_byte(self, addr: int) -> int:
        """Read an 8-bit byte from memory (for backward compatibility)"""
        word_addr = addr >> 1  # Divide by 2 to get word address
        word = self.mem[word_addr & 0xFF]
        if addr & 1:  # Odd address, return high byte
            return (word >> 8) & 0xFF
        else:  # Even address, return low byte
            return word & 0xFF
    
    def write_byte(self, addr: int, value: int):
        """Write an 8-bit byte to memory (for backward compatibility)"""
        word_addr = addr >> 1  # Divide by 2 to get word address
        word = self.mem[word_addr & 0xFF]
        if addr & 1:  # Odd address, modify high byte
            word = (word & 0x00FF) | ((value & 0xFF) << 8)
        else:  # Even address, modify low byte
            word = (word & 0xFF00) | (value & 0xFF)
        self.mem[word_addr & 0xFF] = word
