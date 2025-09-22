import json
import time
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from typing import Dict, Any
from config import config

class PizzeriaDataPublisher:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        self.logger = logging.getLogger(__name__)
        
    def create_message(self, 
                      equipment_id: str,
                      equipment_type: str,
                      event_type: str,
                      **kwargs) -> Dict[str, Any]:
        """
        Create a standardized message following our Kafka Schema.
        This is where we implement the Message Schema for Kafka!
        """
        # Base message structure (our Kafka Message Schema)
        message = {
            "measurement": "pizzeria_event",
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "location": "main_kitchen",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add all additional fields from kwargs
        message.update(kwargs)
        return message
    
    def publish_oven_event(self, oven_id: str, event_type: str, **data):
        """Publish pizza oven events"""
        message = self.create_message(
            equipment_id=oven_id,
            equipment_type="pizza_oven",
            event_type=event_type,
            **data
        )
        self._send_message(message)
    
    def publish_prep_event(self, station_id: str, event_type: str, **data):
        """Publish prep station events"""
        message = self.create_message(
            equipment_id=station_id,
            equipment_type="prep_station", 
            event_type=event_type,
            **data
        )
        self._send_message(message)
    
    def publish_order_event(self, event_type: str, **data):
        """Publish order management events"""
        message = self.create_message(
            equipment_id="order_system",
            equipment_type="order_manager",
            event_type=event_type,
            **data
        )
        self._send_message(message)
    
    def _send_message(self, message: Dict[str, Any]):
        """Send message to Kafka topic"""
        try:
            key = f"{message['equipment_id']}_{message['event_type']}"
            future = self.producer.send(config.kafka_topic, key=key, value=message)
            self.producer.flush()  # Ensure message is sent
            self.logger.debug(f"Published: {key} -> {message['event_type']}")
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")