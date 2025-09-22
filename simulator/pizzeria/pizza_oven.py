import random
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime, timedelta

@dataclass
class Pizza:
    order_id: str
    pizza_type: str
    size: str
    start_time: datetime
    cook_time: int  # seconds
    
    @property
    def is_ready(self) -> bool:
        return datetime.now() >= self.start_time + timedelta(seconds=self.cook_time)
    
    @property
    def time_remaining(self) -> int:
        remaining = (self.start_time + timedelta(seconds=self.cook_time) - datetime.now()).total_seconds()
        return max(0, int(remaining))

class PizzaOven:
    def __init__(self, oven_id: str, capacity: int = 4, publisher=None):
        self.oven_id = oven_id
        self.capacity = capacity
        self.publisher = publisher
        self.current_pizzas: List[Pizza] = []
        self.target_temperature = 450.0
        self.current_temperature = 450.0
        self.is_running = False
        self.door_open = False
        
        # Cooking times by size (in seconds)
        self.cook_times = {
            'small': 480,   # 8 minutes
            'medium': 600,  # 10 minutes  
            'large': 720,   # 12 minutes
            'xlarge': 900   # 15 minutes
        }
    
    def start(self):
        """Start the oven monitoring thread"""
        self.is_running = True
        threading.Thread(target=self._monitor_oven, daemon=True).start()
        threading.Thread(target=self._temperature_fluctuation, daemon=True).start()
    
    def stop(self):
        """Stop the oven"""
        self.is_running = False
    
    def add_pizza(self, order_id: str, pizza_type: str, size: str) -> bool:
        """Add a pizza to the oven if there's space"""
        if len(self.current_pizzas) >= self.capacity:
            return False
        
        cook_time = self.cook_times.get(size, 600)
        # Add some randomness to cook times
        cook_time += random.randint(-30, 60)
        
        pizza = Pizza(
            order_id=order_id,
            pizza_type=pizza_type, 
            size=size,
            start_time=datetime.now(),
            cook_time=cook_time
        )
        
        self.current_pizzas.append(pizza)
        
        if self.publisher:
            self.publisher.publish_oven_event(
                oven_id=self.oven_id,
                event_type="pizza_started",
                order_id=order_id,
                pizza_type=pizza_type,
                size=size,
                cook_time=cook_time,
                temperature=self.current_temperature,
                capacity_used=len(self.current_pizzas),
                capacity_total=self.capacity
            )
        
        return True
    
    def _monitor_oven(self):
        """Monitor oven and check for finished pizzas"""
        while self.is_running:
            # Check for finished pizzas
            finished_pizzas = [p for p in self.current_pizzas if p.is_ready]
            
            for pizza in finished_pizzas:
                self.current_pizzas.remove(pizza)
                
                if self.publisher:
                    self.publisher.publish_oven_event(
                        oven_id=self.oven_id,
                        event_type="pizza_finished",
                        order_id=pizza.order_id,
                        pizza_type=pizza.pizza_type,
                        size=pizza.size,
                        actual_cook_time=int((datetime.now() - pizza.start_time).total_seconds()),
                        temperature=self.current_temperature,
                        capacity_used=len(self.current_pizzas),
                        capacity_total=self.capacity
                    )
            
            # Publish current status
            if self.publisher and random.random() < 0.3:  # 30% chance each cycle
                self.publisher.publish_oven_event(
                    oven_id=self.oven_id,
                    event_type="temperature_reading",
                    temperature=self.current_temperature,
                    capacity_used=len(self.current_pizzas),
                    capacity_total=self.capacity,
                    pizzas_cooking=len(self.current_pizzas),
                    door_open=self.door_open,
                    efficiency_score=self._calculate_efficiency()
                )
            
            time.sleep(2)
    
    def _temperature_fluctuation(self):
        """Simulate realistic temperature fluctuations"""
        while self.is_running:
            # Door opening simulation
            if len(self.current_pizzas) > 0 and random.random() < 0.1:  # 10% chance
                self.door_open = True
                # Temperature drops when door opens
                self.current_temperature = max(300, self.current_temperature - random.randint(20, 50))
                time.sleep(1)
                self.door_open = False
            
            # Normal temperature regulation
            temp_diff = self.target_temperature - self.current_temperature
            if abs(temp_diff) > 5:
                adjustment = temp_diff * 0.1 + random.uniform(-2, 2)
                self.current_temperature += adjustment
            else:
                # Small random fluctuations
                self.current_temperature += random.uniform(-3, 3)
            
            # Keep temperature within reasonable bounds
            self.current_temperature = max(200, min(500, self.current_temperature))
            
            time.sleep(5)
    
    def _calculate_efficiency(self) -> float:
        """Calculate oven efficiency based on usage and temperature"""
        capacity_utilization = len(self.current_pizzas) / self.capacity
        temp_efficiency = 1.0 - abs(self.target_temperature - self.current_temperature) / 100
        return min(1.0, (capacity_utilization * 0.7 + temp_efficiency * 0.3))
    
    @property 
    def status(self) -> Dict:
        """Get current oven status"""
        return {
            'oven_id': self.oven_id,
            'temperature': round(self.current_temperature, 1),
            'capacity_used': len(self.current_pizzas),
            'capacity_total': self.capacity,
            'door_open': self.door_open,
            'pizzas': [
                {
                    'order_id': p.order_id,
                    'pizza_type': p.pizza_type,
                    'size': p.size,
                    'time_remaining': p.time_remaining
                } for p in self.current_pizzas
            ],
            'efficiency': self._calculate_efficiency()
        }