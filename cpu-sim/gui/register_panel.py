from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QGridLayout, QMessageBox
from PySide6.QtCore import Qt, QTimer, Slot
from cpu.registers import GENERAL_REGS, SPECIAL_REGS

class RegisterPanel(QWidget):
    """
    8 개 GPR + 4 개 특수 레지스터를 그리드로 표시.
    200 ms 간격 QTimer 로 값 반영.
    레지스터 값 직접 수정, 상수 로드, 메모리 로드/저장 기능 추가.
    """
    def __init__(self, cpu, parent=None):
        super().__init__(parent)
        self.cpu = cpu
        self.edits = []
        
        # Register display grid
        layout = QGridLayout(self)
        
        # 일반 레지스터 R0–R7
        for i in range(GENERAL_REGS):
            lbl = QLabel(f"R{i}")
            edit = QLineEdit()
            edit.setReadOnly(False)  # Make editable
            edit.setAlignment(Qt.AlignRight)
            edit.editingFinished.connect(self.register_edited)
            edit.setObjectName(f"R{i}")
            layout.addWidget(lbl, i, 0)
            layout.addWidget(edit, i, 1)
            self.edits.append(edit)

        # 특수 레지스터
        for row, name in enumerate(SPECIAL_REGS, GENERAL_REGS):
            lbl = QLabel(name)
            edit = QLineEdit()
            edit.setReadOnly(True)  # Special registers remain read-only
            edit.setAlignment(Qt.AlignRight)
            layout.addWidget(lbl, row, 0)
            layout.addWidget(edit, row, 1)
            self.edits.append(edit)

        layout.setColumnStretch(1, 1)

        # 주기적 업데이트
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_view)
        self.timer.start(200)   # ms
        
        # Flag to prevent editing during update
        self.updating = False

    def update_view(self):
        """Update register display from CPU state"""
        self.updating = True
        for i in range(GENERAL_REGS):
            self.edits[i].setText(f"{self.cpu.reg[i]:04X}")  # 16-bit values (4 hex digits)
        # 특수
        special_start = GENERAL_REGS
        self.edits[special_start].setText(f"{self.cpu.reg.pc:04X}")
        self.edits[special_start+1].setText(f"{self.cpu.reg.ir:04X}")
        self.edits[special_start+2].setText(f"{self.cpu.reg.cpsr:04X}")
        self.edits[special_start+3].setText(f"{self.cpu.reg.lr:04X}")
        self.updating = False
    
    @Slot()
    def register_edited(self):
        """Handle direct editing of register values"""
        if self.updating:
            return
            
        sender = self.sender()
        if not sender:
            return
            
        try:
            reg_idx = int(sender.objectName()[1:])  # Extract number from "R0", "R1", etc.
            value = int(sender.text(), 16)
            self.cpu.reg[reg_idx] = value
        except (ValueError, IndexError):
            QMessageBox.warning(self, "Invalid Input", 
                               "Please enter a valid hexadecimal value.")
            self.update_view()  # Reset to current value
