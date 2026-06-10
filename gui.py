import sys
import sqlite3
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow,
    QVBoxLayout, QHBoxLayout, QWidget,
    QLineEdit, QComboBox, QPushButton, QListWidget,
    QLabel, QSizePolicy, QToolBar, QListWidgetItem,
    QCheckBox, QProgressBar, QFileDialog, QInputDialog,
    QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction


TRACK_LIMIT = 200
GITHUB_URL = 'https://github.com/alexatubc/backerhub'


# --- Background threads ---

class SyncThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            from scraper import main as scraper
            scraper()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, links, output_dir):
        super().__init__()
        self.links = links
        self.output_dir = output_dir

    def run(self):
        try:
            from downloader import download_file, find_file_hoster
            from os import makedirs
            import sqlite3
            makedirs(self.output_dir, exist_ok=True)
            connection = sqlite3.connect(
                'TrackerHub.db',
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            cursor = connection.cursor()
            total = len(self.links)
            for i, link in enumerate(self.links):
                try:
                    hoster = find_file_hoster(link)
                    download_file(link, self.output_dir, hoster, cursor)
                except Exception as e:
                    self.error.emit(f'Failed {link}: {e}')
                self.progress.emit(int((i + 1) / total * 100))
            connection.close()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


# --- Main window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Backerhub')
        self.output_dir = '.'

        # db
        self.connection = sqlite3.connect(
            'TrackerHub.db',
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.cursor = self.connection.cursor()

        # --- Widgets ---
        self.track_search_bar = QLineEdit()
        self.track_search_bar.setPlaceholderText('Search for Tracks...')
        self.track_search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.artist_dropdown = QComboBox()
        self.era_dropdown = QComboBox()
        self.quality_dropdown = QComboBox()
        self.portion_dropdown = QComboBox()
        for dropdown in [self.artist_dropdown, self.era_dropdown,
                         self.quality_dropdown, self.portion_dropdown]:
            dropdown.setFixedSize(150, 30)

        self.track_list_display = QListWidget()
        self.track_list_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.track_list_display.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list_display.customContextMenuRequested.connect(self.show_context_menu)

        self.num_displayed = QLabel('0 tracks')
        self.status_label = QLabel('')

        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        self.download_progress.setFixedHeight(16)

        self.download_btn = QPushButton('Download')
        self.select_all_btn = QPushButton('Select All')
        self.unselect_all_btn = QPushButton('Unselect All')
        self.sync_btn = QPushButton('Sync')
        for btn in [self.download_btn, self.select_all_btn,
                    self.unselect_all_btn, self.sync_btn]:
            btn.setFixedSize(100, 30)

        # --- Toolbar ---
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        url_action = QAction('Set Sheet URL', self)
        api_action = QAction('Set API Key', self)
        outdir_action = QAction('Set Output Dir', self)
        github_action = QAction('GitHub', self)
        toolbar.addAction(url_action)
        toolbar.addAction(api_action)
        toolbar.addAction(outdir_action)
        toolbar.addSeparator()
        toolbar.addAction(github_action)
        url_action.triggered.connect(self.set_sheet_url)
        api_action.triggered.connect(self.set_api_key)
        outdir_action.triggered.connect(self.set_output_dir)
        github_action.triggered.connect(lambda: webbrowser.open(GITHUB_URL))

        # --- Column headers ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(28, 0, 0, 0)
        header_layout.setSpacing(0)
        for label_text, width in [('Artist', 120), ('Name', 200), ('Era', 100), ('Quality', 80), ('Portion', 80), ('Notes', 160)]:
            lbl = QLabel(f'<b>{label_text}</b>')
            lbl.setFixedWidth(width)
            header_layout.addWidget(lbl)
        header_layout.addStretch()

        # --- Layout ---
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(self.artist_dropdown)
        filter_layout.addWidget(self.era_dropdown)
        filter_layout.addWidget(self.quality_dropdown)
        filter_layout.addWidget(self.portion_dropdown)
        filter_layout.addStretch()

        filter_panel = QWidget()
        filter_panel.setLayout(filter_layout)
        filter_panel.setFixedWidth(160)
        filter_panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        list_col = QVBoxLayout()
        list_col.setSpacing(0)
        list_col.addWidget(header_widget)
        list_col.addWidget(self.track_list_display)

        content_row = QHBoxLayout()
        content_row.setSpacing(8)
        content_row.addWidget(filter_panel, 0, Qt.AlignmentFlag.AlignTop)
        content_row.addLayout(list_col)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.num_displayed)
        bottom_row.addStretch()
        bottom_row.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.unselect_all_btn)
        button_layout.addWidget(self.sync_btn)
        button_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        main_layout.addWidget(self.track_search_bar)
        main_layout.addLayout(content_row)
        main_layout.addLayout(bottom_row)
        main_layout.addWidget(self.download_progress)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # --- Signals ---
        self.artist_dropdown.currentIndexChanged.connect(self.on_artist_changed)
        self.era_dropdown.currentIndexChanged.connect(self.populate_tracks)
        self.quality_dropdown.currentIndexChanged.connect(self.populate_tracks)
        self.portion_dropdown.currentIndexChanged.connect(self.populate_tracks)
        self.track_search_bar.textChanged.connect(self.populate_tracks)
        self.select_all_btn.clicked.connect(self.select_all)
        self.unselect_all_btn.clicked.connect(self.unselect_all)
        self.sync_btn.clicked.connect(self.sync)
        self.download_btn.clicked.connect(self.download)

        self.populate_artists()

    # --- Toolbar actions ---

    def set_sheet_url(self):
        url, ok = QInputDialog.getText(self, 'Set Sheet URL', 'Enter Trackerhub Google Sheet URL:')
        if ok and url and '/d/' in url:
            sheet_id = url.split('/d/')[1].split('/')[0]
            # TODO: persist to .env

    def set_api_key(self):
        key, ok = QInputDialog.getText(self, 'Set API Key', 'Enter Google API Key:')
        if ok and key:
            # TODO: persist to .env
            pass

    def set_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if path:
            self.output_dir = path
            self.status_label.setText(f'Output: {path}')

    # --- Population ---

    def populate_artists(self):
        self.artist_dropdown.blockSignals(True)
        self.artist_dropdown.clear()
        self.artist_dropdown.addItem('Artist', None)
        self.cursor.execute('''
            SELECT Artists.id, Artists.name, COUNT(Tracks.id) as track_count
            FROM Artists
            LEFT JOIN Tracks ON Artists.id = Tracks.artist_id
            GROUP BY Artists.id
            ORDER BY Artists.name
        ''')
        for artist_id, name, count in self.cursor.fetchall():
            label = f'{name} ({count})'
            self.artist_dropdown.addItem(label, artist_id)
        self.artist_dropdown.blockSignals(False)

    def on_artist_changed(self):
        artist_id = self.artist_dropdown.currentData()

        for dropdown in [self.era_dropdown, self.quality_dropdown, self.portion_dropdown]:
            dropdown.blockSignals(True)
            dropdown.clear()

        self.era_dropdown.addItem('Era', None)
        self.quality_dropdown.addItem('Quality', None)
        self.portion_dropdown.addItem('Portion', None)

        if artist_id is None:
            self.track_list_display.clear()
            self.num_displayed.setText('0 tracks')
            for dropdown in [self.era_dropdown, self.quality_dropdown, self.portion_dropdown]:
                dropdown.blockSignals(False)
            return

        self.cursor.execute('SELECT DISTINCT era FROM Tracks WHERE artist_id = ? AND era != ""', (artist_id,))
        for (era,) in self.cursor.fetchall():
            self.era_dropdown.addItem(era)

        self.cursor.execute('SELECT DISTINCT quality FROM Tracks WHERE artist_id = ? AND quality != ""', (artist_id,))
        for (quality,) in self.cursor.fetchall():
            self.quality_dropdown.addItem(quality)

        self.cursor.execute('SELECT DISTINCT portion FROM Tracks WHERE artist_id = ? AND portion != ""', (artist_id,))
        for (portion,) in self.cursor.fetchall():
            self.portion_dropdown.addItem(portion)

        for dropdown in [self.era_dropdown, self.quality_dropdown, self.portion_dropdown]:
            dropdown.blockSignals(False)

        self.populate_tracks()

    def populate_tracks(self):
        artist_id = self.artist_dropdown.currentData()

        if artist_id is None:
            self.track_list_display.clear()
            self.num_displayed.setText('0 tracks')
            return

        era = self.era_dropdown.currentText()
        quality = self.quality_dropdown.currentText()
        portion = self.portion_dropdown.currentText()
        search = self.track_search_bar.text().strip().lower()

        query = '''
            SELECT Tracks.id, Tracks.name, Tracks.era, Tracks.quality, Tracks.portion,
                   Artists.name, Tracks.notes,
                   EXISTS(SELECT 1 FROM Links WHERE Links.track_id = Tracks.id) as has_link
            FROM Tracks
            JOIN Artists ON Tracks.artist_id = Artists.id
            WHERE Tracks.artist_id = ?
        '''
        params = [artist_id]

        if era != 'Era':
            query += ' AND Tracks.era = ?'
            params.append(era)
        if quality != 'Quality':
            query += ' AND Tracks.quality = ?'
            params.append(quality)
        if portion != 'Portion':
            query += ' AND Tracks.portion = ?'
            params.append(portion)
        if search:
            query += ' AND LOWER(Tracks.name) LIKE ?'
            params.append(f'%{search}%')

        query += f' LIMIT {TRACK_LIMIT}'

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()

        self.track_list_display.clear()

        if not rows:
            empty_item = QListWidgetItem('No tracks found.')
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.track_list_display.addItem(empty_item)
            self.num_displayed.setText('0 tracks')
            return

        for row in rows:
            track_id, name, era_val, quality_val, portion_val, artist_name, notes, has_link = row
            self.add_track_item(track_id, name, era_val, quality_val, portion_val, artist_name, notes, bool(has_link))

        self.num_displayed.setText(f'{len(rows)} tracks')

    def add_track_item(self, track_id, name, era, quality, portion, artist_name, notes, has_link):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 2, 4, 2)

        checkbox = QCheckBox()
        artist_label = QLabel(artist_name)
        name_label = QLabel(name)
        era_label = QLabel(era or '')
        quality_label = QLabel(quality or '')
        portion_label = QLabel(portion or '')
        notes_label = QLabel(notes or '')
        notes_label.setToolTip(notes or '')

        artist_label.setFixedWidth(120)
        name_label.setFixedWidth(200)
        era_label.setFixedWidth(100)
        quality_label.setFixedWidth(80)
        portion_label.setFixedWidth(80)
        notes_label.setFixedWidth(160)
        notes_label.setStyleSheet('color: gray;')

        # grey out tracks with no link
        if not has_link:
            for lbl in [artist_label, name_label, era_label, quality_label, portion_label]:
                lbl.setStyleSheet('color: gray;')
            checkbox.setEnabled(False)

        row_layout.addWidget(checkbox)
        row_layout.addWidget(artist_label)
        row_layout.addWidget(name_label)
        row_layout.addWidget(era_label)
        row_layout.addWidget(quality_label)
        row_layout.addWidget(portion_label)
        row_layout.addWidget(notes_label)
        row_layout.addStretch()

        item = QListWidgetItem(self.track_list_display)
        item.setData(Qt.ItemDataRole.UserRole, track_id)
        item.setSizeHint(row_widget.sizeHint())
        self.track_list_display.addItem(item)
        self.track_list_display.setItemWidget(item, row_widget)

    # --- Button actions ---

    def select_all(self):
        for i in range(self.track_list_display.count()):
            item = self.track_list_display.item(i)
            widget = self.track_list_display.itemWidget(item)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isEnabled():
                    cb.setChecked(True)

    def unselect_all(self):
        for i in range(self.track_list_display.count()):
            item = self.track_list_display.item(i)
            widget = self.track_list_display.itemWidget(item)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def sync(self):
        self.sync_btn.setEnabled(False)
        self.status_label.setText('Syncing...')
        self.sync_thread = SyncThread()
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        self.sync_thread.start()

    def on_sync_finished(self):
        self.sync_btn.setEnabled(True)
        self.status_label.setText('Sync complete.')
        self.populate_artists()
        self.populate_tracks()

    def on_sync_error(self, msg):
        self.sync_btn.setEnabled(True)
        self.status_label.setText(f'Sync failed: {msg}')

    def download(self):
        checked_track_ids = []
        for i in range(self.track_list_display.count()):
            item = self.track_list_display.item(i)
            widget = self.track_list_display.itemWidget(item)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    checked_track_ids.append(item.data(Qt.ItemDataRole.UserRole))

        if not checked_track_ids:
            self.status_label.setText('No tracks selected.')
            return

        placeholders = ','.join('?' * len(checked_track_ids))
        self.cursor.execute(
            f'SELECT url FROM Links WHERE track_id IN ({placeholders})',
            checked_track_ids
        )
        links = [row[0] for row in self.cursor.fetchall() if row[0]]

        if not links:
            self.status_label.setText('No links found for selected tracks.')
            return

        self.download_btn.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_progress.setValue(0)
        self.status_label.setText(f'Downloading {len(links)} files...')

        self.download_thread = DownloadThread(links, self.output_dir)
        self.download_thread.progress.connect(self.download_progress.setValue)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(lambda msg: self.status_label.setText(msg))
        self.download_thread.start()

    def on_download_finished(self):
        self.download_btn.setEnabled(True)
        self.download_progress.setVisible(False)
        self.status_label.setText('Download complete.')

    # --- Context menu ---

    def show_context_menu(self, pos):
        item = self.track_list_display.itemAt(pos)
        if not item:
            return

        track_id = item.data(Qt.ItemDataRole.UserRole)
        self.cursor.execute('SELECT url FROM Links WHERE track_id = ?', (track_id,))
        link_row = self.cursor.fetchone()
        link = link_row[0] if link_row else None

        menu = QMenu(self)
        if link:
            open_action = menu.addAction('Open Link in Browser')
            copy_link_action = menu.addAction('Copy Link')
        else:
            no_link_action = menu.addAction('No link available')
            no_link_action.setEnabled(False)

        widget = self.track_list_display.itemWidget(item)
        name_label = widget.findChildren(QLabel)[1] if widget else None
        copy_name_action = menu.addAction('Copy Track Name')

        action = menu.exec(self.track_list_display.viewport().mapToGlobal(pos))

        if link:
            if action == open_action:
                webbrowser.open(link)
            elif action == copy_link_action:
                QApplication.clipboard().setText(link)
        if action == copy_name_action and name_label:
            QApplication.clipboard().setText(name_label.text())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 550)
    window.show()
    sys.exit(app.exec())