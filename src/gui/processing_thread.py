# src/gui/processing_thread.py
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from src.detection.detector import YOLODetector
from src.analysis.zone_statistics import ZoneStatistics
from src.detection.tracker import ObjectTracker
from src.heatmap.generator import HeatmapGenerator
from src.heatmap.renderer import HeatmapRenderer
from src.video.video_processor import VideoProcessor
from src.zones.zone_store import ZoneStore

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
    result_saved = pyqtSignal(str)
    statistics_saved = pyqtSignal(str)
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
        source_key: str | None = None,
        zone_store_path: Path | None = None,
        statistics_path: Path | None = None,
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
        self.source_key = source_key
        self.zone_store_path = Path(zone_store_path or "data/output/zones.json")
        self.statistics_path = Path(statistics_path or "data/output/zone_statistics.json")

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
            statistics = None
            if self.source_key:
                try:
                    zones = ZoneStore(self.zone_store_path).load(
                        self.source_key, info["width"], info["height"]
                    ).get_zones()
                except (OSError, ValueError, KeyError, TypeError) as error:
                    self.status_update.emit(f"Не удалось загрузить зоны: {error}")
                    zones = []
                statistics = ZoneStatistics(zones, info["fps"], self.source_key)

            colormap = COLORMAPS.get(self.colormap_name, cv2.COLORMAP_JET)

            self.status_update.emit("▶ Начало обработки...")

            frame_count = 0
            start_time = time.time()
            last_fps_update = start_time

            # === ADDED: Initialize tracking variables BEFORE the loop ===
            best_frame = None
            max_heat = 0.0
            # ==========================================================

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
                
                # === ADDED: Keep a clean copy of the frame for the final save ===
                current_frame_copy = frame.copy()
                # ===============================================================

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
                if statistics is not None:
                    statistics.add_frame(current_pos, detections)
                heatmap_generator.update(detections)

                # === ADDED: Calculate actual heatmap intensity (amount of "red") ===
                current_heat = np.sum(heatmap_generator.get_heatmap())
                if current_heat > max_heat:
                    max_heat = current_heat
                    best_frame = current_frame_copy
                # ==================================================================

                # Отрисовка детекций (если включено)
                if self.show_detections:
                    for obj in detections:
                        x1, y1, x2, y2 = obj["bbox"]
                        text = (
                            f"{obj['label']} ID:{obj['track_id']} "
                            f"{obj['confidence']:.2f}"
                        )
                        self.video.draw_rectangle(
                            frame, x1, y1, x2, y2,
                            color=(0, 255, 0), thickness=2
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

            # === AFTER THE LOOP ENDS === (Fixed indentation so it runs after the loop)
            total_time = time.time() - start_time
            avg_fps = frame_count / total_time if total_time > 0 else 0
            
            self.status_update.emit(
                f"✓ Обработано {frame_count} кадров за {total_time:.1f}с "
                f"({avg_fps:.1f} FPS). Сохранение результатов..."
            )

            # 1. Save the RAW heatmap (just the colors, no video frame)
            raw_heatmap_path = "data/output/heatmap_raw.jpg"
            try:
                heatmap_renderer.save(
                    heatmap_generator.get_heatmap(), 
                    raw_heatmap_path, 
                    colormap
                )
                self.status_update.emit(f"✓ Сырая тепловая карта: {raw_heatmap_path}")
            except IOError as e:
                self.status_update.emit(f"✗ Ошибка сохранения сырой карты: {e}")

            # 2. Save the OVERLAY on the "hottest" frame (most red intensity)
            final_frame = best_frame if best_frame is not None else current_frame_copy
            
            output_frame = heatmap_renderer.overlay(
                final_frame,
                heatmap_generator.get_heatmap(),
                alpha=self.alpha,
                colormap=colormap,
            )

            overlay_path = "data/output/heatmap_overlay.jpg"
            if not cv2.imwrite(overlay_path, output_frame):
                raise IOError("Не удалось сохранить результат анализа с наложением")
                
            self.status_update.emit(f"✓ Кадр с наложением: {overlay_path}")
            if statistics is not None:
                try:
                    statistics.save(self.statistics_path)
                    self.statistics_saved.emit(str(self.statistics_path))
                except OSError as error:
                    self.status_update.emit(f"Не удалось сохранить статистику: {error}")
            self.result_saved.emit(overlay_path)
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
