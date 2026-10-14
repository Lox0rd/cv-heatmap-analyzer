
import os
import time

import cv2


class VideoProcessor:
    """Обработка видеофайлов, локальных камер, RTSP и HTTP-потоков."""

    MAX_FAILURES = 30

    def __init__(self, video_source, buffer_size: int = 1):
        self.video_source = video_source
        self.source_type = self._detect_source_type(video_source)
        self.is_camera = self.source_type == "camera"

        self.buffer_size = buffer_size
        self.consecutive_failures = 0

        self.capture = self._open_capture()

        if not self.capture.isOpened():
            self.capture.release()
            raise ValueError(
                f"Не удалось открыть источник: {video_source}"
            )

    def _detect_source_type(self, source) -> str:
        """Определяет тип источника видео."""
        if isinstance(source, int):
            return "camera"

        if isinstance(source, str):
            source = source.lower()

            if source.startswith(("rtsp://", "rtsps://")):
                return "rtsp"

            if source.startswith(("http://", "https://")):
                return "http_stream"

            return "file"

        raise ValueError(f"Неподдерживаемый источник: {source}")

    def _open_capture(self):
        """Открывает источник видео с нужными настройками."""
        capture = cv2.VideoCapture(self.video_source)

        if self.source_type in ("rtsp", "http_stream"):
            capture.set(
                cv2.CAP_PROP_BUFFERSIZE,
                self.buffer_size
            )

        return capture

    def _reconnect(self) -> bool:
        """Пытается заново подключиться к сетевому потоку."""
        print(f"[{self.source_type.upper()}] Переподключение...")

        self.capture.release()
        time.sleep(1)

        self.capture = self._open_capture()
        self.consecutive_failures = 0

        if self.capture.isOpened():
            print(f"[{self.source_type.upper()}] Подключение восстановлено")
            return True

        print(f"[{self.source_type.upper()}] Не удалось подключиться")
        return False

    def _read_frame(self):
        """Читает кадр и обрабатывает потерю соединения."""
        success, frame = self.capture.read()

        if success:
            self.consecutive_failures = 0
            return frame

        if self.source_type in ("rtsp", "http_stream"):
            self.consecutive_failures += 1

            if self.consecutive_failures >= self.MAX_FAILURES:
                self._reconnect()

        return None

    def get_info(self) -> dict:
        """Возвращает информацию об источнике видео."""
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.capture.get(cv2.CAP_PROP_FPS)

        is_stream = self.source_type in ("rtsp", "http_stream")

        info = {
            "source": (
                "camera" if self.is_camera
                else "video" if self.source_type == "file"
                else self.source_type
            ),
            "source_type": self.source_type,
            "source_value": str(self.video_source),
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": None,
            "duration": None,
        }

        if self.source_type == "file":
            frame_count = int(
                self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )

            info["frame_count"] = frame_count
            info["duration"] = frame_count / fps if fps > 0 else 0

        return info

    def read_frames(self, skip_frames: int = 0):
        """Генератор кадров с поддержкой сетевых переподключений."""
        if skip_frames < 0:
            raise ValueError("skip_frames не может быть отрицательным")

        frame_index = 0

        while True:
            frame = self._read_frame()

            if frame is None:
                if self.source_type in ("rtsp", "http_stream"):
                    continue

                break

            if frame_index % (skip_frames + 1) == 0:
                yield frame

            frame_index += 1

    def read_single_frame(self):
        """Читает один кадр. Если чтение не удалось, возвращает None."""
        return self._read_frame()

    def set_frame_position(self, frame_index: int):
        """Устанавливает позицию в видеофайле."""
        if frame_index < 0:
            raise ValueError("Номер кадра не может быть отрицательным")

        if self.source_type != "file":
            raise ValueError(
                "Перемещение по кадрам доступно только для видеофайлов"
            )

        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

    def get_current_frame_index(self) -> int:
        return int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))

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
        thickness: int = 2,
    ):
        return cv2.rectangle(
            frame, (x1, y1), (x2, y2), color, thickness
        )

    def draw_text(
        self,
        frame,
        text: str,
        x: int,
        y: int,
        color: tuple = (0, 255, 0),
        font_scale: float = 0.7,
        thickness: int = 2,
    ):
        return cv2.putText(
            frame,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
        )

    def draw_line(
        self,
        frame,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple = (255, 0, 0),
        thickness: int = 2,
    ):
        return cv2.line(
            frame, (x1, y1), (x2, y2), color, thickness
        )

    def show(self, frame, window_name: str = "Video"):
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            return False

        return True

    def create_writer(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: float,
    ):
        output_dir = os.path.dirname(output_path)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        writer = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():
            writer.release()
            raise ValueError(
                f"Не удалось создать видео: {output_path}"
            )

        return writer

    def release(self):
        self.capture.release()
        cv2.destroyAllWindows()
