import json
import logging
import socket
from websocket_server import WebsocketServer
from websocket_server.websocket_server import WebSocketHandler

from src.constants import version

logging.getLogger('websocket_server.websocket_server').disabled = True


def _safe_websocket_handle(self):
    try:
        self.handshake()
        self.read_frames()
    except AssertionError:
        self.keep_alive = False
        try:
            self.request.close()
        except OSError:
            pass
    except Exception:
        self.keep_alive = False
        try:
            self.request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.request.close()
        except OSError:
            pass


WebSocketHandler.handle = _safe_websocket_handle

# websocket.enableTrace(True)

class Server:
    def __init__(self, log, Error):
        self.Error = Error
        self.log = log
        self.lastMessages = {}

    def start_server(self):
        port = None
        try:
            # print(self.lastMessage)
            with open("config.json", "r") as conf:
                port = json.load(conf)["port"]
            self.server = WebsocketServer(host="0.0.0.0", port=port)
            # server = websocket.WebSocketApp("wss://localhost:1100", on_open=on_open, on_message=on_message, on_close=on_close)
            self.server.set_fn_new_client(self.handle_new_client)
            self.server.run_forever(threaded=True)
        except Exception as e:
            self.Error.PortError(port)

    def handle_new_client(self, client, server):
        self.send_payload("version", {
            "core": version
        })
        for key in self.lastMessages:
            if key not in ["chat", "version"]:
                self.send_message(self.lastMessages[key])

    def send_message(self, message):
        self.server.send_message_to_all(message)

    def send_payload(self, type, payload):
        payload_copy = dict(payload)
        payload_copy["type"] = type
        # Canonical JSON makes payload comparison stable across dict ordering.
        msg_str = json.dumps(payload_copy, sort_keys=True, separators=(",", ":"))

        # Avoid rebroadcasting identical feed payloads on tight backend loops.
        if type == "feed" and self.lastMessages.get(type) == msg_str:
            return

        self.lastMessages[type] = msg_str
        self.server.send_message_to_all(msg_str)
