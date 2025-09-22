import random
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from config import config

class OrderStatus(Enum):
    RECEIVED = "received"
    PREP = "prep" 
    BAKING = "baking"
    READY = "ready"
    DELIVERED = "delivered"

@dataclass
class Order:
    order_id: str
    pizza_type: str
    size: str
    status: OrderStatus = OrderStatus.RECEIVED
    created_at: datetime = field(default_factory=datetime.now)
    prep_start: Optional[datetime] = None
    baking_start: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    @property
    def total_time(self) -> Optional[int]:
        """Total order time in seconds"""
        if self.delivered_at:
            return int((self.delivered_at - self.created_at).total_seconds())
        return None
    
    @property
    def current_duration(self) -> int:
        """Current order duration in seconds"""
        return int((datetime.now() - self.created_at).total_seconds())

class OrderManager:
    def __init__(self, publisher=None, prep_stations=None, ovens=None):
        self.publisher = publisher
        self.prep_stations = prep_stations or []
        self.ovens = ovens or []
        self.orders: Dict[str, Order] = {}
        self.order_counter = 1
        self.is_running = False
        
        # Rush hour settings
        self.rush_hours = [(11, 14), (17, 21)]  # 11am-2pm, 5pm-9pm
        
    def start(self):
        """Start the order management system"""
        self.is_running = True
        threading.Thread(target=self._generate_orders, daemon=True).start()
        threading.Thread(target=self._process_orders, daemon=True).start()
        threading.Thread(target=self._publish_metrics, daemon=True).start()
    
    def stop(self):
        """Stop the order manager"""
        self.is_running = False
    
    def _generate_orders(self):
        """Generate new orders based on time of day"""
        while self.is_running:
            current_hour = datetime.now().hour
            
            # Determine if it's rush hour
            is_rush_hour = any(start <= current_hour < end for start, end in self.rush_hours)
            
            # Calculate order rate
            base_rate = config.base_orders_per_minute
            if is_rush_hour:
                order_rate = base_rate * config.rush_hour_multiplier
            else:
                order_rate = base_rate
            
            # Convert to seconds between orders  
            seconds_between_orders = 60 / order_rate if order_rate > 0 else 60
            
            # Add some randomness
            wait_time = seconds_between_orders + random.uniform(-10, 20)
            wait_time = max(5, wait_time)  # Minimum 5 seconds between orders
            
            time.sleep(wait_time)
            
            # Create new order
            if random.random() < 0.8:  # 80% chance to actually create order
                self._create_order()
    
    def _create_order(self):
        """Create a new pizza order"""
        order_id = f"ORD-{self.order_counter:04d}"
        self.order_counter += 1
        
        pizza_type = random.choice(config.pizza_types)
        size = random.choice(config.pizza_sizes)
        
        order = Order(
            order_id=order_id,
            pizza_type=pizza_type,
            size=size
        )
        
        self.orders[order_id] = order
        
        if self.publisher:
            self.publisher.publish_order_event(
                event_type="order_created",
                order_id=order_id,
                pizza_type=pizza_type,
                size=size,
                status=order.status.value,
                estimated_total_time=self._estimate_total_time(pizza_type, size),
                current_queue_length=len([o for o in self.orders.values() if o.status != OrderStatus.DELIVERED])
            )
        
        print(f"🍕 New Order: {order_id} - {size} {pizza_type}")
    
    def _process_orders(self):
        """Process orders through the pipeline"""
        while self.is_running:
            # Move orders from RECEIVED to PREP
            received_orders = [o for o in self.orders.values() if o.status == OrderStatus.RECEIVED]
            for order in received_orders[:2]:  # Process max 2 at a time
                if self._send_to_prep(order):
                    order.status = OrderStatus.PREP
                    order.prep_start = datetime.now()
                    
                    if self.publisher:
                        self.publisher.publish_order_event(
                            event_type="order_status_update",
                            order_id=order.order_id,
                            pizza_type=order.pizza_type,
                            size=order.size,
                            status=order.status.value,
                            duration=order.current_duration
                        )
            
            # Move orders from PREP to BAKING
            prep_orders = [o for o in self.orders.values() if o.status == OrderStatus.PREP]
            for order in prep_orders:
                if self._send_to_oven(order):
                    order.status = OrderStatus.BAKING
                    order.baking_start = datetime.now()
                    
                    if self.publisher:
                        self.publisher.publish_order_event(
                            event_type="order_status_update",
                            order_id=order.order_id,
                            pizza_type=order.pizza_type,
                            size=order.size,
                            status=order.status.value,
                            duration=order.current_duration
                        )
            
            # Check for finished pizzas
            baking_orders = [o for o in self.orders.values() if o.status == OrderStatus.BAKING]
            for order in baking_orders:
                # Check if any oven has finished this pizza (simplified check)
                if random.random() < 0.05:  # 5% chance per cycle that pizza is done
                    order.status = OrderStatus.READY
                    order.ready_at = datetime.now()
                    
                    if self.publisher:
                        self.publisher.publish_order_event(
                            event_type="order_status_update",
                            order_id=order.order_id,
                            pizza_type=order.pizza_type,
                            size=order.size,
                            status=order.status.value,
                            duration=order.current_duration
                        )
            
            # Simulate customer pickup/delivery
            ready_orders = [o for o in self.orders.values() if o.status == OrderStatus.READY]
            for order in ready_orders:
                # Orders get picked up after being ready for 2-10 minutes
                if order.ready_at and (datetime.now() - order.ready_at).total_seconds() > random.randint(120, 600):
                    order.status = OrderStatus.DELIVERED
                    order.delivered_at = datetime.now()
                    
                    if self.publisher:
                        self.publisher.publish_order_event(
                            event_type="order_delivered",
                            order_id=order.order_id,
                            pizza_type=order.pizza_type,
                            size=order.size,
                            status=order.status.value,
                            total_time=order.total_time,
                            duration=order.current_duration
                        )
                    
                    print(f"✅ Delivered: {order.order_id} - Total time: {order.total_time}s")
            
            time.sleep(5)
    
    def _send_to_prep(self, order: Order) -> bool:
        """Try to send order to prep station"""
        for station in self.prep_stations:
            if station.add_order(order.order_id, order.pizza_type, order.size):
                return True
        return False
    
    def _send_to_oven(self, order: Order) -> bool:
        """Try to send order to oven"""
        for oven in self.ovens:
            if oven.add_pizza(order.order_id, order.pizza_type, order.size):
                return True
        return False
    
    def _estimate_total_time(self, pizza_type: str, size: str) -> int:
        """Estimate total order time"""
        prep_time = {'small': 120, 'medium': 180, 'large': 240, 'xlarge': 300}.get(size, 180)
        cook_time = {'small': 480, 'medium': 600, 'large': 720, 'xlarge': 900}.get(size, 600)
        return prep_time + cook_time + random.randint(60, 180)  # Add queue time
    
    def _publish_metrics(self):
        """Publish periodic metrics"""
        while self.is_running:
            active_orders = [o for o in self.orders.values() if o.status != OrderStatus.DELIVERED]
            completed_orders = [o for o in self.orders.values() if o.status == OrderStatus.DELIVERED]
            
            # Calculate metrics
            avg_completion_time = 0
            if completed_orders:
                times = [o.total_time for o in completed_orders if o.total_time]
                avg_completion_time = sum(times) / len(times) if times else 0
            
            orders_by_status = {}
            for status in OrderStatus:
                count = len([o for o in self.orders.values() if o.status == status])
                orders_by_status[status.value] = count
            
            if self.publisher:
                self.publisher.publish_order_event(
                    event_type="metrics_update",
                    active_orders=len(active_orders),
                    completed_orders=len(completed_orders),
                    avg_completion_time=round(avg_completion_time, 1),
                    orders_by_status=orders_by_status,
                    total_orders_today=len(self.orders),
                    current_hour_rush=any(start <= datetime.now().hour < end for start, end in self.rush_hours)
                )
            
            time.sleep(10)
    
    @property
    def status(self) -> Dict:
        """Get current order management status"""
        active_orders = [o for o in self.orders.values() if o.status != OrderStatus.DELIVERED]
        
        return {
            'active_orders': len(active_orders),
            'total_orders': len(self.orders),
            'orders_by_status': {
                status.value: len([o for o in self.orders.values() if o.status == status])
                for status in OrderStatus
            },
            'recent_orders': [
                {
                    'order_id': o.order_id,
                    'pizza_type': o.pizza_type,
                    'size': o.size,
                    'status': o.status.value,
                    'duration': o.current_duration
                } for o in sorted(active_orders, key=lambda x: x.created_at, reverse=True)[:10]
            ]
        }