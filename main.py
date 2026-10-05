from src.video.video_processor import VideoProcessor 

video = VideoProcessor("data/input/video.mp4") 
info = video.get_info() 

print(f"Разрешение: {info['width']}x{info['height']}") 
print(f"FPS: {info['fps']}") 
print(f"Кадров: {info['frame_count']}") 
print(f"Длительность: {info['duration']:.2f} сек.") 

video.show() 
video.release()