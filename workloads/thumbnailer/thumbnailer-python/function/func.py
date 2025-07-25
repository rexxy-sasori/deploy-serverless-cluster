import datetime
import io
import json
import os
import logging
from PIL import Image
from minio import Minio
from minio.error import S3Error

class MinioClient:
    def __init__(self, endpoint, access_key, secret_key):
        """Initialize the MinIO client."""
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False  # Assuming HTTP, change to True for HTTPS
        )

    def download(self, bucket_name, object_name, file_path):
        """Download a file from MinIO."""
        try:
            # Ensure that the bucket exists
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket '{bucket_name}' does not exist.")
            
            # Get the file size and log it
            object_stat = self.client.stat_object(bucket_name, object_name)
            download_size = object_stat.size  # In bytes
            logging.info(f"Download file '{object_name}' size: {download_size} bytes")  # Log download size
            
            # Download the file
            self.client.fget_object(bucket_name, object_name, file_path)
            logging.info(f"File '{object_name}' downloaded to '{file_path}'")
        except S3Error as e:
            logging.error(f"Error downloading file: {e}")
            raise e

    def upload_stream(self, bucket_name, object_name, file_stream):
        """Upload a file to MinIO from a stream."""
        try:
            # Ensure the bucket exists
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

            # Log the file size being uploaded
            upload_size = len(file_stream.getvalue())  # In bytes
            logging.info(f"Uploading file '{object_name}' size: {upload_size} bytes")  # Log upload size

            # Upload the file
            self.client.put_object(bucket_name, object_name, file_stream, upload_size)
            logging.info(f"File '{object_name}' uploaded to bucket '{bucket_name}'")
            return object_name  # Return the key (object name)
        except S3Error as e:
            logging.error(f"Error uploading file: {e}")
            raise e


def new():
    return Function()


class Function:
    def __init__(self):
        # Initialize the MinIO client once when the Function is created
        self.client = MinioClient(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin")
        )

    async def handle(self, scope, receive, send):
        logging.info("OK: Request Received")
        assert scope["type"] == "http"

        # Collect request body
        body = b""
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

        try:
            # Parse JSON body
            event = json.loads(body.decode("utf-8"))
            input_bucket = event.get("input-bucket")
            output_bucket = event.get("output-bucket")
            key = event.get("objectKey")
            width = int(event.get("width", 256))
            height = int(event.get("height", 256))
            upload_enabled = event.get("upload", False)

            if not all([input_bucket, output_bucket, key]):
                raise ValueError("Missing required fields in request body")

            # Prepare local file path
            download_path = os.path.join("/tmp", key)
            resized_path = os.path.join("/tmp", f"resized-{key}")
            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            # Download the image from MinIO
            download_begin = datetime.datetime.now()
            self.client.download(input_bucket, key, download_path)
            download_end = datetime.datetime.now()

            # Process the image: resize
            process_begin = datetime.datetime.now()
            with Image.open(download_path) as image:
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.thumbnail((width, height))
                image.save(resized_path, format="JPEG")
            resized_size = os.path.getsize(resized_path)
            process_end = datetime.datetime.now()

            # Log the resized image size
            logging.info(f"Resized object size: {resized_size} bytes")

            # Optional upload
            key_name = "upload-skipped"
            upload_time = None
            if upload_enabled:
                upload_begin = datetime.datetime.now()
                with open(resized_path, "rb") as f:
                    buf = io.BytesIO(f.read())
                    buf.seek(0)
                    key_name = self.client.upload_stream(output_bucket, key, buf)
                upload_end = datetime.datetime.now()
                upload_time = (upload_end - upload_begin) / datetime.timedelta(microseconds=1)

            # Measurements
            measurement = {
                "download_time": (download_end - download_begin) / datetime.timedelta(microseconds=1),
                "compute_time": (process_end - process_begin) / datetime.timedelta(microseconds=1),
            }
            if upload_enabled:
                measurement["upload_time"] = upload_time
                measurement["upload_size"] = resized_size

            response = {
                "result": {
                    "bucket": output_bucket,
                    "key": key_name
                },
                "measurement": measurement
            }

            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps(response).encode("utf-8"),
            })

        except Exception as e:
            logging.exception("Handler failed")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({
                "type": "http.response.body",
                "body": f"Error: {str(e)}".encode("utf-8"),
            })

    def start(self, cfg):
        logging.info("Function starting")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
