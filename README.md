# Realtime Data Pipeline with Kafka, Telegraf & InfluxDB 3 Core

A sample app, demonstrating streaming data pipeline using a Pizza kitchen monitoring system as an example. 

Each component handles a specific part of the data pipeline:
- **Kafka** provides reliable message streaming
- **Telegraf** transforms and routes data efficiently  
- **InfluxDB 3 Core** optimizes time-series storage and querying
- **Custom Dashboard** visualizes real-time metrics

This pattern scales from simple monitoring to enterprise data processing.

## Architecture

```
Python Simulator → Kafka Topics → Telegraf Processing → InfluxDB 3 Core → Custom Web Dashboard
```

## Open Source Tech Stack

- **Kafka** - Message streaming
- **Telegraf** - Data collection and processing  
- **InfluxDB 3 Core** - Leading Timeseries database
- **Docker** - Container deployment
- **Python** - Data simulation and dashboard
- **FastAPI** - Web backend in Python

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB+ RAM available
- Ports 8080, 8181, 9092 free

### Setup Steps

1. **Clone and configure**
```bash
git clone <repository>
cd pizzeria-pipeline
cp .env.example .env
```

2. **Start InfluxDB**
```bash
docker-compose up -d influxdb3-core
```

3. **Create authentication token**
```bash
docker exec influxdb3-core influxdb3 create token --admin
```

4. **Update .env file with token**
```bash
INFLUXDB_TOKEN=your_generated_token_here
```

5. **Create database**
```bash
docker exec influxdb3-core influxdb3 create database pizzeria_data --token "your_token"
```

6. **Start all services**
```bash
docker-compose --profile with-token up -d
```

7. **Access dashboard**
Open http://localhost:8080

## Project Structure

```
├── docker-compose.yml       # Service definitions
├── .env                     # Configuration
├── simulator/               # Python data generator
├── dashboard/               # Web interface
├── telegraf/               # Data processing config
└── queries/                # Sample InfluxDB queries
```

## Testing the Pipeline

### Check data flow
```bash
# Verify Kafka messages
docker exec -it pizzeria-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic pizzeria.events

# Check Telegraf processing
docker-compose logs telegraf

# Query stored data
docker exec influxdb3-core influxdb3 query \
  --database pizzeria_data \
  --token "your_token" \
  "SELECT COUNT(*) FROM pizzeria_event"
```

### Dashboard features
- Live metrics (active orders, completion times)
- Equipment monitoring (oven temperatures, capacity)
- Interactive controls (rush mode, simulation speed)
- Real-time order tracking

## Configuration

### Data Schema
```json
{
  "measurement": "pizzeria_event",
  "equipment_id": "oven_1",
  "equipment_type": "pizza_oven",
  "event_type": "temperature_reading",
  "temperature": 450.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Telegraf Pipeline
- Consumes JSON from Kafka topic `pizzeria.events`
- Extracts tags for efficient querying
- Writes to InfluxDB with proper data types

## Sample Queries

```sql
-- Current oven temperatures
SELECT equipment_id, temperature 
FROM pizzeria_event 
WHERE equipment_type = 'pizza_oven'
AND time >= now() - interval '5 minutes';

-- Order volume by hour
SELECT DATE_TRUNC('hour', time) as hour, COUNT(*) as orders
FROM pizzeria_event
WHERE event_type = 'order_created'
GROUP BY hour;
```

## Troubleshooting

### Common Issues

**Services won't start**
- Check `docker-compose ps` for status
- View logs with `docker-compose logs [service-name]`

**No data flowing**
- Verify simulator is running: `docker-compose logs pizzeria-simulator`
- Check Kafka topic exists: `docker exec pizzeria-kafka kafka-topics --list --bootstrap-server localhost:9092`

**Authentication errors**
- Confirm token is correctly set in .env file
- Test token: `curl -H "Authorization: Bearer your_token" http://localhost:8181/health`

**Dashboard shows no metrics**
- Wait 2-3 minutes for data to flow through pipeline
- Check InfluxDB has data with sample query above

### Stop Everything
```bash
docker-compose down -v
```
