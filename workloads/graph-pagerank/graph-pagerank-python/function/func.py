import datetime
import json
import igraph
import logging

def new():
    return Function()

class Function:
    def __init__(self):
        pass

    async def handle(self, scope, receive, send):
        logging.info("OK: Request Received")

        # Read the full request body
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        try:
            event = json.loads(body.decode())
            size = event.get('size')
            if not isinstance(size, int):
                raise ValueError("Missing or invalid 'size' parameter")

            if "seed" in event:
                import random
                random.seed(event["seed"])

            graph_generating_begin = datetime.datetime.now()
            graph = igraph.Graph.Barabasi(size, 10)
            graph_generating_end = datetime.datetime.now()

            process_begin = datetime.datetime.now()
            result = graph.pagerank()
            process_end = datetime.datetime.now()

            graph_generating_time = (
                graph_generating_end - graph_generating_begin
            ) / datetime.timedelta(microseconds=1)

            process_time = (
                process_end - process_begin
            ) / datetime.timedelta(microseconds=1)

            response_body = json.dumps({
                "result": result[0],
                "measurement": {
                    "graph_generating_time": graph_generating_time,
                    "compute_time": process_time,
                }
            }).encode()

            status = 200

        except Exception as e:
            logging.exception("Error processing request")
            response_body = json.dumps({"error": str(e)}).encode()
            status = 500

        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
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
