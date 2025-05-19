import os
import requests
import yt_dlp
from PyQt5.QtCore import QObject, pyqtSignal, QThread

class DownloadThread(QThread):
    progress_signal = pyqtSignal(float)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, url, format_option, is_mp3=False):
        super().__init__()
        self.url = url
        self.format_option = format_option
        self.is_mp3 = is_mp3

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    self.progress_signal.emit(percent)
                elif 'downloaded_bytes' in d and 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                    self.progress_signal.emit(percent)
                elif '_percent_str' in d:
                    percent_str = d.get('_percent_str', '0%').replace('%', '')
                    self.progress_signal.emit(float(percent_str))
            except:
                pass
        elif d['status'] == 'finished':
            self.progress_signal.emit(100.0)

    def run(self):
        try:
            os.makedirs('downloads', exist_ok=True)

            ydl_opts = {
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
                'progress_hooks': [self.progress_hook],
                'format': self.format_option
            }

            if self.is_mp3:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

class Downloader(QObject):
    progress_signal = pyqtSignal(float)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def download_video_info(self, url):
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnail_url = info.get('thumbnail', '')
            thumbnail_data = requests.get(thumbnail_url).content if thumbnail_url else b''
            return {
                'description': info.get('description', ''),
                'channel_name': info.get('uploader', ''),
                'title': info.get('title', ''),
                'channel_url': info.get('channel_url', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'comment_count': info.get('comment_count', 0),
                'dislike_count': info.get('dislike_count', 0),
                'duration': str(info.get('duration', '')),
                'live_status': 'Live' if info.get('is_live') else 'Not Live',
                'age_limit': info.get('age_limit', 0),
                'availability': info.get('availability', ''),
                'thumbnail': thumbnail_data
            }

    def start_download(self, url, format_option, is_mp3=False): 
        return DownloadThread(url, format_option, is_mp3)

def download_video_info(url):
    return Downloader().download_video_info(url)

def start_download(url, format_option, is_mp3=False):  
    return Downloader().start_download(url, format_option, is_mp3)
