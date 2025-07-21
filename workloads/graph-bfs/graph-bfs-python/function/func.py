# app.py
import datetime
import json
import logging
import igraph
import random

def new():
    return Function()

class Function:
    def __init__(self):
        pass

    async def handle(self, scope, receive, send):
        logging.info("Received request")

        # Read body
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        try:
            event = json.loads(body.decode())
        except Exception as e:
            await self.send_json(send, {"error": f"Invalid JSON: {str(e)}"}, status=400)
            return

        size = event.get('size')
        if not isinstance(size, int) or size <= 0:
            await self.send_json(send, {"error": "Missing or invalid 'size'"}, status=400)
            return

        if "seed" in event:
            random.seed(event["seed"])

        # Generate Barabási–Albert graph
        graph_generating_begin = datetime.datetime.now()
        graph = igraph.Graph.Barabasi(size, 10)
        graph_generating_end = datetime.datetime.now()

        # Run BFS
        process_begin = datetime.datetime.now()
        bfs_result = graph.bfs(0)  # (order, dist, parents)
        process_end = datetime.datetime.now()

        # Microsecond timings
        graph_generating_time = (
            (graph_generating_end - graph_generating_begin)
            / datetime.timedelta(microseconds=1)
        )
        process_time = (
            (process_end - process_begin)
            / datetime.timedelta(microseconds=1)
        )

        await self.send_json(send, {
            "result": {
                "order": bfs_result[0],
                "dist": bfs_result[1],
                "parents": bfs_result[2],
            },
            "measurement": {
                "graph_generating_time": graph_generating_time,
                "compute_time": process_time
            }
        })

    async def send_json(self, send, data, status=200):
        body = json.dumps(data).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    def start(self, cfg):
        logging.info("Function starting")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
