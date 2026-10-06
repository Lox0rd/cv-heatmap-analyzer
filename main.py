from src.video.video_processor import VideoProcessor 
import cv2

video = VideoProcessor("data/input/video.mp4")

print(video.get_info())

for frame in video.read_frames():
    frame = video.resize_frame(frame, 1280, 720)

    frame = video.crop_frame(
        frame,
        100, 50,
        1110, 650
    )
    frame = video.convert_color(frame, cv2.COLOR_BGR2RGB)
    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video.release()