import os
from dataclasses import dataclass
from typing import List

@dataclass
class PizzeriaConfig:
    # Kafka settings
    kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    kafka_topic: str = os.getenv('KAFKA_TOPIC', 'pizzeria.events')
    
    # Simulation settings
    simulation_interval: float = float(os.getenv('SIMULATION_INTERVAL', '2'))
    rush_hour_multiplier: int = int(os.getenv('RUSH_HOUR_MULTIPLIER', '3'))
    base_orders_per_minute: float = float(os.getenv('BASE_ORDERS_PER_MINUTE', '0.5'))
    
    # Pizza menu
    pizza_types: List[str] = None
    pizza_sizes: List[str] = None
    
    def __post_init__(self):
        if self.pizza_types is None:
            self.pizza_types = ['margherita', 'pepperoni', 'supreme', 'hawaiian', 'veggie', 'meat_lovers']
        if self.pizza_sizes is None:
            self.pizza_sizes = ['small', 'medium', 'large', 'xlarge']

# Global config instance
config = PizzeriaConfig()