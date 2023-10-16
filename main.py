import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Slot
from mod_manager.instances.instance import Instance, MCVersion, MPVersion, Platform


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        widget = QWidget()
        self.setCentralWidget(widget)

        layout = QVBoxLayout(widget)

        button = QPushButton("lol")
        button.clicked.connect(self.say_hello)
        
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

    @Slot()
    def say_hello(self):
        print("Button clicked, Hello!")


if __name__ == "__main__":
    #app = QApplication(sys.argv)
    #main_window = MainWindow()

    #main_window.show()

    #app.exec()

    instance = Instance.create_instance("Stoneblock 3", MCVersion("1.18.2", "forge", "40.2.10"), MPVersion("1.8.0", "100", "6647"), Platform.FEEDTHEBEAST)
    instance.launch()
    