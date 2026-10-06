from src.video.video_processor import VideoProcessor 
# video = VideoProcessor(0)
video = VideoProcessor("data/input/video.mp4")
info = video.get_info()
print(video.get_info())
writer = video.create_writer(
    "data/output/result.mp4",
    1010,
    600,
    info["fps"]
)

for frame in video.read_frames(skip_frames=1):
    frame = video.resize_frame(frame, 1280, 720)

    frame = video.crop_frame(
        frame,
        100, 50,
        1110, 650
    )
    frame = video.draw_rectangle(frame, 190, 75, 300, 105)
    # frame = video.convert_color(frame, "BGR2RGB")
    frame = video.draw_text(frame, "Тест", 200, 100, color=(0, 255, 0), font_scale=1, thickness=2)
    frame = video.draw_line(frame, 200, 300, 220, 410)
    writer.write(frame)
    if not video.show(frame):
        break

video.release()