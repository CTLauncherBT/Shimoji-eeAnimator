import sys, os, subprocess, zipfile, uuid, shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QSpinBox, QGroupBox, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(JOBS_DIR, exist_ok=True)

class MP4AnimatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shimoji-ee Playground - FPF Animator")
        self.setMinimumSize(900, 600)

        self.videos = {"BackgroundAnim": [], "TopAnim": [], "BottomAnim": [], "LeftAnim": [], "RightAnim": []}

        main_layout = QVBoxLayout()

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_input = QSpinBox()
        self.fps_input.setMinimum(1)
        self.fps_input.setValue(12)
        fps_layout.addWidget(self.fps_input)
        main_layout.addLayout(fps_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        self.scroll_layout = QVBoxLayout(scroll_content)
        main_layout.addWidget(scroll)

        for layer in self.videos.keys():
            box = QGroupBox(f"{layer} (optional)")
            layout = QVBoxLayout()
            btn_select = QPushButton(f"Select video(s) for {layer}")
            btn_select.clicked.connect(lambda checked, l=layer: self.select_videos(l))
            layout.addWidget(btn_select)
            label = QLabel("No videos selected")
            layout.addWidget(label)
            box.setLayout(layout)
            box.label = label
            self.scroll_layout.addWidget(box)

        self.btn_convert = QPushButton("Convert and Save ZIP")
        self.btn_convert.clicked.connect(self.convert)
        main_layout.addWidget(self.btn_convert)

        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def select_videos(self, layer):
        files, _ = QFileDialog.getOpenFileNames(self, f"Select video(s) for {layer}", "", "Video (*.mp4)")
        if files:
            self.videos[layer] = files
            for i in range(self.scroll_layout.count()):
                box = self.scroll_layout.itemAt(i).widget()
                if box.title().startswith(layer):
                    box.label.setText(f"{len(files)} video(s) selected")

    def convert(self):
        if os.path.exists(JOBS_DIR):
            try:
                shutil.rmtree(JOBS_DIR)
            except Exception as e:
                print(f"[WARN] Could not clear old cache: {e}")
        os.makedirs(JOBS_DIR, exist_ok=True)
        
        fps = self.fps_input.value()
        if not any(self.videos.values()):
            QMessageBox.warning(self, "No videos", "Please select at least one video")
            return

        job_id = str(uuid.uuid4())
        workdir = os.path.join(JOBS_DIR, job_id)
        os.makedirs(workdir, exist_ok=True)

        frame_dict = {layer: [] for layer in self.videos}

        self.status_label.setText("⏳ Extracting frames...")
        QApplication.processEvents()

        for layer, paths in self.videos.items():
            if not paths:
                continue
            layer_dir = os.path.join(workdir, layer.lower())
            os.makedirs(layer_dir, exist_ok=True)
            for video in paths:
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", video,
                        "-vf", f"fps={fps}",
                        os.path.join(layer_dir, "frame_%05d.png")
                    ], check=True)
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(self, "FFmpeg Error", str(e))
                    shutil.rmtree(workdir, ignore_errors=True)
                    return
            frames = sorted(os.listdir(layer_dir))
            frames = [os.path.join(layer_dir, f) for f in frames if f.endswith(".png")]
            frame_dict[layer].extend(frames)

        total_frames = max(len(frames) for frames in frame_dict.values() if frames)

        zip_path, _ = QFileDialog.getSaveFileName(self, "Save ZIP as", "animation.zip", "ZIP (*.zip)")
        if not zip_path:
            shutil.rmtree(workdir, ignore_errors=True)
            return

        sec = round(1 / fps, 6)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            anim_txt = ""
            for i in range(total_frames):
                anim_txt += f"sec_{sec}\n"
                for layer, frames in frame_dict.items():
                    if i < len(frames):
                        fname = os.path.basename(frames[i])
                        rel_path = f"assets/{layer.lower()}/{fname}"
                        zf.write(frames[i], rel_path)
                        anim_txt += f"{layer}={rel_path}\n"
                anim_txt += "\n"
            zf.writestr("animation.txt", anim_txt.strip() + "\n")

        shutil.rmtree(workdir, ignore_errors=True)
        self.status_label.setText(f"Done! ZIP saved at: {zip_path}")
        QMessageBox.information(self, "Finished!", f"ZIP successfully created!\n{zip_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MP4AnimatorApp()
    win.show()
    sys.exit(app.exec())