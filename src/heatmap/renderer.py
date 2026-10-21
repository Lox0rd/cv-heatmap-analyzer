# src/heatmap/renderer.py
import cv2
import numpy as np

from src.config.settings import HEATMAP_ALPHA, HEATMAP_BLUR_SIGMA


class HeatmapRenderer:
    def render(self, heatmap, colormap=cv2.COLORMAP_JET):
        """Преобразует матрицу в цветную тепловую карту."""
        blurred = cv2.GaussianBlur(
            heatmap,
            (0, 0),
            sigmaX=HEATMAP_BLUR_SIGMA,
            sigmaY=HEATMAP_BLUR_SIGMA,
        )

        maximum = blurred.max()

        if maximum > 0:
            normalized = (blurred / maximum * 255).astype(np.uint8)
        else:
            normalized = np.zeros(heatmap.shape, dtype=np.uint8)

        return cv2.applyColorMap(normalized, colormap)

    def overlay(self, frame, heatmap, alpha=HEATMAP_ALPHA, colormap=cv2.COLORMAP_JET):
        """Накладывает тепловую карту на кадр."""
        heatmap_image = self.render(heatmap, colormap)

        if frame.shape[:2] != heatmap.shape[:2]:
            heatmap_image = cv2.resize(
                heatmap_image, (frame.shape[1], frame.shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )

        return cv2.addWeighted(frame, 1 - alpha, heatmap_image, alpha, 0)

    def save(self, heatmap, output_path, colormap=cv2.COLORMAP_JET):
        """Сохраняет цветную тепловую карту."""
        image = self.render(heatmap, colormap)
        if not cv2.imwrite(output_path, image):
            raise IOError(f"Не удалось сохранить тепловую карту: {output_path}")
