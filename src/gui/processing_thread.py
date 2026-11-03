# src/gui/processing_thread.py
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from src.detection.detector import YOLODetector
from src.detection.tracker import ObjectTracker
from src.heatmap.generator import HeatmapGenerator
from src.heatmap.renderer import HeatmapRenderer
from src.video.video_processor import VideoProcessor

COLORMAPS = {
    "Jet": cv2.COLORMAP_JET,
    "Hot": cv2.COLORMAP_HOT,
    "Cool": cv2.COLORMAP_COOL,
    "Rainbow": cv2.COLORMAP_RAINBOW,
    "Ocean": cv2.COLORMAP_OCEAN,
    "Viridis": cv2.COLORMAP_VIRIDIS,
    "Inferno": cv2.COLORMAP_INFERNO,
    "Magma": cv2.COLORMAP_MAGMA,
    "Plasma": cv2.COLORMAP_PLASMA,
    "Spring": cv2.COLORMAP_SPRING,
    "Summer": cv2.COLORMAP_SUMMER,
    "Autumn": cv2.COLORMAP_AUTUMN,
    "Winter": cv2.COLORMAP_WINTER,
}


class ProcessingThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    status_update = pyqtSignal(str)
    frame_position_changed = pyqtSignal(int)
    total_frames_changed = pyqtSignal(int)
    is_file_source = pyqtSignal(bool)
    finished = pyqtSignal()

    def __init__(
        self,
        sources: list,
        confidence: float,
        alpha: float,
        skip_frames: int,
        colormap_name: str = "Jet",
        show_detections: bool = True,
        show_heatmap: bool = True,
        selected_objects: list | None = None,
    ):
        super().__init__()
        self.sources = sources
        self.confidence = confidence
        self.alpha = alpha
        self.skip_frames = skip_frames
        self.colormap_name = colormap_name
        self.show_detections = show_detections
        self.show_heatmap = show_heatmap
        self.selected_objects = selected_objects

        self._is_running = True
        self._seek_position = None  # Позиция для перемотки
        self.video = None

    def run(self):
        try:
            self.status_update.emit("Попытка открытия источника видео...")
            self.video = VideoProcessor.open_source(self.sources)

            info = self.video.get_info()
            self.status_update.emit(
                f"✓ Видео: {info['source_value']} "
                f"({info['width']}x{info['height']} @ {info['fps']} FPS)"
            )

            self.is_file_source.emit(info["source_type"] == "file")

            if info["frame_count"] is not None:
                self.total_frames_changed.emit(info["frame_count"])

            self.status_update.emit("Загрузка модели YOLO...")
            detector = YOLODetector()
            tracker = ObjectTracker(detector)

            heatmap_generator = HeatmapGenerator(
                width=info["width"], height=info["height"]
            )
            heatmap_renderer = HeatmapRenderer()

            colormap = COLORMAPS.get(self.colormap_name, cv2.COLORMAP_JET)

            self.status_update.emit("▶ Начало обработки...")

            frame_count = 0
            start_time = time.time()
            last_fps_update = start_time

            for frame in self.video.read_frames(skip_frames=self.skip_frames):
                if not self._is_running:
                    break

                # Проверяем, нужна ли перемотка
                if self._seek_position is not None:
                    target_frame = self._seek_position
                    self._seek_position = None
                    self.status_update.emit(f"Перемотка на кадр {target_frame}...")
                    self.video.set_frame_position(target_frame)
                    continue  # Пропускаем текущий кадр, читаем новый

                frame_count += 1
                background_frame = frame.copy()

                # Отправляем текущую позицию кадра в GUI
                current_pos = self.video.get_current_frame_index()
                self.frame_position_changed.emit(current_pos)

                # Обновляем FPS в статусе
                current_time = time.time()
                if current_time - last_fps_update >= 1.0:
                    fps = frame_count / (current_time - start_time)
                    self.status_update.emit(
                        f"Кадр {current_pos} | {fps:.1f} FPS"
                    )
                    last_fps_update = current_time

                # Детекция и трекинг
                detections = tracker.update(
                    frame,
                    objects=self.selected_objects,
                    confidence=self.confidence,
                )
                heatmap_generator.update(detections)

                # Отрисовка детекций (если включено)
                if self.show_detections:
                    for obj in detections:
                        x1, y1, x2, y2 = obj["bbox"]
                        text = f"{obj['label']} ID:{obj['track_id']} {obj['confidence']
                                                                      :.2f}"
                        self.video.draw_rectangle(
                            frame, x1, y1, x2, y2,
                            color=(0, 255, 0), thickness=2
                        )
                        self.video.draw_text(
                            frame, text, x1, max(y1 - 10, 20),
                            color=(0, 255, 0), font_scale=0.6, thickness=2
                        )

                # Формируем итоговый кадр
                if self.show_heatmap and self.show_detections:
                    display_frame = heatmap_renderer.overlay(
                        frame, heatmap_generator.get_heatmap(),
                        alpha=self.alpha, colormap=colormap
                    )
                elif self.show_heatmap:
                    display_frame = heatmap_renderer.overlay(
                        frame, heatmap_generator.get_heatmap(),
                        alpha=1.0, colormap=colormap
                    )
                else:
                    display_frame = frame.copy()

                self.frame_ready.emit(display_frame)

            total_time = time.time() - start_time
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.status_update.emit(
                f"✓ Обработано {frame_count} кадров за {total_time:.1f}с "
                f"({avg_fps:.1f} FPS). Сохранение..."
            )
            output_frame = heatmap_renderer.overlay(
                background_frame,
                heatmap_generator.get_heatmap(),
                alpha=self.alpha,
                colormap=colormap,
            )
            if not cv2.imwrite("data/output/heatmap.jpg", output_frame):
                raise IOError("Не удалось сохранить результат анализа")
            self.status_update.emit("✓ Тепловая карта сохранена в data/output/" \
            "heatmap.jpg")
            self.finished.emit()

        except Exception as e:
            error_msg = str(e)
            self.status_update.emit(f"✗ Критическая ошибка: {error_msg}")
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            self.finished.emit()

        finally:
            if self.video:
                self.video.release()

    def seek(self, frame_index: int):
        """Устанавливает позицию для перемотки (будет выполнена в следующем цикле)."""
        self._seek_position = frame_index
        print(f"[DEBUG] Seek requested to frame {frame_index}")

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait()
