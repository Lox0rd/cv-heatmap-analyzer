import os
import time
import threading
import queue

import cv2


class VideoProcessor:
    """Обработка видеофайлов, локальных камер, RTSP и HTTP-потоков."""

    MAX_FAILURES = 30
    
    @staticmethod
    def open_source(sources: list, buffer_size: int = 1):
        last_error = None
        
        for source in sources:
            try:
                print(f"[INFO] Проверка источника: {source}")
                return VideoProcessor(source, buffer_size)
            except ValueError as e:
                print(f"[WARN] Пропуск: {e}")
                last_error = e
                
        # Если ни один источник не сработал
        raise RuntimeError(f"Не удалось открыть ни один из источников. Последняя ошибка: {last_error}")
        
    def __init__(self, video_source, buffer_size: int = 1):
        self.video_source = video_source
        self.source_type = self._detect_source_type(video_source)
        self.is_camera = self.source_type == "camera"

        self.buffer_size = buffer_size
        self.consecutive_failures = 0

        # 1. Сначала открываем камеру
        self.capture = self._open_capture()

        if not self.capture.isOpened():
            self.capture.release()
            raise ValueError(
                f"Не удалось открыть источник: {video_source}"
            )

        # 2. Инициализируем многопоточность
        self.q = queue.Queue(maxsize=2)
        self.running = True
        self.capture_lock = threading.Lock()
        self.thread = threading.Thread(
            target=self._reader_worker, 
            daemon=True
        )
        self.thread.start()

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
            # Дополнительно для низкой задержки FFmpeg
            capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

        return capture

        
    def _reader_worker(self):
        """Фоновый поток чтения кадров."""
        while self.running:
            # Чтение кадра и помещение в очередь защищены
            # одной блокировкой, чтобы перемотка не конфликтовала с чтением.
            with self.capture_lock:
                success, frame = self.capture.read()

                if success:
                    self.consecutive_failures = 0

                    if self.source_type == "file":
                        # Не теряем кадры локального видео.
                        while self.running:
                            try:
                                self.q.put(frame, timeout=0.1)
                                break
                            except queue.Full:
                                continue
                    else:
                        # Для потоков оставляем только свежие кадры.
                        try:
                            if self.q.full():
                                self.q.get_nowait()

                            self.q.put_nowait(frame)
                        except queue.Empty:
                            pass
                        except queue.Full:
                            pass

            if not success:
                if self.source_type in ("rtsp", "http_stream"):
                    self.consecutive_failures += 1

                    if self.consecutive_failures >= self.MAX_FAILURES:
                        self._reconnect()
                else:
                    # Локальный файл закончился.
                    break

                time.sleep(0.1)


    def _reconnect(self) -> bool:
        """Пытается заново подключиться к сетевому потоку."""
        print(f"[{self.source_type.upper()}] Переподключение...")

        self.capture.release()
        time.sleep(1)

        self.capture = self._open_capture()

        if self.capture.isOpened():
            self.consecutive_failures = 0
            print(f"[{self.source_type.upper()}] Подключение восстановлено")
            return True

        print(f"[{self.source_type.upper()}] Не удалось подключиться")
        return False

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
            "is_stream": is_stream,
            "width": width if width > 0 else 1920,
            "height": height if height > 0 else 1080,
            "fps": fps if fps > 0 else 30.0,
            "frame_count": None,
            "duration": None,
        }

        if self.source_type == "file":
            frame_count = int(
                self.capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )

            info["frame_count"] = frame_count
            info["duration"] = frame_count / info["fps"] if info["fps"] > 0 else 0

        return info

    def read_frames(self, skip_frames: int = 0):
        """Генератор кадров, который берет данные из многопоточной очереди."""
        if skip_frames < 0:
            raise ValueError("skip_frames не может быть отрицательным")

        frame_index = 0

        while self.running:
            try:
                # Ждем кадр из очереди с таймаутом, чтобы цикл не завис намертво
                frame = self.q.get(timeout=2.0)
            except queue.Empty:
                if self.source_type in ("rtsp", "http_stream"):
                    print("[WARNING] Очередь пуста, ожидание восстановления потока...")
                    continue
                else:
                    break

            if frame is None:
                continue

            if frame_index % (skip_frames + 1) == 0:
                yield frame

            frame_index += 1

    def read_single_frame(self):
        """Читает один кадр из очереди. Если очередь пуста, возвращает None."""
        try:
            return self.q.get_nowait()
        except queue.Empty:
            return None


    def set_frame_position(self, frame_index: int):
        """Перематывает локальный видеофайл на указанный кадр."""
        if frame_index < 0:
            raise ValueError(
                "Номер кадра не может быть отрицательным"
            )

        if self.source_type != "file":
            raise ValueError(
                "Перемотка доступна только для видеофайлов"
            )

        with self.capture_lock:
            # Удаляем кадры, прочитанные до перемотки.
            while True:
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break

            # Перемещаем указатель чтения.
            success = self.capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                frame_index
            )

            if not success:
                raise RuntimeError(
                    f"Не удалось перейти к кадру {frame_index}"
                )


    def get_current_frame_index(self) -> int:
        """Возвращает текущую позицию указателя чтения (актуально для файлов)."""
        if self.source_type != "file":
            return 0
            
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
        self.running = False
        
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
        if hasattr(self, 'capture') and self.capture.isOpened():
            self.capture.release()
            
        cv2.destroyAllWindows()