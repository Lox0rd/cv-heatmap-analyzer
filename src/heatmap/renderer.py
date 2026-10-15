import cv2
import numpy as np


class HeatmapRenderer:
    def render(self, heatmap):
        """Преобразует матрицу в цветную тепловую карту."""
        blurred = cv2.GaussianBlur(
            heatmap,
            (0, 0),
            sigmaX=15,
            sigmaY=15,
        )

        maximum = blurred.max()

        if maximum > 0:
            normalized = (
                blurred / maximum * 255
            ).astype(np.uint8)
        else:
            normalized = np.zeros(
                heatmap.shape,
                dtype=np.uint8,
            )

        return cv2.applyColorMap(
            normalized,
            cv2.COLORMAP_JET,
        )

    def overlay(self, frame, heatmap, alpha=0.5):
        """Накладывает тепловую карту на кадр."""
        heatmap_image = self.render(heatmap)

        return cv2.addWeighted(
            frame,
            1 - alpha,
            heatmap_image,
            alpha,
            0,
        )

    def save(self, heatmap, output_path):
        """Сохраняет цветную тепловую карту."""
        image = self.render(heatmap)

        if not cv2.imwrite(output_path, image):
            raise IOError(
                f"Не удалось сохранить тепловую карту: {output_path}"
            )