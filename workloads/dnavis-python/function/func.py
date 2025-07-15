import datetime
import io
import json
import os
import logging
from minio import Minio
from minio.error import S3Error
from squiggle import transform

# MinIO Client Class
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

            # Upload the file
            self.client.put_object(bucket_name, object_name, file_stream, len(file_stream.getvalue()))
            logging.info(f"File '{object_name}' uploaded to bucket '{bucket_name}'")
            return object_name  # Return the key (object name)
        except S3Error as e:
            logging.error(f"Error uploading file: {e}")
            raise e

def get_instance():
    """Create and return an instance of MinioClient using environment variables."""
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    
    return MinioClient(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY)


# ASGI Function Handler
def new():
    return Function()

class Function:
    def __init__(self):
        # Initialize the MinIO client once when the Function is created
        self.client = get_instance()

    async def handle(self, scope, receive, send):
        logging.info("OK: Request Received")

        assert scope["type"] == "http"

        # Read HTTP request body
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

            if not all([input_bucket, output_bucket, key]):
                raise ValueError("Missing required fields in request body")

            # Create local path and ensure directory exists
            download_path = os.path.join("/tmp", key)
            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            # Download from input bucket
            download_begin = datetime.datetime.now()
            self.client.download(input_bucket, key, download_path)
            download_stop = datetime.datetime.now()

            # Read and process
            with open(download_path, "r") as f:
                data = f.read()

            process_begin = datetime.datetime.now()
            result = transform(data)
            process_end = datetime.datetime.now()

            # Upload result to output bucket
            upload_begin = datetime.datetime.now()
            buf = io.BytesIO(json.dumps(result).encode())
            buf.seek(0)
            key_name = self.client.upload_stream(output_bucket, key, buf)
            upload_stop = datetime.datetime.now()
            buf.close()

            # Measurements in microseconds
            download_time = (download_stop - download_begin) / datetime.timedelta(microseconds=1)
            upload_time = (upload_stop - upload_begin) / datetime.timedelta(microseconds=1)
            process_time = (process_end - process_begin) / datetime.timedelta(microseconds=1)

            response = {
                "result": {
                    "bucket": output_bucket,
                    "key": key_name
                },
                "measurement": {
                    "download_time": download_time,
                    "compute_time": process_time,
                    "upload_time": upload_time
                }
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
