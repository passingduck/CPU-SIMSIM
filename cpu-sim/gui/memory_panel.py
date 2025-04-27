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
        help_text = (
            "Minimal LC-3 assembler (one word per line)\n"
            "--------------------------------------------------\n"
            "• ADD  DR, SR1, SR2            ; 레지스터-레지스터\n"
            "• ADD  DR, SR1, #imm5          ; 즉시값(-16…+15)\n"
            "• AND  …                       ; 형식 동일\n"
            "• NOT  DR, SR                  ; 비트 반전\n"
            "• BR[n][z][p] LABEL / #off9    ; PC-상대 분기\n"
            "• JMP  BaseR     |  RET        ; 점프 / 서브루틴 복귀\n"
            "• JSR  LABEL/#off11 | JSRR BaseR\n"
            "• LD / LDI / ST / STI  DR|SR, #off9\n"
            "• LDR / STR  DR|SR, BaseR, #off6\n"
            "• LEA  DR, #off9               ; 주소 계산\n"
            "• TRAP x23 / x25 …            ; 시스템 호출\n"
            "※ LABEL 은 아직 지원하지 않으며, #offset 숫자(10진/16진 0x…)만 가능\n"
        )
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
    
    def assemble_instruction(self, line: str):
        """
        단일 LC-3 어셈블리 라인을 16-bit 워드 리스트로 변환.
        ▸ 라벨 파서는 생략하고, #imm / #off 숫자만 허용.
        ▸ 모든 숫자는 10진 또는 0xHEX 인식.
        ▸ 잘못된 형식이면 ValueError 발생.
        """
        # 코멘트 제거
        line = re.sub(r';.*$', '', line).strip()
        if not line:
            raise ValueError("empty")

        # 공통 유틸
        def num(tok, bits, signed=True):
            """토큰 → int, 범위 검사(+sign extend를 기계가 하므로 여기선 값만 확인)"""
            base = 16 if tok.lower().startswith('0x') else 10
            v = int(tok, base)
            lo = -(1 << (bits-1)) if signed else 0
            hi =  (1 << (bits-1)) - 1 if signed else (1 << bits) - 1
            if not lo <= v <= hi:
                raise ValueError(f"immediate {tok} out of range for {bits}-bit field")
            return v & ((1 << bits) - 1)

        # -------- ADD / AND (두 형식) ---------------------------------
        m = re.match(r'(ADD|AND)\s+R(\d),\s*R(\d),\s*(R(\d)|#(-?\w+))$', line, re.I)
        if m:
            op, dr, sr1, last, sr2, imm = m.groups()
            opcode = 0x1 if op.upper() == 'ADD' else 0x5
            dr = int(dr); sr1 = int(sr1)
            if sr2:                          # 레지스터 형식
                sr2 = int(sr2)
                instr = (opcode << 12) | (dr << 9) | (sr1 << 6) | sr2
            else:                            # 즉시 형식
                imm5 = num(imm, 5)
                instr = (opcode << 12) | (dr << 9) | (sr1 << 6) | (1 << 5) | imm5
            return [instr]

        # -------- NOT --------------------------------------------------
        m = re.match(r'NOT\s+R(\d),\s*R(\d)$', line, re.I)
        if m:
            dr, sr = map(int, m.groups())
            instr = (0x9 << 12) | (dr << 9) | (sr << 6) | 0x3F
            return [instr]

        # -------- BR ---------------------------------------------------
        m = re.match(r'BR([nNpPzZ]{0,3})\s+#(-?\w+)$', line)
        if m:
            cond, off = m.groups()
            nzp = 0
            nzp |= 0b100 if 'n' in cond.lower() else 0
            nzp |= 0b010 if 'z' in cond.lower() else 0
            nzp |= 0b001 if 'p' in cond.lower() else 0
            if nzp == 0: nzp = 0b111                  # plain “BR”
            off9 = num(off, 9)
            instr = (0x0 << 12) | (nzp << 9) | off9
            return [instr]

        # -------- JMP / RET -------------------------------------------
        if re.fullmatch(r'RET', line, re.I):
            return [(0xC << 12) | (7 << 6)]
        m = re.match(r'JMP\s+R(\d)$', line, re.I)
        if m:
            baser = int(m.group(1))
            return [(0xC << 12) | (baser << 6)]

        # -------- JSR / JSRR ------------------------------------------
        m = re.match(r'JSRR\s+R(\d)$', line, re.I)
        if m:
            baser = int(m.group(1))
            instr = (0x4 << 12) | (0 << 11) | (0 << 9) | (baser << 6)
            return [instr]
        m = re.match(r'JSR\s+#(-?\w+)$', line, re.I)
        if m:
            off11 = num(m.group(1), 11)
            instr = (0x4 << 12) | (1 << 11) | off11
            return [instr]

        # -------- LD / LDI / ST / STI (PC-offset9) --------------------
        for mnemonic, opc in [('LD',0x2), ('LDI',0xA), ('ST',0x3), ('STI',0xB)]:
            m = re.match(fr'{mnemonic}\s+R?(\d),\s*#(-?\w+)$', line, re.I)
            if m:
                reg, off = m.groups()
                reg = int(reg)
                off9 = num(off, 9)
                instr = (opc << 12) | (reg << 9) | off9
                return [instr]

        # -------- LDR / STR (Base+off6) -------------------------------
        for mnemonic, opc in [('LDR',0x6), ('STR',0x7)]:
            m = re.match(fr'{mnemonic}\s+R(\d),\s*R(\d),\s*#(-?\w+)$', line, re.I)
            if m:
                drsr, baser, off = m.groups()
                drsr  = int(drsr)
                baser = int(baser)
                off6  = num(off, 6)
                instr = (opc << 12) | (drsr << 9) | (baser << 6) | off6
                return [instr]

        # -------- LEA --------------------------------------------------
        m = re.match(r'LEA\s+R(\d),\s*#(-?\w+)$', line, re.I)
        if m:
            dr, off = m.groups()
            dr = int(dr); off9 = num(off, 9, signed=True)
            instr = (0xE << 12) | (dr << 9) | off9
            return [instr]

        # -------- TRAP -------------------------------------------------
        m = re.match(r'TRAP\s+x([0-9A-F]{1,2})$', line, re.I)
        if m:
            vect = int(m.group(1), 16) & 0xFF
            instr = (0xF << 12) | vect
            return [instr]

        raise ValueError("syntax error or unsupported opcode")
