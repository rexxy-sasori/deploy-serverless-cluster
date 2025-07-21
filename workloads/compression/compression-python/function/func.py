import os
import shutil
import uuid
import logging
import json
import datetime
from minio import Minio
from minio.error import S3Error

def new():
    return Function()

class MinioClient:
    def __init__(self, endpoint, access_key, secret_key):
        """Initialize MinIO client."""
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False  # Set True if using HTTPS
        )

    def download_directory(self, bucket_name, prefix, download_path):
        """Recursively download a directory from MinIO to the local file system."""
        try:
            # Ensure the bucket exists
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket '{bucket_name}' does not exist.")
            
            # List all objects in the specified prefix (directory)
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

            for obj in objects:
                local_file_path = os.path.join(download_path, os.path.relpath(obj.object_name, prefix))
                local_dir = os.path.dirname(local_file_path)
                
                # Create the local directory if it doesn't exist
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir)

                # Download the file
                self.client.fget_object(bucket_name, obj.object_name, local_file_path)
                logging.info(f"Downloaded {obj.object_name} to {local_file_path}")
        
        except S3Error as e:
            logging.error(f"Error downloading directory: {e}")
            raise

    def upload(self, bucket_name, key, file_path):
        """Upload a file to MinIO."""
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

        with open(file_path, "rb") as f:
            size = os.path.getsize(file_path)
            self.client.put_object(bucket_name, key, f, length=size)
            logging.info(f"Uploaded {file_path} to {bucket_name}/{key}")


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

            # Temporary download path
            download_dir = f"/tmp/{key}-dir"
            os.makedirs(download_dir, exist_ok=True)

            # Step 1: Download entire directory from MinIO
            self.minio.download_directory(input_bucket, key, download_dir)

            # Step 2: Compress the downloaded directory
            compress_begin = datetime.datetime.utcnow()
            zip_base_path = f"/tmp/{key}"
            zip_path = f"{zip_base_path}.zip"
            shutil.make_archive(zip_base_path, 'zip', root_dir=download_dir)
            compress_end = datetime.datetime.utcnow()

            # Step 3: Upload the ZIP file to MinIO
            self.minio.upload(output_bucket, f"{key}.zip", zip_path)

            end_time = datetime.datetime.utcnow()

            result = {
                "status": "success",
                "key": f"{key}.zip",
                "timing": {
                    "download_ms": (compress_begin - start_time).total_seconds() * 1000,
                    "compress_ms": (compress_end - compress_begin).total_seconds() * 1000,
                    "total_ms": (end_time - start_time).total_seconds() * 1000
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
