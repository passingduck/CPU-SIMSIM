from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer

class ControlPanel(QWidget):
    """
    Step / Run / Pause / Reset 버튼과 상태 레이블.
    Run 시 QTimer 로 CPU.step() 을 고속 호출.
    """
    def __init__(self, cpu, mem_view, parent=None):
        super().__init__(parent)
        self.cpu = cpu
        self.mem_view = mem_view

        self.btn_step  = QPushButton("Step")
        self.btn_run   = QPushButton("Run")
        self.btn_pause = QPushButton("Pause")
        self.btn_reset = QPushButton("Reset")
        self.status    = QLabel("Stopped")

        lay = QHBoxLayout(self)
        for b in (self.btn_step, self.btn_run,
                  self.btn_pause, self.btn_reset, self.status):
            lay.addWidget(b)

        # connections
        self.btn_step.clicked.connect(self.step_once)
        self.btn_run.clicked.connect(self.run)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_reset.clicked.connect(self.reset)

        # timer for continuous run
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step_once)
        self.timer.setInterval(50)  # 20 Hz

    def step_once(self):
        if not self.cpu.running:
            self.status.setText("Stopped")
        try:
            self.cpu.step()
            self.status.setText(f"PC={self.cpu.reg.pc:02X}")
        except RuntimeError as e:
            self.status.setText(str(e))

    def run(self):
        self.cpu.running = True
        self.timer.start()
        self.status.setText("Running")

    def pause(self):
        self.cpu.running = False
        self.timer.stop()
        self.status.setText("Paused")

    def reset(self):
        self.cpu.reset()
        self.mem_view.model().layoutChanged.emit()
        self.status.setText("Reset OK")
