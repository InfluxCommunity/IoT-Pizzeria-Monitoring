"""
Sample queries to explore the pizzeria data in InfluxDB 3 Core
Run these queries to understand your data and create insights
"""

from influxdb_client import InfluxDBClient
import os

# Configuration
INFLUXDB_URL = f"http://{os.getenv('INFLUXDB_HOST', 'localhost')}:8181"
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'your-token-here')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'papa_giuseppe')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'pizzeria_data')

def get_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

def run_sample_queries():
    client = get_client()
    query_api = client.query_api()
    
    queries = {
        "Current Oven Temperatures": f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r._measurement == "pizzeria_event")
          |> filter(fn: (r) => r.equipment_type == "pizza_oven")
          |> filter(fn: (r) => r.event_type == "temperature_reading")
          |> filter(fn: (r) => r._field == "temperature")
          |> last()
        ''',
        
        "Hourly Order Volume": f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "pizzeria_event")
          |> filter(fn: (r) => r.equipment_type == "order_manager")
          |> filter(fn: (r) => r.event_type == "order_created")
          |> aggregateWindow(every: 1h, fn: count)
        ''',
        
        "Average Cook Time by Pizza Size": f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "pizzeria_event")
          |> filter(fn: (r) => r.equipment_type == "pizza_oven")
          |> filter(fn: (r) => r.event_type == "pizza_finished")
          |> filter(fn: (r) => r._field == "actual_cook_time")
          |> group(columns: ["size"])
          |> mean()
        ''',
        
        "Most Popular Pizza Types": f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "pizzeria_event")
          |> filter(fn: (r) => r.equipment_type == "order_manager")
          |> filter(fn: (r) => r.event_type == "order_created")
          |> group(columns: ["pizza_type"])
          |> count()
          |> sort(columns: ["_value"], desc: true)
        ''',
        
        "Oven Efficiency Over Time": f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -2h)
          |> filter(fn: (r) => r._measurement == "pizzeria_event")
          |> filter(fn: (r) => r.equipment_type == "pizza_oven")
          |> filter(fn: (r) => r._field == "efficiency_score")
          |> aggregateWindow(every: 10m, fn: mean)
        '''
    }
    
    print("🍕 Papa Giuseppe's Pizzeria - Data Analysis")
    print("=" * 50)
    
    for title, query in queries.items():
        print(f"\n📊 {title}")
        print("-" * 30)
        
        try:
            result = query_api.query(query)
            
            for table in result:
                for record in table.records:
                    time = record.get_time()
                    value = record.get_value()
                    field = record.get_field()
                    
                    # Extract relevant tags
                    tags = []
                    if 'equipment_id' in record.values:
                        tags.append(f"Equipment: {record.values['equipment_id']}")
                    if 'pizza_type' in record.values:
                        tags.append(f"Type: {record.values['pizza_type']}")
                    if 'size' in record.values:
                        tags.append(f"Size: {record.values['size']}")
                    
                    tag_str = " | ".join(tags) if tags else ""
                    
                    print(f"  {time}: {field} = {value} {tag_str}")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    client.close()

if __name__ == "__main__":
    run_sample_queries()