import cv2
import time
import os
class VideoProcessor:
    """Обработка видео из файлов, камер и RTSP-потоков."""

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
    def _measure_fps(self, sample_frames: int = 30) -> float:
        """Измеряет реальный FPS для RTSP-потоков."""
        start = time.time()
        count = 0

        for _ in range(sample_frames):
            ret, _ = self.capture.read()
            if ret:
                count += 1

        elapsed = time.time() - start
        return count / elapsed if elapsed > 0 else 0.0
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
        
	def set_frame_position(self, frame_index: int):
        if frame_index < 0:
            raise ValueError("Номер кадра не может быть отрицательным")

        self.capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            frame_index
        )
    

    def get_current_frame_index(self) -> int:
        return int(
            self.capture.get(cv2.CAP_PROP_POS_FRAMES)
        )

    def resize_frame(self, frame, width: int, height: int):
        return cv2.resize(frame, (width, height))
    
    def crop_frame(self, frame, x1: int, y1: int, x2: int, y2: int):
        return frame[y1:y2, x1:x2]

    def convert_color(self, frame, conversion_code: str):
        conversions = {
            "BGR2RGB": cv2.COLOR_BGR2RGB,
            "BGR2GRAY": cv2.COLOR_BGR2GRAY,
            "BGR2HSV": cv2.COLOR_BGR2HSV,
            "RGB2BGR": cv2.COLOR_RGB2BGR,
        }

        if conversion_code not in conversions:
            raise ValueError(
                f"Неизвестный тип преобразования: {conversion_code}"
            )

        return cv2.cvtColor(frame, conversions[conversion_code])

    def draw_rectangle(
        self,
        frame,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple = (0, 255, 0),
        thickness: int = 2):
            return cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                thickness
            )

    def draw_text(
        self,
        frame,
        text: str,
        x: int,
        y: int,
        color: tuple = (0, 255, 0),
        font_scale: float = 0.7,
        thickness: int = 2):
            return cv2.putText(
                frame,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                thickness
            )
    
    def draw_line(
        self,
        frame,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple = (255, 0, 0),
        thickness: int = 2):
            return cv2.line(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                thickness
            )
    

    def show(self, frame, window_name: str = "Video"):
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            return False

        return True

    def create_writer(self, output_path: str, width: int, height: int, fps: float):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
		output_dir = os.path.dirname(output_path)
		if output_dir:
			os.makedirs(output_dir, exist_ok=True)
        writer = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (width, height)
        )

        if not writer.isOpened():
            raise ValueError(
                f"Не удалось создать видео: {output_path}"
            )

        return writer
    def release(self):
        self.capture.release()
        cv2.destroyAllWindows()
