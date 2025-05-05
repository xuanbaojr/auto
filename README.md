# Pose Detection with Docker

This project uses OpenCV and MediaPipe to detect human poses from camera feeds and save videos when people are detected.

## Prerequisites

- Docker
- Docker Compose
- A webcam connected to your computer
- X11 display server (for GUI)

## Setup and Running

1. Clone this repository
2. Make sure your webcam is connected
3. Run the application using the provided script:

```bash
./run_docker.sh
```

Or manually with these commands:

```bash
# Allow X server connections
xhost +local:docker

# Build and run the container
docker-compose up --build
```

This will:
- Build the Docker image with all required dependencies
- Start the pose detection application
- Display the camera feed with pose detection
- Save videos when people are detected

## Configuration

The application uses the following cameras:
- Your default webcam (usually /dev/video0)
- RTSP streams (configured in the code)

Videos are saved to the `./video` directory.

## Controls

- Press 'q' to quit the application
- Ctrl+C to stop the Docker container

## Troubleshooting

### X11 Display Issues

If you still encounter display issues after using the run_docker.sh script, try these steps:

1. Check that your X server is running:
```bash
echo $DISPLAY
```

2. Try setting the DISPLAY variable explicitly:
```bash
DISPLAY=:0 docker-compose up
```

3. For Wayland users, try:
```bash
xhost +local:docker
DISPLAY=:0 QT_QPA_PLATFORM=xcb docker-compose up
```

### Camera Access

If the application cannot access your camera, check that the device path in docker-compose.yml matches your webcam:

```yaml
devices:
  - /dev/video0:/dev/video0  # Change if your webcam uses a different device
```

You can list available video devices with:
```bash
ls -l /dev/video*
```

### RTSP Streams

The application is configured to use RTSP streams. If you don't have an RTSP server, you might see errors. You can modify the code to use only the webcam by editing the pose.py file.

### MediaPipe Warnings

You might see warnings from MediaPipe about NORM_RECT and IMAGE_DIMENSIONS. These are informational warnings and don't affect the core functionality.
# auto
