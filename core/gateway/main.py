import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from gateway.websocket_manager import ws_manager
from gateway.mqtt_manager import mqtt_manager
from gateway.store import store
from gateway.routes.system import router as system_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gateway.main")

app = FastAPI(
    title="Smart Grid Cybersecurity Gateway",
    description="Real-time WebSocket and MQTT integration bus for grid digital twins"
)

# Enable CORS for dashboard web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include HTTP API routes
app.include_router(system_router, prefix="/api")

async def check_telemetry_freshness_task():
    import time
    while True:
        await asyncio.sleep(2.0)
        now = time.time()
        last_time = getattr(store, "last_telemetry_time", 0.0)
        if last_time > 0.0 and (now - last_time) > 4.0:
            offline_payload = {
                "topic": "grid/telemetry/status",
                "payload": {
                    "status": "OFFLINE",
                    "timestamp": int(now * 1000),
                    "msg": "COMMUNICATION LOST: Digital Twin simulator went offline."
                }
            }
            await ws_manager.broadcast(offline_payload)
            logger.warning("Digital Twin simulator went offline. Broadcasted status update.")

@app.on_event("startup")
async def startup_event():
    # Capture the running event loop and initialize the MQTT subscriber client
    loop = asyncio.get_running_loop()
    mqtt_manager.start(loop)
    asyncio.create_task(check_telemetry_freshness_task())
    logger.info("Gateway service startup completed.")

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_manager.stop()
    logger.info("Gateway service shutdown completed.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    
    # 1. Immediately send current state and history cache (Bootstrap payload)
    bootstrap_data = store.get_bootstrap_payload()
    await ws_manager.send_personal_message(bootstrap_data, websocket)
    
    try:
        while True:
            # 2. Listen for control actions from dashboard clients
            data = await websocket.receive_text()
            try:
                import json
                message = json.loads(data)
                topic = message.get("topic")
                payload = message.get("payload")
                
                if topic and payload is not None:
                    if topic == "grid/ping":
                        pong_response = {
                            "type": "PONG",
                            "payload": payload
                        }
                        await websocket.send_text(json.dumps(pong_response))
                    else:
                        # Forward control commands directly to MQTT broker
                        mqtt_manager.publish(topic, payload)
                        logger.info(f"Dashboard control forwarded to MQTT [{topic}]: {payload}")
                else:
                    logger.warning("WebSocket command received missing 'topic' or 'payload' parameter.")
            except json.JSONDecodeError:
                logger.error("WebSocket message could not be decoded as valid JSON.")
            except Exception as e:
                logger.error(f"Error handling WebSocket client message: {e}")
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection exception occurred: {e}")
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
