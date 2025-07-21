import logging
import os
import io
import json
import datetime
import shutil
from minio import Minio
from minio.error import S3Error

def new():
    return Function()

class MinioClient:
    def __init__(self, endpoint, access_key, secret_key):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False  # Set to True if TLS is used
        )

    def download(self, bucket, key, local_path):
        if not self.client.bucket_exists(bucket):
            raise ValueError(f"Bucket '{bucket}' does not exist.")
        self.client.fget_object(bucket, key, local_path)
        logging.info(f"Downloaded {bucket}/{key} to {local_path}")

    def upload(self, bucket, key, file_path):
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
        with open(file_path, "rb") as f:
            size = os.path.getsize(file_path)
            self.client.put_object(bucket, key, f, length=size)
            logging.info(f"Uploaded {file_path} to {bucket}/{key}")


class Function:
    def __init__(self):
        self.minio = None

    def start(self, cfg):
        logging.info("Function starting")
        self.minio = MinioClient(
            cfg.get("MINIO_ENDPOINT", "minio:9000"),
            cfg.get("MINIO_ACCESS_KEY", "minioadmin"),
            cfg.get("MINIO_SECRET_KEY", "minioadmin")
        )

    async def handle(self, scope, receive, send):
        if scope["method"] != "POST":
            await self.respond(send, 405, "Method Not Allowed")
            return

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        try:
            payload = json.loads(body.decode())
            input_bucket = payload["input-bucket"]
            output_bucket = payload["output-bucket"]
            key = payload["objectKey"]

            start_time = datetime.datetime.utcnow()

            download_dir = f"/tmp/{key}-dir"
            os.makedirs(download_dir, exist_ok=True)
            input_path = os.path.join(download_dir, key)
            zip_base_path = os.path.join("/tmp", key)
            zip_path = f"{zip_base_path}.zip"

            # Step 1: Download
            self.minio.download(input_bucket, key, input_path)

            # Step 2: Compress
            compress_begin = datetime.datetime.utcnow()
            shutil.make_archive(zip_base_path, 'zip', root_dir=download_dir)
            compress_end = datetime.datetime.utcnow()

            # Step 3: Upload
            self.minio.upload(output_bucket, f"{key}.zip", zip_path)

            end_time = datetime.datetime.utcnow()

            result = {
                "status": "success",
                "key": f"{key}.zip",
                "timing": {
                    "download_to_compress": (compress_begin - start_time).total_seconds(),
                    "compression": (compress_end - compress_begin).total_seconds(),
                    "total": (end_time - start_time).total_seconds(),
                }
            }
            await self.respond(send, 200, json.dumps(result))

        except Exception as e:
            logging.exception("Error during processing")
            await self.respond(send, 500, f"Internal Server Error: {str(e)}")

    async def respond(self, send, status, message):
        headers = [[b"content-type", b"application/json"]]
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": headers
        })
        await send({
            "type": "http.response.body",
            "body": message.encode()
        })

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
