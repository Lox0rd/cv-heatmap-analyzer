import cv2


class VideoProcessor:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.capture = cv2.VideoCapture(video_path)

        if not self.capture.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")

    def get_info(self) -> dict:
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))

        duration = frame_count / fps if fps > 0 else 0

        return {
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
        }

    def read_frames(self):
        while True:
            success, frame = self.capture.read()

            if not success:
                break

            yield frame

    def show(self, window_name: str = "Video"):
        for frame in self.read_frames():
            cv2.imshow(window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    def release(self):
        self.capture.release()
        cv2.destroyAllWindows()