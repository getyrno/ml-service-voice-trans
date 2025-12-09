from fastapi.testclient import TestClient
from app.main import app
import os

# Initialize the test client
client = TestClient(app)

def test_transcribe_silent_video():
    """
    Tests the transcription of a silent video file.
    It should return a 200 OK status and an empty transcript.
    """
    video_path = "tests/test_data/silent_video.mp4"
    
    # Verify that the test video file actually exists before running the test
    assert os.path.exists(video_path), f"Test video not found at {video_path}"

    with open(video_path, "rb") as video_file:
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("silent_video.mp4", video_file, "video/mp4")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "video_id" in data
    assert "language" in data
    assert "transcript" in data
    # The transcript of a generated silent video should be an empty string.
    assert data["transcript"].strip() == ""


def test_upload_non_video_file_fails():
    """
    Tests that uploading a file that is not a video returns a 400 error.
    """
    # Create a dummy text file for the test
    dummy_file_path = "tests/test_data/not_a_video.txt"
    with open(dummy_file_path, "w") as f:
        f.write("this is not a video file")

    with open(dummy_file_path, "rb") as f:
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("not_a_video.txt", f, "text/plain")}
        )

    # Clean up the dummy file after the request
    os.remove(dummy_file_path)

    assert response.status_code == 400
    assert "Неверный тип файла" in response.json()["detail"]
