import sys
import cv2
import subprocess
import os.path
# import ffmpeg
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QSlider, QFileDialog
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QTimer, QUrl

output_dir =    'C:\\svoo\\stuff\\Code\\_projects\\video_editor\\output'
temp_dir =      'C:\\svoo\\stuff\\Code\\_projects\\video_editor\\temp'

MIN_LENGTH = 3  # seconds
FILE_SIZE = 10  # mb

class VideoTrimmer(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.cap = None
        self.frame_count = 0
        self.fps = 30
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Trimmer")
        # self.setGeometry(0, 0, 1280, 720)
        self.setGeometry(0, 0, 978, 720)

        # center the window
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()

        center_x = (screen_geometry.width() - window_geometry.width()) // 2
        center_y = (screen_geometry.height() - window_geometry.height()) // 2
        
        self.move(center_x, center_y)


        # select file
        self.select_button = QPushButton("Select Video", self)
        self.select_button.clicked.connect(self.load_video)

        # video playback
        self.video_widget = QVideoWidget(self)
        self.player = QMediaPlayer(self)
        self.player.setVideoOutput(self.video_widget)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        # progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.progress_slider.setEnabled(False)
        self.progress_slider.sliderMoved.connect(self.update_progress)
        self.progress_slider.sliderReleased.connect(self.stop_update_progress)

        # start time
        self.start_label = QLabel("Start Time: 0 sec", self)
        self.start_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.start_slider.setEnabled(False)
        # self.start_slider.valueChanged.connect(self.update_start_time)
        self.start_slider.sliderMoved.connect(self.update_start_time)

        # end time
        self.end_label = QLabel("End Time: 0 sec", self)
        self.end_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.end_slider.setEnabled(False)
        # self.end_slider.valueChanged.connect(self.update_end_time)
        self.end_slider.sliderMoved.connect(self.update_end_time)

        # trim
        self.trim_button = QPushButton("Trim Video", self)
        self.trim_button.setEnabled(False)
        self.trim_button.clicked.connect(self.trim_video)

        # make layout
        layout = QVBoxLayout()
        layout.addWidget(self.select_button)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.progress_slider)
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_slider)
        layout.addWidget(self.end_label)
        layout.addWidget(self.end_slider)
        layout.addWidget(self.trim_button)

        self.setLayout(layout)

    def load_video(self):
        file_dialog = QFileDialog()
        self.video_path, _ = file_dialog.getOpenFileName(self, "Select Video", "", "Videos (*.mp4 *.avi *.mov)")
        self.original_path = self.video_path

        if self.video_path:
            vf_name = self.video_path \
                .split('\\')[-1] \
                .split('/')[-1] \
                .replace('.mp4', '')
            # vf_name = ''
            output_path = temp_dir + '\\' + vf_name + "_merged_audio.mp4"
            # print(output_path)
            # exit(0)

            # Merge audio tracks using FFmpeg
            if not os.path.exists(output_path):
                print('file not opened before, generating audio...')
                command = [
                    "ffmpeg", "-i", self.video_path,
                    "-filter_complex", "[0:a:0][0:a:1]amerge=inputs=2[a]",
                    "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    output_path, "-y"
                ]
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.video_path = output_path
            # print(self.video_path)

            self.cap = cv2.VideoCapture(self.video_path)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            total_duration = self.frame_count // self.fps

            self.start_slider.setMaximum(total_duration)
            self.end_slider.setMaximum(total_duration)

            self.progress_slider.setEnabled(True)
            self.start_slider.setEnabled(True)
            self.end_slider.setEnabled(True)
            self.trim_button.setEnabled(True)

            # setup video player
            self.player.positionChanged.connect(self.on_playback_change)
            self.player.setSource(QUrl.fromLocalFile(self.video_path))
            self.player.play()

    def on_playback_change(self, value, isReal=True):
        # self.start_label.setText(f"Start Time: {value} sec")

        if isReal:
            if value > self.end_slider.value() * 1000:
                value = self.start_slider.value() * 1000
                self.player.setPosition(value)

            self.progress_slider.setValue(value)

    def update_progress(self, value, isReal=True):
        # self.start_label.setText(f"Start Time: {value} sec")

        if isReal:
            self.player.setPosition(value)
            self.player.pause()

    def stop_update_progress(self, isReal=True):
        self.player.play()

    def update_start_time(self, value, isReal=True):
        self.start_label.setText(f"Start Time: {value} sec")
        self.progress_slider.setMinimum(value * 1000)

        if isReal:
            self.player.setPosition(value * 1000)
            if value + MIN_LENGTH > self.end_slider.value():
                self.end_slider.setValue(value + MIN_LENGTH)
                self.update_end_time(self.end_slider.value(), False)

    def update_end_time(self, value, isReal=True):
        self.end_label.setText(f"End Time: {value} sec")
        self.progress_slider.setMaximum(value * 1000)

        if isReal:
            self.player.setPosition(int((value - 1.2) * 1000))
            if value - MIN_LENGTH < self.start_slider.value():
                self.start_slider.setValue(value - MIN_LENGTH)
                self.update_start_time(self.start_slider.value(), False)

    def trim_video(self):
        if not self.video_path:
            return

        start_time = self.start_slider.value()
        end_time = self.end_slider.value()

        if start_time >= end_time:
            return  # Prevent invalid trim

        output_path = self.original_path.replace(".mp4", " - Trim.mp4")
        output_path = output_dir + '\\' + output_path.split('/')[-1]

        duration = end_time - start_time
        bitrate = (FILE_SIZE * 0.87 * 1024 * 1024 * 8) // duration
        # print(bitrate)

        self.player.pause()

        command = [
            "ffmpeg", "-y",
            "-i", self.video_path,
            "-ss", str(start_time), "-to", str(end_time),
            "-b:v", str(bitrate),
            # "-c", "copy", output_path
            "-c:v", "libx264", output_path
        ]
        subprocess.run(command)

        self.player.play()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoTrimmer()
    window.show()
    sys.exit(app.exec())
