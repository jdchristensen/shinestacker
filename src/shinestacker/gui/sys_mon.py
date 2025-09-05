import psutil
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QColor

class SystemMonitorOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_timer()        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(8, 4, 8, 4)        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(240, 240, 240, 220);
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                background: transparent;
            }
        """)        
        self.cpu_label = QLabel("CPU: --%")
        self.cpu_label.setMinimumWidth(60)        
        self.mem_label = QLabel("MEM: --%")
        self.mem_label.setMinimumWidth(70)        
        layout.addWidget(self.cpu_label)
        layout.addWidget(self.mem_label)
        self.setLayout(layout)
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # Update every second
        
    def update_stats(self):
        cpu_percent = psutil.cpu_percent()        
        memory = psutil.virtual_memory()
        mem_percent = memory.percent        
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self.mem_label.setText(f"MEM: {mem_percent:.1f}%")
