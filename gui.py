import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QGridLayout,
    QLineEdit, QComboBox, QPushButton
)
from scraper import main as scraper
from PyQt6.QtCore import Qt



class MainWindow(QMainWindow):

    # TODO: Add toolbar button to input trackerhub URL
    # TODO: Add toolbar button to input API key
    # TODO: Add toolbar button to redirect to github repo

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backerhub")
        self.df = scraper()

        trackname_searchbar = QLineEdit()
        track_table = QTableWidget()
        artist_dropdown = QComboBox()
        quality_dropdown = QComboBox()
        era_dropdown = QComboBox()
        download_button = QPushButton('Download')
        selectall_button = QPushButton('Select All')
        deselectall_button = QPushButton('Unselect All')
        clearcontents_button = QPushButton('Reset Flags')

        artist_dropdown.addItem('Artist')
        quality_dropdown.addItem('Quality')
        era_dropdown.addItem('Era')

        layout = QGridLayout()

        dropdown_container = QWidget()
        dropdown_layout = QVBoxLayout()
        dropdown_layout.addWidget(artist_dropdown)
        dropdown_layout.addWidget(quality_dropdown)
        dropdown_layout.addWidget(era_dropdown)
        dropdown_layout.addStretch()  # pushes dropdowns to top, fills remaining space
        dropdown_layout.setContentsMargins(0, 0, 0, 0)
        dropdown_container.setLayout(dropdown_layout)

        layout.addWidget(trackname_searchbar, 0, 0, 1, 4)
        layout.addWidget(dropdown_container, 1, 0)
        layout.addWidget(track_table, 1, 1, 1, 3)
        layout.addWidget(download_button, 2, 0)
        layout.addWidget(selectall_button, 2, 1)
        layout.addWidget(deselectall_button, 2, 2)
        layout.addWidget(clearcontents_button, 2, 3)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 0)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())