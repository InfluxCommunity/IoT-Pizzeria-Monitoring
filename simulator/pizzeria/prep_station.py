import random
import time
import threading
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass

@dataclass 
class PrepOrder:
    order_id: str
    pizza_type: str
    size: str
    start_time: datetime
    prep_time: int
    
    @property
    def is_ready(self) -> bool:
        return (datetime.now() - self.start_time).total_seconds() >= self.prep_time

class PrepStation:
    def __init__(self, station_id: str, publisher=None):
        self.station_id = station_id
        self.publisher = publisher
        self.current_orders: List[PrepOrder] = []
        self.is_running = False
        
        # Prep times by size (in seconds)
        self.prep_times = {
            'small': 120,   # 2 minutes
            'medium': 180,  # 3 minutes
            'large': 240,   # 4 minutes
            'xlarge': 300   # 5 minutes
        }
        
        # Ingredient inventory (starts full)
        self.ingredients = {
            'dough': 100,
            'sauce': 100, 
            'cheese': 100,
            'pepperoni': 80,
            'mushrooms': 60,
            'peppers': 60,
            'ham': 50,
            'pineapple': 40
        }
    
    def start(self):
        """Start the prep station monitoring"""
        self.is_running = True
        threading.Thread(target=self._monitor_prep, daemon=True).start()
        threading.Thread(target=self._restock_ingredients, daemon=True).start()
    
    def stop(self):
        """Stop the prep station"""
        self.is_running = False
    
    def add_order(self, order_id: str, pizza_type: str, size: str) -> bool:
        """Add an order to prep queue"""
        if not self._check_ingredients(pizza_type):
            return False
        
        prep_time = self.prep_times.get(size, 180)
        # Add some randomness
        prep_time += random.randint(-20, 40)
        
        order = PrepOrder(
            order_id=order_id,
            pizza_type=pizza_type,
            size=size, 
            start_time=datetime.now(),
            prep_time=prep_time
        )
        
        self.current_orders.append(order)
        self._use_ingredients(pizza_type)
        
        if self.publisher:
            self.publisher.publish_prep_event(
                station_id=self.station_id,
                event_type="prep_started",
                order_id=order_id,
                pizza_type=pizza_type,
                size=size,
                prep_time=prep_time,
                queue_length=len(self.current_orders)
            )
        
        return True
    
    def _monitor_prep(self):
        """Monitor prep station and complete orders"""
        while self.is_running:
            # Check for completed prep orders
            completed = [o for o in self.current_orders if o.is_ready]
            
            for order in completed:
                self.current_orders.remove(order)
                
                if self.publisher:
                    self.publisher.publish_prep_event(
                        station_id=self.station_id,
                        event_type="prep_completed", 
                        order_id=order.order_id,
                        pizza_type=order.pizza_type,
                        size=order.size,
                        actual_prep_time=int((datetime.now() - order.start_time).total_seconds()),
                        queue_length=len(self.current_orders)
                    )
            
            # Publish status updates
            if self.publisher and random.random() < 0.2:
                low_ingredients = [k for k, v in self.ingredients.items() if v < 20]
                
                self.publisher.publish_prep_event(
                    station_id=self.station_id,
                    event_type="status_update",
                    queue_length=len(self.current_orders),
                    low_ingredients=low_ingredients,
                    total_ingredients=sum(self.ingredients.values()),
                    efficiency_score=self._calculate_efficiency()
                )
            
            time.sleep(3)
    
    def _check_ingredients(self, pizza_type: str) -> bool:
        """Check if we have enough ingredients for this pizza"""
        required = self._get_required_ingredients(pizza_type)
        return all(self.ingredients.get(ing, 0) >= amount for ing, amount in required.items())
    
    def _use_ingredients(self, pizza_type: str):
        """Use ingredients for making pizza"""
        required = self._get_required_ingredients(pizza_type)
        for ingredient, amount in required.items():
            self.ingredients[ingredient] = max(0, self.ingredients[ingredient] - amount)
    
    def _get_required_ingredients(self, pizza_type: str) -> Dict[str, int]:
        """Get required ingredients for pizza type"""
        base = {'dough': 1, 'sauce': 1, 'cheese': 1}
        
        extras = {
            'pepperoni': {'pepperoni': 2},
            'supreme': {'pepperoni': 1, 'mushrooms': 1, 'peppers': 1},
            'hawaiian': {'ham': 2, 'pineapple': 1},
            'veggie': {'mushrooms': 2, 'peppers': 2},
            'meat_lovers': {'pepperoni': 2, 'ham': 1}
        }
        
        result = base.copy()
        result.update(extras.get(pizza_type, {}))
        return result
    
    def _restock_ingredients(self):
        """Periodically restock ingredients"""
        while self.is_running:
            time.sleep(30)  # Restock every 30 seconds
            
            for ingredient in self.ingredients:
                if self.ingredients[ingredient] < 50:
                    restock_amount = random.randint(20, 40)
                    self.ingredients[ingredient] += restock_amount
                    
                    if self.publisher:
                        self.publisher.publish_prep_event(
                            station_id=self.station_id,
                            event_type="ingredient_restocked",
                            ingredient=ingredient,
                            amount_added=restock_amount,
                            new_total=self.ingredients[ingredient]
                        )
    
    def _calculate_efficiency(self) -> float:
        """Calculate prep station efficiency"""
        # Based on queue length and ingredient levels
        queue_efficiency = 1.0 if len(self.current_orders) < 3 else 0.5
        ingredient_efficiency = min(self.ingredients.values()) / 100
        return min(1.0, (queue_efficiency + ingredient_efficiency) / 2)
    
    @property
    def status(self) -> Dict:
        """Get current prep station status"""
        return {
            'station_id': self.station_id,
            'queue_length': len(self.current_orders),
            'ingredients': self.ingredients.copy(),
            'current_orders': [
                {
                    'order_id': o.order_id,
                    'pizza_type': o.pizza_type,
                    'size': o.size,
                    'time_remaining': max(0, o.prep_time - int((datetime.now() - o.start_time).total_seconds()))
                } for o in self.current_orders
            ],
            'efficiency': self._calculate_efficiency()
        }