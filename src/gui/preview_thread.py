import threading

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class VideoPreviewThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    position_changed = pyqtSignal(int)
    total_frames_changed = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    playback_finished = pyqtSignal()

    def __init__(self, video_path, start_frame=0, parent=None):
        super().__init__(parent)

        self.video_path = video_path
        self.start_frame = max(0, start_frame)

        self._lock = threading.Lock()
        self._playing = True
        self._pending_seek = None

    
    def run(self):
        capture = None

        try:
            # Создаём захват внутри try, чтобы перехватить исключения OpenCV.
            capture = cv2.VideoCapture(self.video_path)

            if not capture.isOpened():
                self.error_occurred.emit(
                    f"Не удалось открыть видео: {self.video_path}"
                )
                return

            fps = capture.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0

            total_frames = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )
            self.total_frames_changed.emit(total_frames)

            if total_frames > 0:
                self.start_frame = min(
                    self.start_frame,
                    total_frames - 1,
                )

            if self.start_frame > 0:
                capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    self.start_frame,
                )

            while not self.isInterruptionRequested():
                with self._lock:
                    seek_to = self._pending_seek
                    self._pending_seek = None
                    playing = self._playing

                # Перемотка доступна даже во время паузы.
                if seek_to is not None:
                    if total_frames > 0:
                        seek_to = min(
                            seek_to,
                            total_frames - 1,
                        )

                    capture.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        seek_to,
                    )

                    success, frame = capture.read()

                    if success:
                        self.frame_ready.emit(frame)

                        actual_position = max(
                            0,
                            int(
                                capture.get(
                                    cv2.CAP_PROP_POS_FRAMES
                                )
                            ) - 1,
                        )
                        self.position_changed.emit(actual_position)

                    continue

                if not playing:
                    self.msleep(30)
                    continue

                success, frame = capture.read()

                if not success:
                    with self._lock:
                        self._playing = False

                    self.playback_finished.emit()
                    break

                position = max(
                    0,
                    int(
                        capture.get(cv2.CAP_PROP_POS_FRAMES)
                    ) - 1,
                )

                self.frame_ready.emit(frame)
                self.position_changed.emit(position)

                self.msleep(max(1, int(1000 / fps)))

        except Exception as error:
            self.error_occurred.emit(
                f"Ошибка предпросмотра: {error}"
            )

        finally:
            if capture is not None:
                try:
                    capture.release()
                except Exception:
                    pass

    def toggle_playback(self):
        with self._lock:
            self._playing = not self._playing
            return self._playing

    def seek(self, frame_index):
        with self._lock:
            self._pending_seek = max(0, frame_index)

    def stop(self):
        self.requestInterruption()
        self.wait()
