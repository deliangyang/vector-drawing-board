"""Entry point for the Vector Drawing Board application."""

import sys

from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Vector Drawing Board")
    app.setOrganizationName("VectorDrawingBoard")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
