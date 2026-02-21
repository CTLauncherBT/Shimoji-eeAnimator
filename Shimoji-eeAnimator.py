# -*- coding: utf-8 -*-
import sys, os, subprocess, zipfile, uuid, shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QSpinBox, QHBoxLayout, QRadioButton, QButtonGroup, QMessageBox
)
from PySide6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_DIR = os.path.join(BASE_DIR, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)

class MP4ToFramesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP4 to Shimoji-ee Animation")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        self.label_video = QLabel("No video selected")
        layout.addWidget(self.label_video)

        self.btn_select_video = QPushButton("Select video (.mp4 recommended)")
        self.btn_select_video.clicked.connect(self.select_video)
        layout.addWidget(self.btn_select_video)

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_input = QSpinBox()
        self.fps_input.setMinimum(1)
        self.fps_input.setValue(12)
        fps_layout.addWidget(self.fps_input)
        layout.addLayout(fps_layout)

        layout.addWidget(QLabel("Animation typ:"))
        self.anim_group = QButtonGroup()
        anim_layout = QVBoxLayout()
        for name in ["BackgroundAnim", "TopAnim", "LeftAnim", "RightAnim"]:
            rb = QRadioButton(name)
            if name == "BackgroundAnim": rb.setChecked(True)
            self.anim_group.addButton(rb)
            anim_layout.addWidget(rb)
        layout.addLayout(anim_layout)

        self.btn_convert = QPushButton("Convert and save")
        self.btn_convert.clicked.connect(self.convert)
        layout.addWidget(self.btn_convert)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.video_path = None

    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "MP4 auswählen", "", "Video (*.mp4)")
        if file_path:
            self.video_path = file_path
            self.label_video.setText(f"{os.path.basename(file_path)} selected")

    def convert(self):
        if not self.video_path:
            QMessageBox.warning(self, "Error", "Please select a video")
            return

        fps = self.fps_input.value()
        anim_type = self.anim_group.checkedButton().text()

        job_id = str(uuid.uuid4())
        workdir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(workdir, exist_ok=True)

        input_path = os.path.join(workdir, "input.mp4")
        shutil.copy(self.video_path, input_path)

        self.status_label.setText("Frames extracting...")
        QApplication.processEvents()

        # FFmpeg Frame Extraktion
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", input_path,
                "-vf", f"fps={fps}",
                os.path.join(workdir, "frame_%05d.png")
            ], check=True)
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"FFmpeg Error:\n{e}")
            shutil.rmtree(workdir, ignore_errors=True)
            return

        self.status_label.setText("create .zip...")
        QApplication.processEvents()

        zip_path, _ = QFileDialog.getSaveFileName(self, "ZIP speichern als", "animation.zip", "ZIP (*.zip)")
        if not zip_path:
            shutil.rmtree(workdir, ignore_errors=True)
            return

        sec = round(1 / fps, 6)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            anim_txt = ""
            for f in sorted(os.listdir(workdir)):
                if f.startswith("frame_") and f.endswith(".png"):
                    absf = os.path.join(workdir, f)
                    rel = f"assets/main/{f}"
                    zf.write(absf, rel)
                    anim_txt += f"sec_{sec}\n{anim_type}={rel}\n\n"
            zf.writestr("animation.txt", anim_txt.strip() + "\n")

        shutil.rmtree(workdir, ignore_errors=True)
        self.status_label.setText(f"Ready! Saved the .zip in: {zip_path}")
        QMessageBox.information(self, "Finished!", f".zip successfully created!\n{zip_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MP4ToFramesApp()
    win.show()
    sys.exit(app.exec())
