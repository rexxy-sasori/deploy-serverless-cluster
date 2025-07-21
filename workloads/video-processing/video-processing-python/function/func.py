# Function
import json
import os
import logging
import time
import datetime
import io
import subprocess
from pathlib import Path
from minio.error import S3Error
from minio_clients import get_instance  # Ensure this is accessible

logging.basicConfig(level=logging.INFO)


def new():
    return Function()


class Function:
    def __init__(self):
        self.minio = None

    def start(self, cfg):
        logging.info("Function starting")
        self.minio = get_instance()

    async def handle(self, scope, receive, send):
        if scope["type"] != "http":
            return

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        try:
            event = json.loads(body.decode())
        except json.JSONDecodeError:
            await self.send_response(send, 400, {"error": "Invalid input"})
            logging.error("Invalid input format")
            return

        logging.info(f"Received event: {event}")
        try:
            input_bucket = event["bucket"]["input"]
            output_bucket = event["bucket"]["output"]
            key = event["object"]["key"]
            duration = event["object"]["duration"]
            op = event["object"]["op"]
        except KeyError as e:
            await self.send_response(send, 400, {"error": f"Missing key: {e}"})
            return

        if ".." in input_bucket or ".." in key:
            await self.send_response(send, 400, {"error": "Invalid path components"})
            return

        tmp_input = f"/tmp/{Path(key).name}"
        tmp_output = f"/tmp/processed-{Path(key).name}"
        output_key = f"processed-{key}"

        try:
            start_dl = time.time()
            self.minio.download(input_bucket, key, tmp_input)
            end_dl = time.time()
            dl_size = Path(tmp_input).stat().st_size
        except Exception as e:
            await self.send_response(send, 500, {"error": f"Download failed: {str(e)}"})
            return

        try:
            start_proc = time.time()
            self.process_file(op, tmp_input, tmp_output, duration)
            end_proc = time.time()
        except Exception as e:
            await self.send_response(send, 500, {"error": f"Processing failed: {str(e)}"})
            return

        try:
            start_ul = time.time()
            with open(tmp_output, "rb") as f:
                buf = io.BytesIO(f.read())
            key_uploaded = self.minio.upload_file(output_bucket, output_key, buf)
            end_ul = time.time()
            ul_size = buf.getbuffer().nbytes
        except Exception as e:
            await self.send_response(send, 500, {"error": f"Upload failed: {str(e)}"})
            return

        result = {
            "result": {
                "bucket": output_bucket,
                "key": key_uploaded
            },
            "measurement": {
                "download_time_us": (end_dl - start_dl) * 1e6,
                "download_size": dl_size,
                "compute_time_us": (end_proc - start_proc) * 1e6,
                "upload_time_us": (end_ul - start_ul) * 1e6,
                "upload_size": ul_size
            }
        }

        logging.info(f"Response: {result}")
        await self.send_response(send, 200, result)

    def process_file(self, op, input_path, output_path, duration):
        logging.info(f"Processing with ffmpeg: {op}, input: {input_path}, output: {output_path}, duration: {duration}")
        if op != "extract-gif":
            raise ValueError(f"Unsupported operation: {op}")
        cmd = [
            "ffmpeg", "-y", "-i", input_path, "-t", duration,
            "-vf", "fps=10,scale=320:trunc(ih/2)*2:flags=lanczos", output_path
        ]
        subprocess.run(cmd, check=True)

    async def send_response(self, send, status_code, data):
        headers = [[b"content-type", b"application/json"]]
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps(data).encode(),
        })

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
