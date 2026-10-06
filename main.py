from src.video.video_processor import VideoProcessor 
video = VideoProcessor("data/input/video.mp4")

print(video.get_info())

for frame in video.read_frames():
    frame = video.resize_frame(frame, 1280, 720)

    frame = video.crop_frame(
        frame,
        100, 50,
        1110, 650
    )
    frame = video.draw_rectangle(frame, 100, 50, 111, 65)
    frame = video.convert_color(frame, "BGR2RGB")
    if not video.show(frame):
        break

video.release()