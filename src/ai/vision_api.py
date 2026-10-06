import base64
import os

import cv2
from dotenv import load_dotenv
from openai import OpenAI


class VisionAPI:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None
    ):
        load_dotenv()

        self.api_key = api_key or os.getenv("COMET_API_KEY")
        self.base_url = base_url or os.getenv("COMET_BASE_URL")
        self.model = model or os.getenv("VISION_MODEL")

        if not self.api_key:
            raise ValueError("Не указан COMET_API_KEY")

        if not self.base_url:
            raise ValueError("Не указан COMET_BASE_URL")

        if not self.model:
            raise ValueError("Не указан VISION_MODEL")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def analyze(self, image_path: str, prompt: str) -> str:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(
                image_file.read()
            ).decode("utf-8")

        return self._send_request(image_data, prompt)

    def analyze_frame(self, frame, prompt: str) -> str:
        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            raise ValueError("Не удалось закодировать кадр")

        image_data = base64.b64encode(
            buffer
        ).decode("utf-8")

        return self._send_request(image_data, prompt)

    def _send_request(self, image_data: str, prompt: str) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:image/jpeg;base64,{image_data}"
                                )
                            }
                        }
                    ]
                }
            ]
        )

        return response.choices[0].message.content