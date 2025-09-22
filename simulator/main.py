# Initialize equipment
import logging
import time
import signal
import sys
from pizzeria.data_publisher import PizzeriaDataPublisher
from pizzeria.pizza_oven import PizzaOven
from pizzeria.prep_station import PrepStation  
from pizzeria.order_manager import OrderManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PizzeriaSimulator:
    def __init__(self):
        self.publisher = PizzeriaDataPublisher()
        self.ovens = [
            PizzaOven("oven_1", capacity=4, publisher=self.publisher),
            PizzaOven("oven_2", capacity=3, publisher=self.publisher),
            PizzaOven("oven_3", capacity=2, publisher=self.publisher)
        ]
        
        self.prep_stations = [
            PrepStation("prep_1", publisher=self.publisher),
            PrepStation("prep_2", publisher=self.publisher)
        ]
        
        # Initialize order manager
        self.order_manager = OrderManager(
            publisher=self.publisher,
            prep_stations=self.prep_stations,
            ovens=self.ovens
        )
        
        self.running = False
        
    def start(self):
        """Start the pizzeria simulation"""
        logger.info("🍕 Starting Papa Giuseppe's Pizzeria Simulation...")
        
        self.running = True
        
        # Start all equipment
        for oven in self.ovens:
            oven.start()
            
        for station in self.prep_stations:
            station.start()
            
        # Start order management
        self.order_manager.start()
        
        logger.info("✅ Pizzeria simulation started!")
        logger.info("📊 Data is being published to Kafka topic: pizzeria.events")
        logger.info("🏪 Kitchen Status:")
        logger.info(f"   - {len(self.ovens)} Pizza Ovens")
        logger.info(f"   - {len(self.prep_stations)} Prep Stations")
        logger.info("   - Order Management System Active")
        
        # Keep running
        try:
            while self.running:
                time.sleep(10)
                self._log_status()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the simulation"""
        logger.info("🛑 Stopping pizzeria simulation...")
        
        self.running = False
        
        # Stop all equipment
        for oven in self.ovens:
            oven.stop()
            
        for station in self.prep_stations:
            station.stop()
            
        self.order_manager.stop()
        
        logger.info("✅ Pizzeria simulation stopped")
    
    def _log_status(self):
        """Log current status"""
        total_pizzas_cooking = sum(len(oven.current_pizzas) for oven in self.ovens)
        total_orders_prepping = sum(len(station.current_orders) for station in self.prep_stations)
        
        logger.info(f"🍕 Status: {total_pizzas_cooking} pizzas cooking, {total_orders_prepping} orders in prep")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    if 'simulator' in globals():
        simulator.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start simulator
    simulator = PizzeriaSimulator()
    simulator.start()