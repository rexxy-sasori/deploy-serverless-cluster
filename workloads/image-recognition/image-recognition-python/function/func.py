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

class Function:
    def __init__(self):
        self.models = {}  # Cache: model_name -> model
        self.model_download_times = {}  # model_name -> download time in μs
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])
        self.minio_client = None
        self.model_bucket = None

    def _init_minio(self, cfg):
        """Initialize MinIO client lazily from environment/config."""
        if self.minio_client is None:
            endpoint = cfg.get("MINIO_ENDPOINT", "minio:9000")
            access_key = cfg.get("MINIO_ACCESS_KEY", "minioadmin")
            secret_key = cfg.get("MINIO_SECRET_KEY", "minioadmin")
            self.model_bucket = cfg.get("MODEL_BUCKET", "models")
            self.minio_client = Minio(
                endpoint, access_key=access_key, secret_key=secret_key, secure=False
            )
            logging.info("MinIO client initialized.")

    def _load_model_from_minio(self, model_name: str) -> torch.nn.Module:
        """Download and load model by name if not already loaded."""
        if model_name in self.models:
            return self.models[model_name]

        model_path = f"/tmp/{model_name}"
        logging.info(f"Downloading model {model_name} to {model_path}")

        download_start = time.time()
        self.minio_client.fget_object(self.model_bucket, model_name, model_path)
        download_end = time.time()
        download_time_us = int((download_end - download_start) * 1_000_000)
        self.model_download_times[model_name] = download_time_us

        model = torch.load(model_path, map_location=torch.device("cpu"))
        model.eval()
        self.models[model_name] = model
        logging.info(f"Model {model_name} loaded in {download_time_us} μs")
        return model

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
            image_data = base64.b64decode(data["image"])
            model_name = data["model_name"]  # required in request
            cfg = os.environ

            # Init MinIO (only once)
            self._init_minio(cfg)

            # Load model (download if needed)
            model = self._load_model_from_minio(model_name)

            # Preprocess image
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            input_tensor = self.transform(image).unsqueeze(0)

            # Inference timing
            inference_start = time.time()
            with torch.no_grad():
                outputs = model(input_tensor)
                _, predicted = torch.max(outputs, 1)
            inference_end = time.time()
            inference_time_us = int((inference_end - inference_start) * 1_000_000)

            class_index = predicted.item()
            logging.info(f"[{model_name}] Inference {inference_time_us} μs, Class {class_index}")

            result = {
                "class_index": class_index,
                "inference_time_us": inference_time_us,
                "model_download_time_us": self.model_download_times.get(model_name)
            }

            response_body = json.dumps(result).encode()
            status_code = 200
        except Exception as e:
            logging.exception("Request failed")
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

    def start(self, cfg):
        logging.info("Function initialized (model loading deferred)")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"

def new():
    return Function()
