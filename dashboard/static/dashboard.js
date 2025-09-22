class PizzeriaDashboard {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 3000;
    this.lastUpdateTime = null;

    this.initializeWebSocket();
    this.setupControlHandlers();
    this.setupUI();
  }

  initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupWebSocketHandlers();
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.updateConnectionStatus('error', 'Connection failed');
    }
  }

  setupWebSocketHandlers() {
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.updateConnectionStatus('online', 'Connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleDashboardUpdate(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.updateConnectionStatus('offline', 'Disconnected');
      this.attemptReconnection();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.updateConnectionStatus('error', 'Connection error');
    };
  }

  attemptReconnection() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.updateConnectionStatus('offline', `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.initializeWebSocket();
      }, this.reconnectDelay);
    } else {
      this.updateConnectionStatus('error', 'Connection failed');
      this.showNotification('Connection lost. Please refresh the page.', 'error');
    }
  }

  updateConnectionStatus(status, text) {
    const indicator = document.getElementById('connection-indicator');
    const statusText = document.getElementById('connection-text');

    indicator.className = `status-dot ${status}`;
    statusText.textContent = text;
  }

  setupControlHandlers() {
    // Rush mode toggle
    document.getElementById('rush-mode-toggle').addEventListener('change', (e) => {
      this.sendControlMessage('toggle_rush_mode');
    });

    // Equipment failure toggle
    document.getElementById('equipment-failure-toggle').addEventListener('change', (e) => {
      this.sendControlMessage('toggle_equipment_failure');
    });

    // New orders toggle
    document.getElementById('new-orders-toggle').addEventListener('change', (e) => {
      this.sendControlMessage('toggle_new_orders');
    });

    // Speed control
    const speedControl = document.getElementById('speed-control');
    const speedValue = document.getElementById('speed-value');

    speedControl.addEventListener('input', (e) => {
      const speed = parseFloat(e.target.value);
      speedValue.textContent = `${speed}x`;
      this.sendControlMessage('set_speed', speed);
    });
  }

  sendControlMessage(action, value = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'control',
        action: action
      };

      if (value !== null) {
        message.value = value;
      }

      this.ws.send(JSON.stringify(message));
    }
  }

  setupUI() {
    // Add click handlers for metric cards (for interactivity)
    document.querySelectorAll('.metric-card').forEach(card => {
      card.addEventListener('click', () => {
        card.classList.add('updating');
        setTimeout(() => card.classList.remove('updating'), 500);
      });
    });
  }

  handleDashboardUpdate(data) {
    try {
      this.lastUpdateTime = new Date();

      if (data.error) {
        console.error('Dashboard data error:', data.error);
        this.showNotification('Data update error: ' + data.error, 'error');
        return;
      }

      // Update metrics
      if (data.metrics) {
        this.updateMetrics(data.metrics);
      }

      // Update ovens
      if (data.ovens) {
        this.updateOvens(data.ovens);
      }

      // Update recent orders
      if (data.recent_orders) {
        this.updateRecentOrders(data.recent_orders);
      }

      // Update simulation controls
      if (data.simulation_controls) {
        this.updateControlsState(data.simulation_controls);
      }

      // Update pipeline status based on data freshness
      this.updatePipelineStatus(data);

    } catch (error) {
      console.error('Error handling dashboard update:', error);
    }
  }

  updateMetrics(metrics) {
    // Active orders
    this.animateValueUpdate('active-orders', metrics.active_orders || 0);

    // Completed orders
    this.animateValueUpdate('completed-orders', metrics.completed_orders || 0);

    // Average completion time (convert seconds to minutes)
    const avgMinutes = Math.round((metrics.avg_completion_time || 0) / 60 * 10) / 10;
    this.animateValueUpdate('avg-time', avgMinutes);

    // Rush hour indicator
    const rushIndicator = document.getElementById('rush-indicator');
    const rushStatus = document.getElementById('rush-status');

    if (metrics.rush_hour) {
      rushIndicator.classList.add('active');
      rushStatus.textContent = 'Rush Hour';
    } else {
      rushIndicator.classList.remove('active');
      rushStatus.textContent = 'Normal';
    }
  }

  updateOvens(ovens) {
    const container = document.getElementById('ovens-container');

    // Clear existing ovens
    container.innerHTML = '';

    ovens.forEach(oven => {
      const ovenCard = this.createOvenCard(oven);
      container.appendChild(ovenCard);
    });
  }

  createOvenCard(oven) {
    const card = document.createElement('div');
    card.className = 'oven-card';

    // Add temperature-based styling
    if (oven.temperature > 470) {
      card.classList.add('high-temp');
    } else if (oven.temperature < 400) {
      card.classList.add('low-temp');
    }

    const capacityPercentage = (oven.capacity_used / oven.capacity_total) * 100;

    card.innerHTML = `
            <div class="oven-header">
                <div class="oven-title">🔥 ${oven.oven_id.replace('_', ' ').toUpperCase()}</div>
                <div class="oven-temp">${oven.temperature}°F</div>
            </div>
            <div class="oven-capacity">
                <span>Capacity:</span>
                <div class="capacity-bar">
                    <div class="capacity-fill" style="width: ${capacityPercentage}%"></div>
                </div>
                <span>${oven.capacity_used}/${oven.capacity_total}</span>
            </div>
            <div class="oven-efficiency">
                <strong>Efficiency:</strong> ${Math.round(oven.efficiency * 100)}%
            </div>
        `;

    return card;
  }

  updateRecentOrders(orders) {
    const tbody = document.getElementById('orders-list');
    tbody.innerHTML = '';

    // Sort orders by timestamp (most recent first)
    const sortedOrders = orders
      .filter(order => order.order_id)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 10);

    sortedOrders.forEach(order => {
      const row = this.createOrderRow(order);
      tbody.appendChild(row);
    });
  }

  createOrderRow(order) {
    const row = document.createElement('tr');

    const formatDuration = (seconds) => {
      if (!seconds) return '-';
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    };

    const formatTime = (timestamp) => {
      if (!timestamp) return '-';
      return new Date(timestamp).toLocaleTimeString();
    };

    const formatPizzaType = (type) => {
      return type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    row.innerHTML = `
            <td>${order.order_id}</td>
            <td>${formatPizzaType(order.pizza_type)}</td>
            <td>${order.size.toUpperCase()}</td>
            <td><span class="status-badge status-${order.status}">${order.status.toUpperCase()}</span></td>
            <td>${formatDuration(order.duration)}</td>
            <td>${formatTime(order.timestamp)}</td>
        `;

    return row;
  }

  updateControlsState(controls) {
    // Update toggle states without triggering events
    const rushToggle = document.getElementById('rush-mode-toggle');
    const equipmentToggle = document.getElementById('equipment-failure-toggle');
    const ordersToggle = document.getElementById('new-orders-toggle');
    const speedControl = document.getElementById('speed-control');
    const speedValue = document.getElementById('speed-value');

    rushToggle.checked = controls.rush_mode || false;
    equipmentToggle.checked = controls.equipment_failure || false;
    ordersToggle.checked = controls.new_orders_enabled !== false;
    speedControl.value = controls.speed_multiplier || 1.0;
    speedValue.textContent = `${controls.speed_multiplier || 1.0}x`;
  }

  updatePipelineStatus(data) {
    const now = new Date();
    const dataAge = this.lastUpdateTime ? now - this.lastUpdateTime : 0;

    // Update status based on data freshness and content
    const simulatorStatus = document.getElementById('simulator-status');
    const kafkaStatus = document.getElementById('kafka-status');
    const telegrafStatus = document.getElementById('telegraf-status');
    const influxdbStatus = document.getElementById('influxdb-status');

    // Simulator status
    if (data.ovens && data.ovens.length > 0) {
      this.updateStepStatus(simulatorStatus, 'active', 'Active');
    } else {
      this.updateStepStatus(simulatorStatus, 'warning', 'No Data');
    }

    // Kafka status (inferred from data flow)
    if (data.recent_orders && data.recent_orders.length > 0) {
      this.updateStepStatus(kafkaStatus, 'active', 'Active');
    } else {
      this.updateStepStatus(kafkaStatus, 'warning', 'No Messages');
    }

    // Telegraf status (inferred from data processing)
    if (data.metrics) {
      this.updateStepStatus(telegrafStatus, 'active', 'Processing');
    } else {
      this.updateStepStatus(telegrafStatus, 'warning', 'No Processing');
    }

    // InfluxDB status
    if (data.status === 'connected' && dataAge < 30000) {
      this.updateStepStatus(influxdbStatus, 'active', 'Connected');
    } else {
      this.updateStepStatus(influxdbStatus, 'inactive', 'Disconnected');
    }
  }

  updateStepStatus(element, status, text) {
    element.className = `step-status ${status}`;
    element.textContent = text;
  }

  animateValueUpdate(elementId, newValue) {
    const element = document.getElementById(elementId);
    const currentValue = parseInt(element.textContent) || 0;

    if (currentValue !== newValue) {
      element.parentElement.classList.add('updating');
      element.textContent = newValue;
      setTimeout(() => {
        element.parentElement.classList.remove('updating');
      }, 500);
    }
  }

  showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());

    // Create new notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => notification.classList.add('show'), 100);

    // Hide notification after 5 seconds
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 300);
    }, 5000);
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.dashboard = new PizzeriaDashboard();
});

// Add some fun interactions
document.addEventListener('DOMContentLoaded', () => {
  // Add pizza emoji rain effect when rush mode is enabled
  let pizzaRain = null;

  function startPizzaRain() {
    if (pizzaRain) return;

    pizzaRain = setInterval(() => {
      createFallingPizza();
    }, 500);
  }

  function stopPizzaRain() {
    if (pizzaRain) {
      clearInterval(pizzaRain);
      pizzaRain = null;
    }
  }

  function createFallingPizza() {
    const pizza = document.createElement('div');
    pizza.innerHTML = '🍕';
    pizza.style.position = 'fixed';
    pizza.style.top = '-50px';
    pizza.style.left = Math.random() * window.innerWidth + 'px';
    pizza.style.fontSize = '20px';
    pizza.style.zIndex = '9999';
    pizza.style.pointerEvents = 'none';
    pizza.style.transition = 'transform 3s linear';

    document.body.appendChild(pizza);

    setTimeout(() => {
      pizza.style.transform = 'translateY(' + (window.innerHeight + 100) + 'px) rotate(360deg)';
    }, 100);

    setTimeout(() => pizza.remove(), 3000);
  }

  // Listen for rush mode changes
  document.getElementById('rush-mode-toggle').addEventListener('change', (e) => {
    if (e.target.checked) {
      startPizzaRain();
    } else {
      stopPizzaRain();
    }
  });
});