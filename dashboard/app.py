import os
import json
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from influxdb_client_3 import InfluxDBClient3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
INFLUXDB_HOST = os.getenv('INFLUXDB_HOST', 'localhost')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_DATABASE = os.getenv('INFLUXDB_BUCKET', 'pizzeria_data')  # In v3, bucket = database
UPDATE_INTERVAL = int(os.getenv('DASHBOARD_UPDATE_INTERVAL', '1000')) / 1000

# FastAPI app
app = FastAPI(title="Papa Giuseppe's Pizzeria Dashboard")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class DashboardData:
    def __init__(self):
        self.connected_clients: List[WebSocket] = []
        self.simulation_controls = {
            "rush_mode": False,
            "equipment_failure": False,
            "new_orders_enabled": True,
            "speed_multiplier": 1.0
        }
        self.influxdb_client = None
        self._init_influxdb_client()
    
    def _init_influxdb_client(self):
      try:
          if not INFLUXDB_TOKEN:
              logger.error("INFLUXDB_TOKEN not set!")
              return None
              
          self.influxdb_client = InfluxDBClient3(
              host=f"http://{INFLUXDB_HOST}:8181",
              token=INFLUXDB_TOKEN,
              database=INFLUXDB_DATABASE
          )
          logger.info("InfluxDB v3 client initialized successfully")
      except Exception as e:
          logger.error(f"Failed to initialize InfluxDB client: {e}")
          self.influxdb_client = None
    
    async def add_client(self, websocket: WebSocket):
        self.connected_clients.append(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
    
    async def remove_client(self, websocket: WebSocket):
        if websocket in self.connected_clients:
            self.connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
    
    async def broadcast_data(self, data: Dict):
        if not self.connected_clients:
            return
            
        disconnected = []
        for client in self.connected_clients:
            try:
                await client.send_text(json.dumps(data))
            except Exception as e:
                logger.warning(f"Client disconnected: {e}")
                disconnected.append(client)
        
        for client in disconnected:
            await self.remove_client(client)

# Global dashboard data instance
dashboard = DashboardData()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Papa Giuseppe's Pizzeria Dashboard"
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await dashboard.add_client(websocket)
    
    try:
        initial_data = await get_dashboard_data()
        await websocket.send_text(json.dumps(initial_data))
        
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                await handle_client_message(json.loads(message))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        await dashboard.remove_client(websocket)

async def handle_client_message(message: Dict):
    """Handle interactive control messages"""
    if message.get("type") == "control":
        action = message.get("action")
        
        if action == "toggle_rush_mode":
            dashboard.simulation_controls["rush_mode"] = not dashboard.simulation_controls["rush_mode"]
            logger.info(f"Rush mode: {dashboard.simulation_controls['rush_mode']}")
            
        elif action == "toggle_equipment_failure":
            dashboard.simulation_controls["equipment_failure"] = not dashboard.simulation_controls["equipment_failure"]
            logger.info(f"Equipment failure mode: {dashboard.simulation_controls['equipment_failure']}")
            
        elif action == "toggle_new_orders":
            dashboard.simulation_controls["new_orders_enabled"] = not dashboard.simulation_controls["new_orders_enabled"]
            logger.info(f"New orders enabled: {dashboard.simulation_controls['new_orders_enabled']}")
            
        elif action == "set_speed":
            speed = float(message.get("value", 1.0))
            dashboard.simulation_controls["speed_multiplier"] = max(0.1, min(5.0, speed))
            logger.info(f"Speed multiplier: {dashboard.simulation_controls['speed_multiplier']}")

async def get_dashboard_data() -> Dict:
    """Query InfluxDB v3 and return dashboard data"""
    try:
        if not dashboard.influxdb_client:
            return {"error": "InfluxDB client not available", "status": "error"}
        
        # Query for oven data using v3 SQL syntax
        oven_query = """
        SELECT *
        FROM pizzeria_event
        WHERE time >= now() - interval '5 minutes'
        AND equipment_type = 'pizza_oven'
        AND event_type = 'temperature_reading'
        ORDER BY time DESC
        LIMIT 10
        """
        
        # Query for recent orders
        orders_query = """
        SELECT *
        FROM pizzeria_event
        WHERE time >= now() - interval '30 minutes'
        AND equipment_type = 'order_manager'
        AND (event_type = 'order_created' OR event_type = 'order_status_update')
        ORDER BY time DESC
        LIMIT 20
        """
        
        # Query for metrics
        metrics_query = """
        SELECT *
        FROM pizzeria_event
        WHERE time >= now() - interval '1 hour'
        AND equipment_type = 'order_manager'
        AND event_type = 'metrics_update'
        ORDER BY time DESC
        LIMIT 1
        """
        
        # Execute queries
        try:
            oven_result = dashboard.influxdb_client.query(query=oven_query, language="sql")
            oven_df = oven_result.to_pandas() if oven_result else pd.DataFrame()
        except Exception:
            oven_df = pd.DataFrame()
            
        try:
            orders_result = dashboard.influxdb_client.query(query=orders_query, language="sql")
            orders_df = orders_result.to_pandas() if orders_result else pd.DataFrame()
        except Exception:
            orders_df = pd.DataFrame()
            
        try:
            metrics_result = dashboard.influxdb_client.query(query=metrics_query, language="sql")
            metrics_df = metrics_result.to_pandas() if metrics_result else pd.DataFrame()
        except Exception:
            metrics_df = pd.DataFrame()
        
        # Process results
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "ovens": process_oven_data(oven_df),
            "recent_orders": process_orders_data(orders_df),
            "metrics": process_metrics_data(metrics_df),
            "simulation_controls": dashboard.simulation_controls.copy(),
            "status": "connected"
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error querying dashboard data: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "status": "error"
        }

