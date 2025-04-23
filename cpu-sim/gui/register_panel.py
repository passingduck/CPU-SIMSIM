from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QGridLayout
from PySide6.QtCore import Qt, QTimer
from cpu.registers import GENERAL_REGS, SPECIAL_REGS

class RegisterPanel(QWidget):
    """
    8 개 GPR + 4 개 특수 레지스터를 그리드로 표시.
    200 ms 간격 QTimer 로 값 반영.
    """
    def __init__(self, cpu, parent=None):
        super().__init__(parent)
        self.cpu = cpu
        self.edits = []
        layout = QGridLayout(self)

        # 일반 레지스터 R0–R7
        for i in range(GENERAL_REGS):
            lbl = QLabel(f"R{i}")
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setAlignment(Qt.AlignRight)
            layout.addWidget(lbl, i, 0)
            layout.addWidget(edit, i, 1)
            self.edits.append(edit)

        # 특수 레지스터
        for row, name in enumerate(SPECIAL_REGS, GENERAL_REGS):
            lbl = QLabel(name)
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setAlignment(Qt.AlignRight)
            layout.addWidget(lbl, row, 0)
            layout.addWidget(edit, row, 1)
            self.edits.append(edit)

        layout.setColumnStretch(1, 1)

        # 주기적 업데이트
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_view)
        self.timer.start(200)   # ms

    def update_view(self):
        for i in range(GENERAL_REGS):
            self.edits[i].setText(f"{self.cpu.reg[i]:08X}")
        # 특수
        self.edits[8].setText(f"{self.cpu.reg.pc:08X}")
        self.edits[9].setText(f"{self.cpu.reg.ir:08X}")
        self.edits[10].setText(f"{self.cpu.reg.cpsr:08X}")
        self.edits[11].setText(f"{self.cpu.reg.lr:08X}")
