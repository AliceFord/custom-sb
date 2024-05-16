import sys
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtWidgets import QTableWidgetItem


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("groundmentor.ui", self)
        # self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.aircraftTable.setRowCount(2)
    window.aircraftTable.setItem(0, 0, QTableWidgetItem("Aircraft Type"))

    window.commandEntry.returnPressed.connect(lambda: window.commandEntry.setText(""))

    window.show()

    app.exec()
