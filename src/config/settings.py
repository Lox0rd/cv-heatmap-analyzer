"""Application-wide defaults for video analysis and rendering."""

# Detection
YOLO_MODEL_PATH = "models/yolo26n.pt"
DETECTION_CONFIDENCE = 0.5
TRACKED_OBJECTS = ("person", "car")
DETECTED_OBJECTS = ("person", "car", "bicycle", "motorcycle", "bus", "truck")

# Video sources and capture
DEFAULT_VIDEO_SOURCE = "data/input/VideoTests/cars1.mp4"
DEFAULT_CAMERA_INDEX = 0
VIDEO_BUFFER_SIZE = 1
VIDEO_QUEUE_SIZE = 2
VIDEO_MAX_FAILURES = 30
VIDEO_READ_TIMEOUT_MS = 5000
VIDEO_FALLBACK_FPS = 30.0

# Heatmap and preview
HEATMAP_DECAY = 0.995
HEATMAP_POINT_RADIUS = 10
HEATMAP_BLUR_SIGMA = 15
HEATMAP_ALPHA = 0.5
HEATMAP_COLORMAP_NAME = "Jet"

# Processing UI
DEFAULT_SKIP_FRAMES = 0
