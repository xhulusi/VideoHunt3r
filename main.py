import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from ui.main_window import Ui_Form
from src.downloader import download_video_info, start_download
import yt_dlp

class VideoInfoThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            info = download_video_info(self.url)
            self.finished.emit(info)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.download_in_progress = False

        self.ui.btn_search.clicked.connect(self.search_video)
        self.ui.btn_download.clicked.connect(self.download_video)
        self.ui.url_input.textChanged.connect(self.check_url_input)
        self.ui.url_input.setPlaceholderText("Enter YouTube video URL here...")

        self.progress_bar = self.ui.progressBar
        self.progress_bar.setValue(0)

        self.ui.btn_search.setEnabled(False)
        self.ui.btn_download.setEnabled(False)
        self.align_line_edits()

        self.formats = {} 

    def align_line_edits(self):
        fields = [
            self.ui.description_le, self.ui.channel_name_le, self.ui.title_le,
            self.ui.channel_url_le, self.ui.view_count_le, self.ui.like_count_le,
            self.ui.comment_count_le, self.ui.dislike_count_le, self.ui.duration_le,
            self.ui.live_status_le, self.ui.age_limit_le, self.ui.avaiblity_le
        ]
        for le in fields:
            le.setAlignment(Qt.AlignLeft)
            le.setCursorPosition(0)
            le.textChanged.connect(lambda _, le=le: le.setCursorPosition(0))

    def check_url_input(self):
        url = self.ui.url_input.text().strip()
        enabled = bool(url) and not self.download_in_progress
        self.ui.btn_search.setEnabled(enabled)
        self.ui.btn_download.setEnabled(enabled)

    def seconds_to_minutes_format(self, seconds):
        try:
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            return f"{m}:{s:02d} min"
        except:
            return "N/A"

    def search_video(self):
        url = self.ui.url_input.text()
        self.ui.btn_search.setEnabled(False)
        self.ui.btn_download.setEnabled(False)
        self.ui.btn_search.setText("Searching...")
        self.ui.comboBox.clear()
        QApplication.processEvents()

        self.thread = VideoInfoThread(url)
        self.thread.finished.connect(self.display_video_info)
        self.thread.error.connect(self.display_error)
        self.thread.start()

    def display_video_info(self, info):
        self.ui.description_le.setText(info.get('description', 'N/A'))
        self.ui.channel_name_le.setText(info.get('channel_name', 'N/A'))
        self.ui.title_le.setText(info.get('title', 'N/A'))
        self.ui.channel_url_le.setText(info.get('channel_url', 'N/A'))
        self.ui.view_count_le.setText(str(info.get('view_count', 'N/A')))
        self.ui.like_count_le.setText(str(info.get('like_count', 'N/A')))
        self.ui.comment_count_le.setText(str(info.get('comment_count', 'N/A')))
        self.ui.dislike_count_le.setText(str(info.get('dislike_count', 'N/A')))
        self.ui.duration_le.setText(self.seconds_to_minutes_format(info.get('duration')))
        self.ui.live_status_le.setText(info.get('live_status', 'N/A'))
        self.ui.age_limit_le.setText(str(info.get('age_limit', 'N/A')))
        self.ui.avaiblity_le.setText(info.get('availability', 'N/A'))

        pixmap = QPixmap()
        pixmap.loadFromData(info.get('thumbnail', b''))
        self.ui.label_3.setPixmap(pixmap.scaled(self.ui.label_3.size(), Qt.KeepAspectRatio))

        self.populate_format_combobox(self.ui.url_input.text())
        self.ui.btn_search.setText("Search")
        self.ui.btn_search.setEnabled(True)
        self.ui.btn_download.setEnabled(True)
        self.progress_bar.setValue(0)


    def display_error(self, msg):
        self.ui.btn_search.setText("Search")
        self.ui.btn_search.setEnabled(True)
        self.ui.btn_download.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)

    def populate_format_combobox(self, url):
        self.ui.comboBox.clear()
        self.formats.clear()

        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('ext') == 'mp4']

            best_formats = {}
            for fmt in video_formats:
                height = fmt.get('height')
                size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                if height not in best_formats or size > (best_formats[height].get('filesize') or 0):
                    best_formats[height] = fmt

            for height in sorted(best_formats.keys(), reverse=True):
                fmt = best_formats[height]
                ext = fmt.get('ext')
                size = fmt.get('filesize') or fmt.get('filesize_approx')
                size_mb = round(size / (1024 * 1024), 1) if size else '??'
                desc = f"{height}p - {size_mb} MB - {ext}"
                self.formats[desc] = fmt.get('format_id')
                self.ui.comboBox.addItem(desc)

            self.ui.comboBox.addItem("MP3 (Audio Only)")
            self.formats["MP3 (Audio Only)"] = "bestaudio"

    def download_video(self):
        url = self.ui.url_input.text()
        selected_desc = self.ui.comboBox.currentText()
        format_id = self.formats.get(selected_desc, 'best')
        is_mp3 = selected_desc == "MP3 (Audio Only)"

        self.download_in_progress = True
        self.ui.btn_search.setEnabled(False)
        self.ui.btn_download.setEnabled(False)
        self.ui.url_input.setEnabled(False)
        self.ui.comboBox.setEnabled(False)
        self.ui.btn_download.setText("Downloading...")
        self.ui.btn_download.setStyleSheet("background-color: #2ecc71; color: white;")
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        self.download_thread = start_download(url, format_id, is_mp3)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(lambda msg: self.download_error(msg))
        self.download_thread.start()


    def update_progress(self, percent):
        self.progress_bar.setValue(int(percent))
        QApplication.processEvents()

    def download_finished(self):
        self.download_in_progress = False
        self.ui.url_input.setEnabled(True)
        self.ui.comboBox.setEnabled(True)
        self.ui.btn_download.setText("Download")
        self.ui.btn_download.setStyleSheet("")  
        self.ui.btn_search.setEnabled(True)
        self.ui.btn_download.setEnabled(True)
        self.progress_bar.setValue(100)
        QApplication.processEvents()
        QMessageBox.information(self, "Success", "Video successfully downloaded!")

    def download_error(self, msg):
        self.download_in_progress = False
        self.ui.url_input.setEnabled(True)
        self.ui.comboBox.setEnabled(True)
        self.ui.btn_download.setStyleSheet("background-color: #e74c3c; color: white;")
        self.ui.btn_download.setText("Download")  # <-- BU SATIR KRİTİK
        QTimer.singleShot(1000, lambda: self.ui.btn_download.setStyleSheet(""))
        QMessageBox.critical(self, "Error", msg)
        self.ui.btn_search.setEnabled(True)
        self.ui.btn_download.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())