from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QTimer
from PySide6.QtWidgets import QTableView

class MemoryModel(QAbstractTableModel):
    """256 바이트 메모리를 1 열 테이블로 노출."""
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
            return f"{val:08X}"
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


class MemoryPanel(QTableView):
    """스크롤 가능한 메모리 뷰."""
    def __init__(self, cpu, parent=None):
        super().__init__(parent)
        self.setModel(MemoryModel(cpu, self))
        self.setSelectionBehavior(QTableView.SelectRows)
        self.verticalHeader().setDefaultSectionSize(20)
        self.horizontalHeader().setStretchLastSection(True)

        # 주기적 새로고침
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.model().layoutChanged.emit)
        self.timer.start(500)  # ms
