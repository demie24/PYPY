import asyncio
import logging
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.websocket_manager import ws_manager
from gateway.mqtt_manager import mqtt_manager
from gateway.store import store
from gateway.routes.system import router as system_router
from gateway.routes.telemetry import router as telemetry_router
from gateway.routes.saas_auth import router as saas_auth_router
from gateway.routes.billing import router as billing_router
from gateway.routes.simulation import router as simulation_router
from gateway.routes.scenarios import router as scenarios_router
from gateway.routes.experiments import router as experiments_router
from gateway.routes.copilot import router as copilot_router
from gateway.routes.operations import router as operations_router, update_api_request_metric
from gateway.routes.security_hardening import router as security_router
from gateway.routes.analytics import router as analytics_router
from gateway.routes.admin_portal import router as admin_portal_router


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gateway.main")

app = FastAPI(
    title="Smart Grid Cybersecurity Gateway",
    description="Real-time WebSocket and MQTT integration bus for grid digital twins"
)

# Custom Rate Limiting Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 150, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        # Skip health checks, telemetry websocket, and local unit test triggers
        path = request.url.path
        if path.startswith("/ws") or "health" in path:
            return await call_next(request)
            
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        timestamps = self.requests.get(ip, [])
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        
        if len(timestamps) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit exceeded."}
            )
            
        timestamps.append(now)
        self.requests[ip] = timestamps
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# Security Headers + Metrics Tracking middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start) * 1000
    is_error = response.status_code >= 400
    # Skip metrics tracking for websocket, health, and prometheus endpoints
    if not request.url.path.startswith("/ws") and "prometheus" not in request.url.path:
        update_api_request_metric(latency_ms, is_error)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Hardened CORS configuration
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS", 
    "https://pypygrid.com,https://app.pypygrid.com,http://localhost:3000,http://localhost:3001,http://localhost:8080"
)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include HTTP API routes
app.include_router(system_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api")
app.include_router(saas_auth_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")
app.include_router(scenarios_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(operations_router, prefix="/api")
app.include_router(security_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(admin_portal_router, prefix="/api")

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
    # Initialize database tables (idempotent)
    from services.auth.session import init_db
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

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
