import sys
import cv2
import subprocess
import os.path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QSlider, QFileDialog
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QTimer, QUrl
import re

# constants
SETTINGS = {
    'INPUT_DIR': '.\\input',
    'OUTPUT_DIR': '.\\output',
    'TEMP_DIR': '.\\temp',
    'FILE_SIZE': 10
}

# non configurable constants
FFMPEG = 'ffmpeg.exe'
SETTINGS_DIR = '.\\settings.txt'
MIN_LENGTH = 3  # seconds

class VideoTrimmer(QWidget):
    def __init__(self):
        super().__init__()
        self.original_path = None
        self.video_path = None
        self.audio_path = None
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
        self.audio_player = QMediaPlayer(self)
        self.audio_player.setAudioOutput(self.audio_output)
        # self.player.setAudioOutput(self.audio_output)

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
        vid_path, _ = file_dialog.getOpenFileName(self, "Select Video", SETTINGS.get('INPUT_DIR'), "Videos (*.mp4 *.avi *.mov *.*)")

        if vid_path:
            self.video_path = vid_path
            self.original_path = self.video_path
            self.video_extension = os.path.basename(self.video_path).split('.')[-1]
            vf_name = '.'.join(os.path.basename(self.video_path).split('.')[:-1])
            self.video_name = vf_name
            # output_path = os.path.abspath(os.path.join(SETTINGS.get('TEMP_DIR'), vf_name + '.aac'))
            output_path = os.path.abspath(os.path.join(SETTINGS.get('TEMP_DIR'), vf_name + f'_merged_audio.{self.video_extension}'))

            # print(output_path)
            # exit(0)

            probe = subprocess.run([
                FFMPEG, "-i", self.video_path
            ], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            # num_audio_tracks = len(re.findall(r'Stream #0:\d+: Audio:', probe.stderr))
            num_audio_tracks = len(re.findall(r'Stream #0:\d+(?:\([^\)]*\))?: Audio:', probe.stderr))
            inputs = ''.join(f'[0:a:{i}]' for i in range(num_audio_tracks))

            self.n_audio_tracks = num_audio_tracks
            self.audio_input_str = inputs

            # Merge audio tracks using FFmpeg
            if not os.path.exists(output_path):
                print('file not opened before, generating audio...')

                command = [
                    FFMPEG, "-i", self.video_path,
                    # "-filter_complex", "[0:a:0][0:a:1]amerge=inputs=2[a]",
                    "-filter_complex", f"{inputs}amix=inputs={num_audio_tracks}:duration=longest[a]",
                    # "-map", "[a]",
                    # "-c:a", "aac", "-b:a", "192k",
                    # "-map", "0:v",
                    "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    output_path, "-y"
                ]
                # subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(command)
            self.video_path = self.original_path
            self.audio_path = output_path
            # self.video_path = output_path
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
            self.audio_player.setSource(QUrl.fromLocalFile(self.audio_path))
            self.play()

    def pause(self):
        self.audio_player.pause()
        self.player.pause()

    def play(self):
        self.audio_player.play()
        self.player.play()

    def setPosition(self, value):
        self.audio_player.setPosition(value)
        self.player.setPosition(value)

    def on_playback_change(self, value, isReal=True):
        # self.start_label.setText(f"Start Time: {value} sec")

        if isReal:
            if value > self.end_slider.value() * 1000:
                value = self.start_slider.value() * 1000
                self.setPosition(value)

            self.progress_slider.setValue(value)

    def update_progress(self, value, isReal=True):
        # self.start_label.setText(f"Start Time: {value} sec")

        if isReal:
            self.setPosition(value)
            self.pause()

    def stop_update_progress(self, isReal=True):
        self.play()

    def update_start_time(self, value, isReal=True):
        self.start_label.setText(f"Start Time: {value} sec")
        self.progress_slider.setMinimum(value * 1000)

        if isReal:
            self.setPosition(value * 1000)
            if value + MIN_LENGTH > self.end_slider.value():
                self.end_slider.setValue(value + MIN_LENGTH)
                self.update_end_time(self.end_slider.value(), False)

    def update_end_time(self, value, isReal=True):
        self.end_label.setText(f"End Time: {value} sec")
        self.progress_slider.setMaximum(value * 1000)

        if isReal:
            self.setPosition(int((value - 1.2) * 1000))
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

        # output_path = self.original_path.replace(".mp4", " - Trim.mp4")
        output_path = self.video_name + f' - Trim.{self.video_extension}'
        output_path = os.path.join(SETTINGS.get('OUTPUT_DIR'), output_path.split('/')[-1])
        # output_path = SETTINGS.get('OUTPUT_DIR') + '\\' + output_path.split('/')[-1]

        duration = end_time - start_time
        bitrate = (SETTINGS.get('FILE_SIZE') * 0.87 * 1024 * 1024 * 8) // duration
        # print(bitrate)

        self.pause()

        command = [
            FFMPEG, "-y",
            "-i", self.original_path,
            "-ss", str(start_time), "-to", str(end_time),
            # "-filter_complex", "[0:a:0][0:a:1]amerge=inputs=2[a]",
            "-filter_complex", f"{self.audio_input_str}amix=inputs={self.n_audio_tracks}:duration=longest[a]",
            "-ac", "2",
            "-map", "[a]",
            "-map", "0:v:0",
            "-b:v", str(bitrate),
            "-c:v", "libx264", output_path
        ]
        subprocess.run(command)

        self.play()

if __name__ == "__main__":
    # verify required folders and files exist

    # settings file
    if not os.path.exists(SETTINGS_DIR):
        # first time set up

        # create the default dirs
        if not os.path.exists(SETTINGS.get('INPUT_DIR')):
            os.mkdir(SETTINGS.get('INPUT_DIR'))

        if not os.path.exists(SETTINGS.get('OUTPUT_DIR')):
            os.mkdir(SETTINGS.get('OUTPUT_DIR'))

        if not os.path.exists(SETTINGS.get('TEMP_DIR')):
            os.mkdir(SETTINGS.get('TEMP_DIR'))

        # create the settings file
        with open(SETTINGS_DIR, mode='w') as f:
            for s,v in SETTINGS.items():
                f.write(f'{s}={v}\n')
    else:
        # read settings
        with open(SETTINGS_DIR, mode='r') as f:
            for l in f.readlines():
                try:
                    key,val = l.strip().split('=')
                    try:
                        val = int(val)
                    except:
                        pass

                    SETTINGS[key] = val
                except:
                    print(f'error reading settings line: {l.strip()}')


    app = QApplication(sys.argv)
    window = VideoTrimmer()
    window.show()
    sys.exit(app.exec())
