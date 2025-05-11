# main.py

import sys
from PySide6.QtWidgets import QApplication
from controller.main_controller import MainController


def main():
    app = QApplication(sys.argv)
    controller = MainController(app)
    controller.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()