def process_oven_data(df: pd.DataFrame) -> List[Dict]:
    """Process oven data from DataFrame"""
    if df.empty:
        return []
    
    ovens = {}
    for _, row in df.iterrows():
        oven_id = row.get("equipment_id", "unknown")
        
        if oven_id not in ovens:
            ovens[oven_id] = {
                "oven_id": oven_id,
                "temperature": 0,
                "capacity_used": 0,
                "capacity_total": 4,
                "efficiency": 0,
                "status": "offline"
            }
        
        # Update oven data from row
        if pd.notna(row.get("temperature")):
            ovens[oven_id]["temperature"] = round(float(row["temperature"]), 1)
            ovens[oven_id]["status"] = "active"
        if pd.notna(row.get("capacity_used")):
            ovens[oven_id]["capacity_used"] = int(row["capacity_used"])
        if pd.notna(row.get("capacity_total")):
            ovens[oven_id]["capacity_total"] = int(row["capacity_total"])
        if pd.notna(row.get("efficiency_score")):
            ovens[oven_id]["efficiency"] = round(float(row["efficiency_score"]), 2)
    
    return list(ovens.values())

def process_orders_data(df: pd.DataFrame) -> List[Dict]:
    """Process orders data from DataFrame"""
    if df.empty:
        return []
    
    orders = []
    for _, row in df.iterrows():
        order_data = {
            "timestamp": row.get("time"),
            "order_id": row.get("order_id", ""),
            "pizza_type": row.get("pizza_type", ""),
            "size": row.get("size", ""),
            "status": row.get("status", ""),
            "event_type": row.get("event_type", "")
        }
        
        if pd.notna(row.get("duration")):
            order_data["duration"] = int(float(row["duration"]))
            
        orders.append(order_data)
    
    return orders[:10]

def process_metrics_data(df: pd.DataFrame) -> Dict:
    """Process metrics data from DataFrame"""
    metrics = {
        "active_orders": 0,
        "completed_orders": 0,
        "avg_completion_time": 0,
        "orders_received": 0,
        "orders_prep": 0,
        "orders_baking": 0,
        "orders_ready": 0,
        "rush_hour": False
    }
    
    if not df.empty:
        row = df.iloc[0]  # Get latest metrics
        
        if pd.notna(row.get("active_orders")):
            metrics["active_orders"] = int(row["active_orders"])
        if pd.notna(row.get("completed_orders")):
            metrics["completed_orders"] = int(row["completed_orders"])
        if pd.notna(row.get("avg_completion_time")):
            metrics["avg_completion_time"] = round(float(row["avg_completion_time"]), 1)
        if pd.notna(row.get("current_hour_rush")):
            metrics["rush_hour"] = bool(row["current_hour_rush"])
    
    return metrics

async def periodic_updates():
    """Send periodic updates to all connected clients"""
    while True:
        try:
            if dashboard.connected_clients:
                data = await get_dashboard_data()
                await dashboard.broadcast_data(data)
            await asyncio.sleep(UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_updates())
    logger.info("Dashboard started successfully!")

@app.on_event("shutdown") 
async def shutdown_event():
    if dashboard.influxdb_client:
        dashboard.influxdb_client.close()
    logger.info("Dashboard stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if dashboard.influxdb_client:
            # Test connection with simple query
            result = dashboard.influxdb_client.query(query="SELECT 1 as test", language="sql")
            return {"status": "healthy", "influxdb": "connected"}
        else:
            return {"status": "unhealthy", "error": "InfluxDB client not initialized"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}