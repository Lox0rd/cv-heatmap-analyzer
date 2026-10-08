import base64
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pytest

from src.ai.vision_api import VisionAPI


@pytest.fixture
def vision_api():
    with patch("src.ai.vision_api.OpenAI") as mock_openai:
        api = VisionAPI(
            api_key="test-api-key",
            base_url="https://test.example.com/v1",
            model="test-model"
        )

        yield api


def test_init_success():
    with patch("src.ai.vision_api.OpenAI") as mock_openai:
        api = VisionAPI(
            api_key="test-api-key",
            base_url="https://test.example.com/v1",
            model="test-model"
        )

        assert api.api_key == "test-api-key"
        assert api.base_url == "https://test.example.com/v1"
        assert api.model == "test-model"

        mock_openai.assert_called_once_with(
            api_key="test-api-key",
            base_url="https://test.example.com/v1"
        )


def test_init_without_api_key():
    with patch("src.ai.vision_api.load_dotenv"):
        with patch.dict(
            "os.environ",
            {},
            clear=True
        ):
            with pytest.raises(ValueError, match="COMET_API_KEY"):
                VisionAPI()


def test_init_without_base_url():
    with patch("src.ai.vision_api.load_dotenv"):
        with patch.dict(
            "os.environ",
            {
                "COMET_API_KEY": "test-api-key"
            },
            clear=True
        ):
            with pytest.raises(ValueError, match="COMET_BASE_URL"):
                VisionAPI()


def test_init_without_model():
    with patch("src.ai.vision_api.load_dotenv"):
        with patch.dict(
            "os.environ",
            {
                "COMET_API_KEY": "test-api-key",
                "COMET_BASE_URL": "https://test.example.com/v1"
            },
            clear=True
        ):
            with pytest.raises(ValueError, match="VISION_MODEL"):
                VisionAPI()


def test_analyze(vision_api):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test analysis"

    vision_api.client.chat.completions.create.return_value = mock_response

    image_data = b"test image data"

    with patch("builtins.open", mock_open(read_data=image_data)):
        result = vision_api.analyze(
            "test.jpg",
            "Что находится на изображении?"
        )

    assert result == "Test analysis"

    vision_api.client.chat.completions.create.assert_called_once()

    call_kwargs = (
        vision_api.client.chat.completions.create.call_args.kwargs
    )

    assert call_kwargs["model"] == "test-model"

    message = call_kwargs["messages"][0]
    assert message["role"] == "user"

    content = message["content"]

    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Что находится на изображении?"

    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )


def test_analyze_frame(vision_api):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Frame analysis"

    vision_api.client.chat.completions.create.return_value = mock_response

    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    result = vision_api.analyze_frame(
        frame,
        "Проанализируй кадр"
    )

    assert result == "Frame analysis"

    vision_api.client.chat.completions.create.assert_called_once()

    call_kwargs = (
        vision_api.client.chat.completions.create.call_args.kwargs
    )

    content = call_kwargs["messages"][0]["content"]

    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Проанализируй кадр"

    image_url = content[1]["image_url"]["url"]

    assert image_url.startswith("data:image/jpeg;base64,")

    encoded_image = image_url.split(",", 1)[1]
    decoded_image = base64.b64decode(encoded_image)

    assert decoded_image.startswith(b"\xff\xd8")


def test_analyze_frame_invalid_frame(vision_api):
    frame = None

    with pytest.raises(ValueError, match="Не удалось закодировать кадр"):
        vision_api.analyze_frame(
            frame,
            "Проанализируй кадр"
        )


def test_send_request(vision_api):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI response"

    vision_api.client.chat.completions.create.return_value = mock_response

    result = vision_api._send_request(
        "test-base64-image",
        "Test prompt"
    )

    assert result == "AI response"

    vision_api.client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Test prompt"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/jpeg;base64,"
                                "test-base64-image"
                            )
                        }
                    }
                ]
            }
        ]
    )