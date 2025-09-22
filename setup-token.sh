#!/bin/bash
echo "🍕 Papa Giuseppe's Pizzeria Setup"
echo "================================="

# Step 1: Start only InfluxDB first
echo "📊 Starting InfluxDB 3 Core..."
docker-compose up -d influxdb3-core

echo "⏳ Waiting for InfluxDB to be ready..."
sleep 30

# Check if InfluxDB is healthy
if ! docker-compose ps | grep -q "influxdb3-core.*healthy"; then
    echo "❌ InfluxDB failed to start. Check logs:"
    docker-compose logs influxdb3-core
    exit 1
fi

echo "✅ InfluxDB 3 Core is running!"

# Step 2: Create admin token
echo "🔑 Creating admin token..."
TOKEN=$(docker exec influxdb3-core influxdb3 create token --admin 2>/dev/null | tail -1)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to create token. Trying alternative method..."
    TOKEN=$(docker exec influxdb3-core influxdb3 create token --admin --format json | grep '"token"' | cut -d'"' -f4)
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Could not create token automatically."
    echo "📝 Please run manually:"
    echo "   docker exec influxdb3-core influxdb3 create token --admin"
    echo "   Then copy the token to .env file"
    exit 1
fi

echo "✅ Token created: ${TOKEN:0:20}..."

# Step 3: Update .env file
echo "📝 Updating .env file..."
if [ -f .env ]; then
    # Update existing .env file
    sed -i.bak "s/INFLUXDB_TOKEN=.*/INFLUXDB_TOKEN=$TOKEN/" .env
else
    echo "❌ .env file not found!"
    exit 1
fi

echo "✅ Token saved to .env file"

# Step 4: Create database
echo "🏗️ Creating database..."
docker exec influxdb3-core influxdb3 create database pizzeria_data

# Step 5: Start remaining services
echo "🚀 Starting all services..."
docker-compose --profile with-token up -d

echo ""
echo "🎉 Setup Complete!"
echo "================================="
echo "📊 Dashboard: http://localhost:8080"
echo "📈 InfluxDB: http://localhost:8181"
echo "📝 Your token: $TOKEN"
echo ""
echo "🔧 Useful commands:"
echo "  docker-compose logs -f                    # View all logs"
echo "  docker-compose logs pizzeria-simulator   # View simulator logs"
echo "  docker-compose ps                        # Check service status"
echo ""