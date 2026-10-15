# from src.ai.vision_api import VisionAPI
# from src.video.video_processor import VideoProcessor

# vision = VisionAPI()
# # video = VideoProcessor("rtsp://localhost:8554/test")
# # video = VideoProcessor(0)
# video = VideoProcessor("data/input/video.mp4")
# info = video.get_info()
# print(video.get_info())
# #video.set_frame_position(1000)
# # writer = video.create_writer(
# #     "data/output/result.mp4",
# #     1010,
# #     600,
# #     info["fps"]
# # )
# for frame in video.read_frames(skip_frames=2):
#     # frame = video.resize_frame(frame, 1280, 720)
#     # print("Кадр номер:", video.get_current_frame_index())
#     #frame = video.crop_frame(
#     #     frame,
#     #     100, 50,
#     #     1110, 650
#     # )
#     # frame = video.draw_rectangle(frame, 190, 75, 300, 105)
#     # frame = video.convert_color(frame, "BGR2RGB")
#     # frame = video.draw_text(frame, "Тест", 200, 100, color=(0, 255, 0),
#     #  font_scale=1, thickness=2)
#     # frame = video.draw_line(frame, 200, 300, 220, 410)
#     # writer.write(frame)
#     if not video.show(frame):
#         break




from src.video.video_processor import VideoProcessor
from src.detection.detector import YOLODetector
from src.detection.tracker import ObjectTracker


def main():
    video = VideoProcessor(0)
    # Для RTSP можно использовать:
    # video = VideoProcessor("rtsp://localhost:8554/test")
    # Для локальной камеры:
    # video = VideoProcessor(0)

    detector = YOLODetector()
    tracker = ObjectTracker(detector)
    
    info = video.get_info()
    print("Информация о видео:", info)

    try:
        for frame in video.read_frames(skip_frames=0):
            detections = tracker.update(
                frame,
                objects=["person", "car"],
                confidence=0.5,
            )

            for obj in detections:
                x1, y1, x2, y2 = obj["bbox"]

                label = obj["label"]
                track_id = obj["track_id"]
                confidence = obj["confidence"]

                # Рисуем рамку вокруг объекта
                video.draw_rectangle(
                    frame,
                    x1, y1, x2, y2,
                    color=(0, 255, 0),
                    thickness=2,
                )

                # Подписываем класс, ID и уверенность
                text = (
                    f"{label} ID:{track_id} "
                    f"{confidence:.2f}"
                )

                video.draw_text(
                    frame,
                    text,
                    x1,
                    max(y1 - 10, 20),
                    color=(0, 255, 0),
                    font_scale=0.6,
                    thickness=2,
                )
            # Показываем обработанный кадр
            if not video.show(frame, window_name="YOLO Tracking"):
                break

    finally:
        video.release()


if __name__ == "__main__":
    main()
