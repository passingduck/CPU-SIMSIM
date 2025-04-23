# --- main.py ---
"""Application entry-point for the educational CPU simulator.
Run `python -m main` (or `python main.py`) from the project root to launch the GUI."""
from gui.main_window import run

if __name__ == "__main__":
    run()

# --- gui/register_panel.py ---
"""Widget that shows the 8 general‑purpose registers and the four special
registers (PC, IR, CPSR, LR) in a compact table. Updates are pulled from the
CPU instance via the `refresh()` slot, which the control panel triggers after
each CPU step."""
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout
from PySide6.QtCore import Slot

from cpu.registers import GENERAL_REGS, SPECIAL_REGS

class RegisterPanel(QWidget):
    HEADERS = [f"R{i}" for i in range(GENERAL_REGS)] + SPECIAL_REGS

    def __init__(self, cpu):
        super().__init__()
        self.cpu = cpu
        self.table = QTableWidget(len(self.HEADERS), 2)
        self.table.setHorizontalHeaderLabels(["Reg", "Value (hex)"])
        for row, name in enumerate(self.HEADERS):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem("0x00000000"))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.refresh()

    @Slot()
    def refresh(self):
        """Update table values from CPU state."""
        for i in range(GENERAL_REGS):
            val = self.cpu.reg[i]
            self.table.item(i, 1).setText(f"0x{val:08X}")
        # special regs
        specials = [self.cpu.reg.pc, self.cpu.reg.ir, self.cpu.reg.cpsr, self.cpu.reg.lr]
        for j, val in enumerate(specials, start=GENERAL_REGS):
            self.table.item(j, 1).setText(f"0x{val:08X}")

# --- gui/memory_panel.py ---
"""Central widget that displays all 256 memory cells in a scrollable table."""
from PySide6.QtWidgets import QTableView, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

MEM_COLS = 16  # 16 columns x 16 rows == 256 cells

class MemoryModel(QAbstractTableModel):
    def __init__(self, cpu):
        super().__init__()
        self.cpu = cpu

    # Qt model overrides
    def rowCount(self, parent=QModelIndex()):
        return 256 // MEM_COLS

    def columnCount(self, parent=QModelIndex()):
        return MEM_COLS

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        addr = index.row()*MEM_COLS + index.column()
        val = self.cpu.mem.read(addr)
        return f"{val:02X}"

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return f"+{section:X}"
        return f"{section*MEM_COLS:02X}"

    def refresh(self):
        top_left = self.index(0, 0)
        bottom_right = self.index(self.rowCount()-1, self.columnCount()-1)
        self.dataChanged.emit(top_left, bottom_right)

class MemoryPanel(QWidget):
    def __init__(self, cpu):
        super().__init__()
        self.model = MemoryModel(cpu)
        view = QTableView()
        view.setModel(self.model)
        view.horizontalHeader().setStretchLastSection(True)
        view.verticalHeader().setVisible(False)
        view.setSelectionMode(QTableView.NoSelection)
        layout = QVBoxLayout(self)
        layout.addWidget(view)
        self.setLayout(layout)

    def refresh(self):
        self.model.refresh()

# --- gui/control_panel.py ---
"""Run/step/reset buttons controlling the CPU and updating views."""
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer, Slot

class ControlPanel(QWidget):
    def __init__(self, cpu, memory_panel):
        super().__init__()
        self.cpu = cpu
        self.memory_panel = memory_panel

        self.btn_step = QPushButton("Step")
        self.btn_run  = QPushButton("Run")
        self.btn_reset = QPushButton("Reset")
        self.status = QLabel("Ready")

        layout = QHBoxLayout(self)
        for w in (self.btn_step, self.btn_run, self.btn_reset, self.status):
            layout.addWidget(w)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(200)  # 5 Hz
        self.timer.timeout.connect(self.step)

        # connections
        self.btn_step.clicked.connect(self.step)
        self.btn_run.clicked.connect(self.toggle_run)
        self.btn_reset.clicked.connect(self.reset)

    @Slot()
    def step(self):
        try:
            self.cpu.step()
            self.parent().findChild(QWidget, "Registers").refresh()
            self.memory_panel.refresh()
            self.status.setText(f"PC=0x{self.cpu.reg.pc:02X}")
        except Exception as e:
            self.timer.stop()
            self.status.setText(str(e))

    @Slot()
    def toggle_run(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_run.setText("Run")
        else:
            self.timer.start()
            self.btn_run.setText("Pause")

    @Slot()
    def reset(self):
        self.cpu.reset()
        self.parent().findChild(QWidget, "Registers").refresh()
        self.memory_panel.refresh()
        self.status.setText("Reset done")
