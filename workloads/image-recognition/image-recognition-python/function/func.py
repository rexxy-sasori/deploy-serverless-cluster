import logging
import base64
import json
import io
import os
import time
import torch
import torchvision.transforms as transforms
from PIL import Image
from minio import Minio
from minio.error import S3Error
from functools import lru_cache

class Function:
    def __init__(self):
        self.model_cache = {}
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])
        self.minio_client = None
        self.bucket_name = None

    def start(self):
        logging.info("Initializing MinIO client from environment variables...")
        self.minio_client = Minio(
            os.environ.get("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=False,
        )
        self.bucket_name = os.environ.get("MODEL_BUCKET", "models")
        logging.info(f"MinIO client ready. Using bucket: {self.bucket_name}")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"

    @lru_cache(maxsize=3)
    def load_model(self, model_name):
        """Download and load model from MinIO, cache using LRU"""
        model_path = f"/tmp/{model_name}"
        logging.info(f"Downloading model '{model_name}' from bucket '{self.bucket_name}'")
        download_start = time.time()
        self.minio_client.fget_object(self.bucket_name, model_name, model_path)
        download_end = time.time()
        download_time_us = int((download_end - download_start) * 1_000_000)

        model = torch.load(model_path, map_location=torch.device("cpu"))
        model.eval()
        logging.info(f"Model '{model_name}' loaded in {download_time_us} μs")
        return model, download_time_us

    async def handle(self, scope, receive, send):
        assert scope["type"] == "http"

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        try:
            data = json.loads(body.decode())
            model_name = data["model"]  # e.g. "resnet50.pth"
            image_data = base64.b64decode(data["image"])
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            input_tensor = self.transform(image).unsqueeze(0)

            # Load model and measure download time
            model, model_download_time_us = self.load_model(model_name)

            # Measure inference time
            inference_start = time.time()
            with torch.no_grad():
                outputs = model(input_tensor)
                _, predicted = torch.max(outputs, 1)
            inference_end = time.time()
            inference_time_us = int((inference_end - inference_start) * 1_000_000)

            class_idx = predicted.item()
            logging.info(f"Inference: {inference_time_us} μs, Predicted index: {class_idx}")

            result = {
                "class_index": class_idx,
                "inference_time_us": inference_time_us,
                "model_download_time_us": model_download_time_us
            }

            response_body = json.dumps(result).encode()
            status_code = 200
        except Exception as e:
            logging.exception("Request handling failed")
            response_body = json.dumps({"error": str(e)}).encode()
            status_code = 500

        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": response_body,
        })

def new():
    return Function()
