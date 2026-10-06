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
    

    def show(self, frame, window_name: str = "Video"):
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            return False

        return True

    def release(self):
        self.capture.release()
        cv2.destroyAllWindows()