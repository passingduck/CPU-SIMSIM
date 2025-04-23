from PySide6.QtWidgets import (QMainWindow, QWidget, QDockWidget,
                               QVBoxLayout, QApplication)
from PySide6.QtCore import Qt
from .register_panel import RegisterPanel
from .memory_panel import MemoryPanel
from .control_panel import ControlPanel
from cpu.cpu_core import CPU
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cpu = CPU()
        self.setWindowTitle("Educational CPU Simulator")

        # 중앙 위젯: 메모리
        self.memory_panel = MemoryPanel(self.cpu)
        self.setCentralWidget(self.memory_panel)

        # Dock 1 : 레지스터
        reg_dock = QDockWidget("Registers", self)
        reg_dock.setWidget(RegisterPanel(self.cpu))
        self.addDockWidget(Qt.LeftDockWidgetArea, reg_dock)

        # Dock 2 : 컨트롤
        ctrl_dock = QDockWidget("Control", self)
        ctrl_dock.setWidget(ControlPanel(self.cpu, self.memory_panel))
        self.addDockWidget(Qt.BottomDockWidgetArea, ctrl_dock)


def run():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.resize(1280, 960)
    mw.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
