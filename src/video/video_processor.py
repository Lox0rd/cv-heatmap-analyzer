import cv2


class VideoProcessor:
    """Обработка видео из файлов, камер и RTSP-потоков."""

    def __init__(self, video_source, buffer_size: int = 1):
        self.video_source = video_source
        self.capture = cv2.VideoCapture(video_source)

        if not self.capture.isOpened():
            raise ValueError(f"Не удалось открыть источник: {video_source}")

        # Определяем тип источника
        self.source_type = self._detect_source_type(video_source)

        # Для RTSP — уменьшаем буфер чтобы получать свежие кадры
        if self.source_type == "rtsp":
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)

    def _detect_source_type(self, source) -> str:
        """Определяет тип источника видео."""
        if isinstance(source, int):
            return "camera"
        if isinstance(source, str):
            if source.startswith(("rtsp://", "rtsps://")):
                return "rtsp"
            if source.startswith(("http://", "https://")):
                return "http_stream"
            return "file"
        return "unknown"

    def get_info(self) -> dict:
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.capture.get(cv2.CAP_PROP_FPS)

        # RTSP камеры часто отдают fps=0
        if self.source_type == "rtsp" and fps == 0:
            fps = self._measure_fps()

        info = {
            "source_type": self.source_type,
            "source": str(self.video_source),
            "width": width,
            "height": height,
            "fps": fps,
        }

        if self.source_type == "file":
            frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
            info["frame_count"] = frame_count
            info["duration"] = frame_count / fps if fps > 0 else 0
        else:
            info["frame_count"] = None
            info["duration"] = None

        return info

    def _measure_fps(self, sample_frames: int = 30) -> float:
        """Измеряет реальный FPS для RTSP-потоков."""
        import time
        start = time.time()
        count = 0

        for _ in range(sample_frames):
            ret, _ = self.capture.read()
            if ret:
                count += 1

        elapsed = time.time() - start
        return count / elapsed if elapsed > 0 else 0.0

    def read_frames(self, skip_frames: int = 0):
        """Генератор кадров с поддержкой RTSP reconnect."""
        if skip_frames < 0:
            raise ValueError("skip_frames не может быть отрицательным")

        frame_index = 0
        consecutive_failures = 0
        max_failures = 30  # Для RTSP — больше попыток

        while True:
            success, frame = self.capture.read()

            if not success:
                consecutive_failures += 1

                # Для RTSP пытаемся переподключиться
                if self.source_type == "rtsp":
                    if consecutive_failures >= max_failures:
                        print(f"[RTSP] Переподключение к {self.video_source}...")
                        self.capture.release()
                        self.capture = cv2.VideoCapture(str(self.video_source))
                        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        consecutive_failures = 0
                    continue
                else:
                    break
            else:
                consecutive_failures = 0

            if frame_index % (skip_frames + 1) == 0:
                yield frame

            frame_index += 1

    def read_single_frame(self):
        """Читает один кадр (для потоковой обработки)."""
        success, frame = self.capture.read()
        if not success:
            return None
        return frame

    def release(self):
        self.capture.release()
        cv2.destroyAllWindows()
