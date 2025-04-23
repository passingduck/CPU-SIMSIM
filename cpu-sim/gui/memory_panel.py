from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QTimer
from PySide6.QtWidgets import (QTableView, QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                              QPushButton, QInputDialog, QMessageBox, QTextEdit, QGroupBox)
import re

class MemoryModel(QAbstractTableModel):
    """256 바이트 메모리를 1 열 테이블로 노출. 편집 가능."""
    def __init__(self, cpu, parent=None):
        super().__init__(parent)
        self.cpu = cpu

    # 필수 구현
    def rowCount(self, parent=QModelIndex()):
        return 256

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            val = self.cpu.mem.read(index.row())
            return f"{val:04X}"  # 16-bit values (4 hex digits)
        return None

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Vertical:
            return f"{section:02X}"
        return "Value"

    # 편집 허용
    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            try:
                self.cpu.mem.write(index.row(), int(value, 16))
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
            except ValueError:
                return False
        return False


class MemoryPanel(QWidget):
    """스크롤 가능한 메모리 뷰와 편집 컨트롤."""
    def __init__(self, cpu, parent=None):
        super().__init__(parent)
        self.cpu = cpu
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Instructions label
        instr_label = QLabel("Double-click a cell to edit memory values directly")
        layout.addWidget(instr_label)
        
        # Memory table view
        self.table_view = QTableView(self)
        self.table_view.setModel(MemoryModel(cpu, self))
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.verticalHeader().setDefaultSectionSize(20)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_view)
        
        # Memory edit controls
        edit_layout = QHBoxLayout()
        
        # Edit specific address button
        self.btn_edit = QPushButton("Edit Address")
        self.btn_edit.clicked.connect(self.edit_address)
        edit_layout.addWidget(self.btn_edit)
        
        layout.addLayout(edit_layout)
        
        # Assembly input group
        asm_group = QGroupBox("Assembly Input")
        asm_layout = QVBoxLayout()
        
        # Assembly instructions help
        help_text = """
        Supported instructions (16-bit format):
        - AND Rd, Rs1   (0xdrs)  - Bitwise AND of Rd and Rs1, result in Rd
        - OR Rd, Rs1    (0x1rs)  - Bitwise OR of Rd and Rs1, result in Rd
        - ADD Rd, Rs1   (0x2rs)  - Add Rd and Rs1, result in Rd
        - MUL Rd, Rs1   (0x3rs)  - Multiply Rd and Rs1, result in Rd
        - DIV Rd, Rs1   (0x4rs)  - Divide Rd by Rs1, result in Rd
        - LDI Rd, #imm  (0x5ri)  - Load immediate value to Rd
        - LDM Rd, [Rs1] (0x6rs)  - Load from memory address in Rs1 to Rd
        - STM Rd, [Rs1] (0x7rs)  - Store Rd to memory address in Rs1
        - MV [Rd]       (0x8rs)  - Move value in Rd to PC (jump)
        - CMP Rd        (0x9rs)  - Compare Rd with 0, set Z flag if equal
        - JZ [Rd]       (0xArs)  - Jump to address in Rd if Z flag is set
        
        Rd, Rs1 can be R0-R15 (4 bits each)
        For LDI, immediate can be 0-255 (8 bits) using Rs1 and Rs2 fields
        If immediate is 0, the next word in memory is used as the full immediate
        Z flag is the rightmost bit of CPSR register
        """
        help_label = QLabel(help_text)
        asm_layout.addWidget(help_label)
        
        # Assembly text input
        self.asm_text = QTextEdit()
        self.asm_text.setPlaceholderText("Enter assembly instructions here, one per line")
        asm_layout.addWidget(self.asm_text)
        
        # Assembly controls
        asm_controls = QHBoxLayout()
        
        # Start address for assembly
        self.btn_start_addr = QPushButton("Set Start Address")
        self.btn_start_addr.clicked.connect(self.set_start_address)
        asm_controls.addWidget(self.btn_start_addr)
        
        # Assemble button
        self.btn_assemble = QPushButton("Assemble and Load")
        self.btn_assemble.clicked.connect(self.assemble_and_load)
        asm_controls.addWidget(self.btn_assemble)
        
        asm_layout.addLayout(asm_controls)
        asm_group.setLayout(asm_layout)
        layout.addWidget(asm_group)
        
        # Current start address for assembly
        self.start_address = 0
        
        # 주기적 새로고침
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)  # ms
    
    def refresh(self):
        """Refresh the memory view"""
        self.table_view.model().layoutChanged.emit()
    
    def edit_address(self):
        """Edit a specific memory address"""
        addr, ok1 = QInputDialog.getInt(self, "Edit Memory", 
                                      "Enter memory address (0-255):",
                                      0, 0, 255)
        if not ok1:
            return
            
        current_val = self.cpu.mem.read(addr)
        value_str, ok2 = QInputDialog.getText(self, "Edit Memory", 
                                           f"Enter new value for address {addr:02X} (hex):",
                                           text=f"{current_val:04X}")  # 16-bit values (4 hex digits)
        if ok2:
            try:
                value = int(value_str, 16)
                self.cpu.mem.write(addr, value)
                self.refresh()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", 
                                   "Please enter a valid hexadecimal value.")
    
    
    def set_start_address(self):
        """Set the start address for assembly code"""
        addr, ok = QInputDialog.getInt(self, "Assembly Start Address", 
                                     "Enter start address for assembly (0-255):",
                                     self.start_address, 0, 255)
        if ok:
            self.start_address = addr
    
    def assemble_and_load(self):
        """Assemble the code in the text box and load it into memory"""
        asm_text = self.asm_text.toPlainText().strip()
        if not asm_text:
            QMessageBox.warning(self, "Empty Input", "Please enter assembly code.")
            return
        
        lines = asm_text.split('\n')
        addr = self.start_address
        errors = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith(';'):  # Skip empty lines and comments
                continue
            
            try:
                # Parse the instruction
                instr_bytes = self.assemble_instruction(line)
                
                # Write to memory
                for b in instr_bytes:
                    if addr > 255:
                        errors.append(f"Line {i+1}: Memory overflow at address {addr}")
                        break
                    self.cpu.mem.write(addr, b)
                    addr += 1
            except ValueError as e:
                errors.append(f"Line {i+1}: {str(e)}")
        
        self.refresh()
        
        if errors:
            QMessageBox.warning(self, "Assembly Errors", 
                               "The following errors occurred:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Assembly Complete", 
                                   f"Code assembled and loaded starting at address {self.start_address:02X}")
    
    def assemble_instruction(self, line):
        """Convert a single assembly instruction to machine code bytes"""
        # Remove comments
        line = re.sub(r';.*$', '', line).strip()
        
        # Match instruction patterns
        # ALU operations: AND, OR, ADD, MUL, DIV
        alu_match = re.match(r'(AND|OR|ADD|MUL|DIV)\s+R(\d+),\s*R(\d+)', line, re.IGNORECASE)
        if alu_match:
            op_name, rd, rs1 = alu_match.groups()
            op_map = {'AND': 0x0, 'OR': 0x1, 'ADD': 0x2, 'MUL': 0x3, 'DIV': 0x4}
            op = op_map[op_name.upper()]
            rd = int(rd)
            rs1 = int(rs1)
            
            # Check register range
            if not (0 <= rd < 16 and 0 <= rs1 < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            # 16-bit instruction format: opcode(4) | rd(4) | rs1(4) | rs2/imm(4)
            instr = (op << 12) | (rd << 8) | (rs1 << 4) | 0  # rs2 is unused for ALU ops
            return [instr]
        
        # Load immediate: LDI Rd, #imm
        ldi_match = re.match(r'LDI\s+R(\d+),\s*#(\d+)', line, re.IGNORECASE)
        if ldi_match:
            rd, imm = ldi_match.groups()
            rd = int(rd)
            imm = int(imm)
            
            # Check register range
            if not (0 <= rd < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
            
            if 0 <= imm <= 255:
                # Immediate fits in 8 bits (split across rs1 and rs2 fields)
                rs1 = (imm >> 4) & 0xF  # High 4 bits
                rs2 = imm & 0xF         # Low 4 bits
                instr = (0x5 << 12) | (rd << 8) | (rs1 << 4) | rs2
                return [instr]
            else:
                # Large immediate needs an extra word
                instr = (0x5 << 12) | (rd << 8) | 0  # Use 0 to indicate extra word
                return [instr, imm & 0xFFFF]  # Only use the lower 16 bits
        
        # Load from memory: LDM Rd, [Rs1]
        ldm_match = re.match(r'LDM\s+R(\d+),\s*\[R(\d+)\]', line, re.IGNORECASE)
        if ldm_match:
            rd, rs1 = ldm_match.groups()
            rd = int(rd)
            rs1 = int(rs1)
            
            # Check register range
            if not (0 <= rd < 16 and 0 <= rs1 < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            instr = (0x6 << 12) | (rd << 8) | (rs1 << 4) | 0  # rs2 is unused
            return [instr]
        
        # Store to memory: STM Rd, [Rs1]
        stm_match = re.match(r'STM\s+R(\d+),\s*\[R(\d+)\]', line, re.IGNORECASE)
        if stm_match:
            rd, rs1 = stm_match.groups()
            rd = int(rd)
            rs1 = int(rs1)
            
            # Check register range
            if not (0 <= rd < 16 and 0 <= rs1 < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            instr = (0x7 << 12) | (rd << 8) | (rs1 << 4) | 0  # rs2 is unused
            return [instr]
        
        # Move to PC: MV [Rd]
        mv_match = re.match(r'MV\s+\[R(\d+)\]', line, re.IGNORECASE)
        if mv_match:
            rd = int(mv_match.group(1))
            
            # Check register range
            if not (0 <= rd < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            instr = (0x8 << 12) | (rd << 8) | 0  # rs1 and rs2 are unused
            return [instr]
        
        # Compare with zero: CMP Rd
        cmp_match = re.match(r'CMP\s+R(\d+)', line, re.IGNORECASE)
        if cmp_match:
            rd = int(cmp_match.group(1))
            
            # Check register range
            if not (0 <= rd < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            instr = (0x9 << 12) | (rd << 8) | 0  # rs1 and rs2 are unused
            return [instr]
        
        # Jump if zero: JZ [Rd]
        jz_match = re.match(r'JZ\s+\[R(\d+)\]', line, re.IGNORECASE)
        if jz_match:
            rd = int(jz_match.group(1))
            
            # Check register range
            if not (0 <= rd < 16):
                raise ValueError(f"Register out of range (must be R0-R15): {line}")
                
            instr = (0xA << 12) | (rd << 8) | 0  # rs1 and rs2 are unused
            return [instr]
        
        raise ValueError(f"Invalid instruction: {line}")
