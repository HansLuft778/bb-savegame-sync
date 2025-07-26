import asyncio
import websockets
import time
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_SIZE = 50 * 1024 * 1024  # 50MB
PING_INTERVAL = 20
PING_TIMEOUT = 10

connected_clients = set()
message_count = 0
message_tracker = {}


def register_message(message_id: int, method: str, params=None):
    message_tracker[message_id] = {
        "id": message_id,
        "method": method,
        "params": params or {},
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }
    logger.info(f"Registered message {message_id} with method '{method}' in tracker")


def get_tracked_message(message_id: int):
    return message_tracker.get(message_id)


def mark_message_completed(message_id: int):
    if message_id in message_tracker:
        message_tracker[message_id]["status"] = "completed"
        logger.info(f"Marked message {message_id} as completed")


def remove_message_from_tracker(message_id: int):
    if message_id in message_tracker:
        removed = message_tracker.pop(message_id)
        logger.info(f"Removed message {message_id} from tracker")
        return removed
    return None


async def handle_save_file_response(websocket, result, message_id):
    try:
        logger.info(f"Received save file response for message {message_id}")

        ident = result["identifier"]
        is_binary = result["binary"]
        data = result["save"]

        byte_data = bytes(ord(c) for c in data)
        with open(f"bitburnerSave_{int(time.time())}_.json.gz", "wb") as f:
            f.write(byte_data)

    except Exception as e:
        logger.error(f"Error processing save file response: {e}")


async def cleanup_old_messages():
    # Clean up every minute
    while True:
        await asyncio.sleep(60)

        current_time = datetime.now()
        messages_to_remove = []

        # Remove messages older than 5 min
        for msg_id, msg_data in message_tracker.items():
            if msg_data["status"] == "completed":
                msg_time = datetime.fromisoformat(msg_data["timestamp"])
                if (current_time - msg_time).total_seconds() > 300:
                    messages_to_remove.append(msg_id)

        for msg_id in messages_to_remove:
            remove_message_from_tracker(msg_id)

        if messages_to_remove:
            logger.info(
                f"Cleaned up {len(messages_to_remove)} old completed messages from tracker"
            )


async def handle_jsonrpc_message(websocket, data):
    message_id = data.get("id")

    if "result" in data or "error" in data:
        # response to a previous request
        if message_id is not None:
            tracked_message = get_tracked_message(message_id)
            if tracked_message:
                logger.info(
                    f"Received response for tracked message {message_id}: {tracked_message['method']}"
                )
                mark_message_completed(message_id)

                if "result" in data:
                    result = data["result"]
                    method = tracked_message["method"]

                    if method == "getSaveFile":
                        await handle_save_file_response(websocket, result, message_id)
                    else:
                        logger.info(
                            f"Success response for {method}: {str(result)[:200]}..."
                        )

                elif "error" in data:
                    logger.error(
                        f"Error response for {tracked_message['method']}: {data['error']}"
                    )
            else:
                logger.warning(
                    f"Received response for unknown message ID: {message_id}"
                )
                # Send error response
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Unknown message received"},
                }
                await websocket.send(json.dumps(error_response))
    else:
        # Invalid JSON-RPC message
        logger.warning(f"Invalid JSON-RPC message received: {data}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": -32600, "message": "Invalid JSON-RPC message"},
        }
        await websocket.send(json.dumps(error_response))


async def handle_client(websocket):
    client_address = websocket.remote_address
    logger.info(f"New client connected: {client_address}")

    connected_clients.add(websocket)

    # immediatly request savefile data from client
    try:
        await get_savefile()
        logger.info("Requested save file from newly connected client")
    except Exception as e:
        logger.error(f"Failed to request save file from new client: {e}")

    # receive and parse messages from client
    try:
        async for message in websocket:
            message_size = len(message)
            logger.info(
                f"Received message from {client_address}: size={message_size} bytes"
            )
            if message_size < 1000:
                logger.info(f"Message content: {message}")

            data = json.loads(message)
            await handle_jsonrpc_message(websocket, data)

    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client_address} connection closed unexpectedly: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"Client {client_address} disconnected normally")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_address} disconnected")
    except asyncio.TimeoutError:
        logger.warning(f"Timeout with client {client_address}")
    except Exception as e:
        logger.error(f"Error handling client {client_address}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
    finally:
        # Remove client from connected clients
        connected_clients.discard(websocket)


async def broadcast_message(message):
    if connected_clients:
        logger.info(f"Broadcasting message to {len(connected_clients)} clients")
        # Create a copy of the set to avoid issues if clients disconnect during broadcast
        clients_copy = connected_clients.copy()
        await asyncio.gather(
            *[client.send(message) for client in clients_copy], return_exceptions=True
        )


async def get_savefile():
    global message_count
    if connected_clients:
        method = "getSaveFile"
        # Register the message in the tracker before sending
        register_message(message_count, method)

        data = {
            "jsonrpc": "2.0",
            "id": message_count,
            "method": method,
        }
        message = json.dumps(data)
        await broadcast_message(message)
        message_count += 1


async def main():
    host = "localhost"
    port = 12525

    logger.info(f"Starting WebSocket server on {host}:{port}")
    logger.info(f"Max message size: {MAX_SIZE / 1024 / 1024:.1f}MB")

    server = await websockets.serve(
        handle_client,
        host,
        port,
        max_size=MAX_SIZE,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
        close_timeout=30,  # timeout for savefile message
    )
    logger.info(f"WebSocket server running on ws://{host}:{port}")

    # Start the cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_messages())

    try:
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        cleanup_task.cancel()
        server.close()
        await server.wait_closed()
        logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
