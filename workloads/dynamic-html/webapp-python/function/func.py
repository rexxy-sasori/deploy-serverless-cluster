import logging
import random
import time
import json
from datetime import datetime
from jinja2 import Template

def new():
    return Function()

class Function:
    def __init__(self):
        self.template = Template("""
<!DOCTYPE html>
<html>
  <head>
    <title>Randomly generated data.</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="http://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css" rel="stylesheet" media="screen">
    <style type="text/css">
      .container {
        max-width: 500px;
        padding-top: 100px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <p>Welcome {{ username }}!</p>
      <p>Data generated at: {{ cur_time }}!</p>
      <p>Requested random numbers:</p>
      <ul>
        {% for n in random_numbers %}
        <li>{{ n }}</li>
        {% endfor %}
      </ul>
    </div>
  </body>
</html>
""")
        self.size_generators = {
            "test": 10,
            "tiny": 100,
            "small": 1000,
            "medium": 10000,
            "large": 100000,
            "huge": 1000000,
            "massive": 10000000,
        }

    def input_size(self, size):
        if size in self.size_generators:
            return self.size_generators[size]
        try:
            return int(size)
        except (ValueError, TypeError):
            return 1

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
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            logging.error(f"Failed to decode JSON: {e}")
            await send({
                "type": "http.response.start",
                "status": 400,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({
                "type": "http.response.body",
                "body": b"Invalid JSON",
            })
            return

        size = payload.get("size", "1")
        debug = str(payload.get("debug", "false")).lower() == "true"

        start_time = time.time()
        init_start = time.time()
        template = self.template
        init_end = time.time()

        setup_start = time.time()
        load_size = self.input_size(size)
        rand = random.Random()
        numbers = [rand.randint(0, 999999) for _ in range(load_size)]
        setup_end = time.time()

        context = {
            "username": "testname",
            "random_numbers": numbers,
            "cur_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        render_start = time.time()
        rendered = template.render(context)
        render_end = time.time()

        measurement = {
            "total_run_time": render_end - start_time,
            "init_time": init_end - init_start,
            "setup_time": setup_end - setup_start,
            "render_time": render_end - render_start,
            "input_size": float(load_size),
            "render_size": float(len(rendered)),
        }

        logging.info(f"Measurement: {measurement}")

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/html"]],
        })
        await send({
            "type": "http.response.body",
            "body": rendered.encode("utf-8"),
        })

    def start(self, cfg):
        logging.info("Function starting")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
