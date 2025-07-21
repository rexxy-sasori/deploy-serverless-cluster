# function.py
import logging
import json
import datetime
from igraph import Graph


def new():
    return Function()


class Function:
    def __init__(self):
        pass

    async def handle(self, scope, receive, send):
        logging.info("OK: Request Received")

        try:
            # Receive full request body
            body = b""
            more_body = True
            while more_body:
                message = await receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

            # Parse JSON request
            payload = json.loads(body.decode("utf-8"))
            size = payload.get("size")
            seed = payload.get("seed", None)

            if not isinstance(size, int) or size <= 0:
                raise ValueError("Invalid 'size'")

            if seed is not None:
                import random
                random.seed(seed)

            # Generate Barabási–Albert graph
            gen_start = datetime.datetime.now()
            graph = Graph.Barabasi(n=size, m=10)
            gen_end = datetime.datetime.now()

            # Compute spanning tree
            compute_start = datetime.datetime.now()
            spanning = graph.spanning_tree(None, False)
            compute_end = datetime.datetime.now()

            # Calculate timings in microseconds
            graph_time = (gen_end - gen_start) / datetime.timedelta(microseconds=1)
            compute_time = (compute_end - compute_start) / datetime.timedelta(microseconds=1)

            # Prepare result (return edge list)
            edge_list = [list(edge.tuple) for edge in spanning.es]

            response_body = json.dumps({
                "result": edge_list,
                "measurement": {
                    "graph_generating_time": graph_time,
                    "compute_time": compute_time
                }
            }).encode()

            status = 200
            content_type = b"application/json"

        except Exception as e:
            logging.exception("Error handling request")
            response_body = json.dumps({"error": str(e)}).encode()
            status = 400
            content_type = b"application/json"

        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", content_type],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": response_body,
        })

    def start(self, cfg):
        logging.info("Function starting")

    def stop(self):
        logging.info("Function stopping")

    def alive(self):
        return True, "Alive"

    def ready(self):
        return True, "Ready"
