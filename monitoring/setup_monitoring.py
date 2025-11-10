#!/usr/bin/env python3
"""
Monitoring Setup for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module sets up comprehensive monitoring for the photo extraction system,
including performance metrics, resource monitoring, and alerting.

Usage:
    python setup_monitoring.py [--config PATH] [--output PATH] [--mode MODE]
"""

import sys
import os
import json
import time
import argparse
import traceback
import threading
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import statistics
import psutil
import subprocess

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config
    from utils.logging_utils import create_logger
    from scripts.auto_extract_photos_from_databasejp_v2 import AdvancedPhotoExtractor
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class MonitoringConfig:
    """Configuration for monitoring system"""
    enable_performance_monitoring: bool = True
    enable_resource_monitoring: bool = True
    enable_alerting: bool = True
    enable_dashboard: bool = False
    monitoring_interval_seconds: float = 5.0
    metrics_retention_days: int = 7
    alert_thresholds: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'cpu_percent': 80.0,
                'memory_percent': 85.0,
                'disk_usage_percent': 90.0,
                'error_rate_percent': 5.0,
                'response_time_seconds': 2.0
            }


@dataclass
class MonitoringMetrics:
    """Collected monitoring metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_mb: float
    disk_percent: float
    active_connections: int
    cache_hit_rate: float
    extraction_rate: float
    error_rate: float
    avg_response_time: float
    queue_size: int


class MonitoringSystem:
    """Comprehensive monitoring system for photo extraction"""
    
    def __init__(self, config: PhotoExtractionConfig, monitoring_config: MonitoringConfig, 
                 output_dir: Path = None):
        self.config = config
        self.monitoring_config = monitoring_config
        self.output_dir = output_dir or Path("monitoring_data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("MonitoringSystem", config)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.metrics_history: List[MonitoringMetrics] = []
        self.alerts_history: List[Dict[str, Any]] = []
        
        # System components for monitoring
        self.extractor = None
        self.performance_metrics = {}
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        
        self.logger.info("Monitoring system initialized")
    
    def setup_components(self):
        """Setup system components for monitoring"""
        try:
            self.extractor = AdvancedPhotoExtractor(self.config)
            self.logger.info("Components setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup components: {e}")
            return False
    
    def start_monitoring(self):
        """Start monitoring system"""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Monitoring system started")
    
    def stop_monitoring(self):
        """Stop monitoring system"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10.0)
        
        self.logger.info("Monitoring system stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        self.logger.info("Monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                # Store metrics
                self.metrics_history.append(metrics)
                
                # Check for alerts
                if self.monitoring_config.enable_alerting:
                    self._check_alerts(metrics)
                
                # Cleanup old metrics
                self._cleanup_old_metrics()
                
                # Sleep until next collection
                time.sleep(self.monitoring_config.monitoring_interval_seconds)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_config.monitoring_interval_seconds)
        
        self.logger.info("Monitoring loop stopped")
    
    def _collect_metrics(self) -> MonitoringMetrics:
        """Collect current system metrics"""
        try:
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1.0)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            # Application metrics (would be collected from actual running system)
            active_connections = self.performance_metrics.get('active_connections', 0)
            cache_hit_rate = self.performance_metrics.get('cache_hit_rate', 0.0)
            extraction_rate = self.performance_metrics.get('extraction_rate', 0.0)
            error_rate = self.performance_metrics.get('error_rate', 0.0)
            avg_response_time = self.performance_metrics.get('avg_response_time', 0.0)
            queue_size = self.performance_metrics.get('queue_size', 0)
            
            metrics = MonitoringMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory.used / (1024 * 1024),
                memory_percent=memory.percent,
                disk_usage_mb=disk.used / (1024 * 1024),
                disk_percent=(disk.used / disk.total) * 100 if disk.total > 0 else 0,
                active_connections=active_connections,
                cache_hit_rate=cache_hit_rate,
                extraction_rate=extraction_rate,
                error_rate=error_rate,
                avg_response_time=avg_response_time,
                queue_size=queue_size
            )
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            # Return default metrics on error
            return MonitoringMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0, memory_mb=0.0, memory_percent=0.0,
                disk_usage_mb=0.0, disk_percent=0.0, active_connections=0,
                cache_hit_rate=0.0, extraction_rate=0.0, error_rate=0.0,
                avg_response_time=0.0, queue_size=0
            )
    
    def _check_alerts(self, metrics: MonitoringMetrics):
        """Check for alert conditions"""
        alerts = []
        thresholds = self.monitoring_config.alert_thresholds
        
        # CPU alert
        if metrics.cpu_percent > thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"High CPU usage: {metrics.cpu_percent:.1f}%",
                'timestamp': metrics.timestamp.isoformat(),
                'value': metrics.cpu_percent,
                'threshold': thresholds['cpu_percent']
            })
        
        # Memory alert
        if metrics.memory_percent > thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"High memory usage: {metrics.memory_percent:.1f}%",
                'timestamp': metrics.timestamp.isoformat(),
                'value': metrics.memory_percent,
                'threshold': thresholds['memory_percent']
            })
        
        # Disk alert
        if metrics.disk_percent > thresholds['disk_usage_percent']:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f"High disk usage: {metrics.disk_percent:.1f}%",
                'timestamp': metrics.timestamp.isoformat(),
                'value': metrics.disk_percent,
                'threshold': thresholds['disk_usage_percent']
            })
        
        # Error rate alert
        if metrics.error_rate > thresholds['error_rate_percent']:
            alerts.append({
                'type': 'error_rate_high',
                'severity': 'critical',
                'message': f"High error rate: {metrics.error_rate:.1f}%",
                'timestamp': metrics.timestamp.isoformat(),
                'value': metrics.error_rate,
                'threshold': thresholds['error_rate_percent']
            })
        
        # Response time alert
        if metrics.avg_response_time > thresholds['response_time_seconds']:
            alerts.append({
                'type': 'response_time_high',
                'severity': 'warning',
                'message': f"High response time: {metrics.avg_response_time:.2f}s",
                'timestamp': metrics.timestamp.isoformat(),
                'value': metrics.avg_response_time,
                'threshold': thresholds['response_time_seconds']
            })
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _process_alert(self, alert: Dict[str, Any]):
        """Process an alert"""
        # Store alert
        self.alerts_history.append(alert)
        
        # Log alert
        severity = alert['severity'].upper()
        self.logger.warning(f"ALERT [{severity}]: {alert['message']}")
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics based on retention policy"""
        if not self.metrics_history:
            return
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=self.monitoring_config.metrics_retention_days)
        
        # Remove old metrics
        original_count = len(self.metrics_history)
        self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_date]
        removed_count = original_count - len(self.metrics_history)
        
        if removed_count > 0:
            self.logger.debug(f"Cleaned up {removed_count} old metrics records")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[MonitoringMetrics]:
        """Get most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 24) -> List[MonitoringMetrics]:
        """Get metrics history for specified hours"""
        if not self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for metrics"""
        recent_metrics = self.get_metrics_history(hours)
        
        if not recent_metrics:
            return {}
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        error_rates = [m.error_rate for m in recent_metrics]
        response_times = [m.avg_response_time for m in recent_metrics]
        
        return {
            'period_hours': hours,
            'samples_count': len(recent_metrics),
            'time_range': {
                'start': recent_metrics[0].timestamp.isoformat(),
                'end': recent_metrics[-1].timestamp.isoformat()
            },
            'cpu': {
                'avg': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'current': cpu_values[-1] if cpu_values else 0
            },
            'memory': {
                'avg': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'current': memory_values[-1] if memory_values else 0
            },
            'performance': {
                'avg_error_rate': statistics.mean(error_rates),
                'max_error_rate': max(error_rates),
                'avg_response_time': statistics.mean(response_times),
                'max_response_time': max(response_times),
                'current_response_time': response_times[-1] if response_times else 0
            },
            'alerts': {
                'total_count': len([a for a in self.alerts_history 
                                  if datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=hours)]),
                'by_type': {}
            }
        }
    
    def save_metrics_data(self, filename: str = None) -> bool:
        """Save metrics data to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monitoring_metrics_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        try:
            # Convert metrics to serializable format
            serializable_metrics = [asdict(m) for m in self.metrics_history]
            serializable_alerts = self.alerts_history
            
            # Convert datetime objects to ISO strings
            for m in serializable_metrics:
                m['timestamp'] = m['timestamp'].isoformat()
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_config': asdict(self.monitoring_config),
                'metrics': serializable_metrics,
                'alerts': serializable_alerts,
                'summary': self.get_metrics_summary()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Monitoring data saved to: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save monitoring data: {e}")
            return False
    
    def setup_dashboard(self) -> bool:
        """Setup monitoring dashboard"""
        if not self.monitoring_config.enable_dashboard:
            return True
        
        try:
            # Create dashboard directory
            dashboard_dir = self.output_dir / "dashboard"
            dashboard_dir.mkdir(exist_ok=True)
            
            # Create HTML dashboard
            dashboard_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNS-CLAUDEJP 5.4 - Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #3498db;
        }}
        .metric-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .chart-container {{
            margin-bottom: 30px;
            height: 400px;
        }}
        .alert {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-good {{
            background-color: #2ecc71;
        }}
        .status-warning {{
            background-color: #f39c12;
        }}
        .status-critical {{
            background-color: #e74c3c;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>UNS-CLAUDEJP 5.4 - Monitoring Dashboard</h1>
            <p>Real-time monitoring of photo extraction system performance</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">CPU Usage</div>
                <div class="metric-value" id="cpu-value">--</div>
                <div class="metric-label" id="cpu-status">Loading...</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Memory Usage</div>
                <div class="metric-value" id="memory-value">--</div>
                <div class="metric-label" id="memory-status">Loading...</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Error Rate</div>
                <div class="metric-value" id="error-rate-value">--</div>
                <div class="metric-label" id="error-rate-status">Loading...</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-title">Response Time</div>
                <div class="metric-value" id="response-time-value">--</div>
                <div class="metric-label" id="response-time-status">Loading...</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Performance History</h2>
            <canvas id="performance-chart"></canvas>
        </div>
        
        <div id="alerts-container">
            <h2>Recent Alerts</h2>
            <div id="alerts-list">Loading...</div>
        </div>
        
        <div class="footer">
            <p>Last updated: <span id="last-updated">--</span></p>
            <p>UNS-CLAUDEJP 5.4 Photo Extraction System v2.0</p>
        </div>
    </div>
    
    <script>
        // Global variables
        let metricsData = [];
        let alertsData = [];
        
        // Initialize dashboard
        function initDashboard() {{
            loadMetricsData();
            updateMetrics();
            updateAlerts();
            setupChart();
            
            // Update every 5 seconds
            setInterval(updateMetrics, 5000);
            setInterval(loadMetricsData, 30000);  // Reload data every 30 seconds
        }}
        
        // Load metrics data
        function loadMetricsData() {{
            fetch('monitoring_data.json')
                .then(response => response.json())
                .then(data => {{
                    metricsData = data.metrics || [];
                    alertsData = data.alerts || [];
                    updateLastUpdated();
                }})
                .catch(error => {{
                    console.error('Error loading metrics data:', error);
                }});
        }}
        
        // Update metrics display
        function updateMetrics() {{
            if (metricsData.length === 0) return;
            
            const latestMetrics = metricsData[metricsData.length - 1];
            
            // Update CPU
            const cpuValue = latestMetrics.cpu_percent.toFixed(1);
            document.getElementById('cpu-value').textContent = cpuValue + '%';
            updateStatus('cpu-status', cpuValue, 70, 90);
            
            // Update Memory
            const memoryValue = latestMetrics.memory_percent.toFixed(1);
            document.getElementById('memory-value').textContent = memoryValue + '%';
            updateStatus('memory-status', memoryValue, 70, 90);
            
            // Update Error Rate
            const errorRateValue = latestMetrics.error_rate.toFixed(1);
            document.getElementById('error-rate-value').textContent = errorRateValue + '%';
            updateStatus('error-rate-status', errorRateValue, 1, 5);
            
            // Update Response Time
            const responseTimeValue = latestMetrics.avg_response_time.toFixed(2);
            document.getElementById('response-time-value').textContent = responseTimeValue + 's';
            updateStatus('response-time-status', responseTimeValue, 0.5, 2.0, true);
        }}
        
        // Update status indicator
        function updateStatus(elementId, value, warningThreshold, criticalThreshold, isInverted = false) {{
            const element = document.getElementById(elementId);
            let statusClass = 'status-good';
            let statusText = 'Normal';
            
            if (isInverted) {{
                if (value < warningThreshold) {{
                    statusClass = 'status-good';
                    statusText = 'Good';
                }} else if (value < criticalThreshold) {{
                    statusClass = 'status-warning';
                    statusText = 'Warning';
                }} else {{
                    statusClass = 'status-critical';
                    statusText = 'Critical';
                }}
            }} else {{
                if (value > warningThreshold) {{
                    statusClass = 'status-warning';
                    statusText = 'Warning';
                }} else if (value > criticalThreshold) {{
                    statusClass = 'status-critical';
                    statusText = 'Critical';
                }}
            }}
            
            element.innerHTML = `<span class="status-indicator ${{statusClass}}"></span>${{statusText}}`;
        }}
        
        // Update alerts
        function updateAlerts() {{
            const alertsContainer = document.getElementById('alerts-list');
            
            if (alertsData.length === 0) {{
                alertsContainer.innerHTML = '<p>No recent alerts</p>';
                return;
            }}
            
            // Get recent alerts (last 24 hours)
            const now = new Date();
            const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            const recentAlerts = alertsData.filter(alert => 
                new Date(alert.timestamp) > twentyFourHoursAgo
            ).slice(-10); // Last 10 alerts
            
            let alertsHtml = '';
            recentAlerts.forEach(alert => {{
                const alertTime = new Date(alert.timestamp).toLocaleString();
                const severityClass = alert.severity === 'critical' ? 'status-critical' : 
                                       alert.severity === 'warning' ? 'status-warning' : 'status-good';
                
                alertsHtml += `
                    <div class="alert">
                        <span class="status-indicator ${{severityClass}}"></span>
                        <strong>${{alert.type.replace('_', ' ').toUpperCase()}}</strong>: ${{alert.message}}
                        <br><small>${{alertTime}}</small>
                    </div>
                `;
            }});
            
            alertsContainer.innerHTML = alertsHtml;
        }}
        
        // Setup chart
        function setupChart() {{
            const ctx = document.getElementById('performance-chart').getContext('2d');
            
            // Prepare data for chart
            const chartData = prepareChartData();
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: chartData.labels,
                    datasets: [
                        {{
                            label: 'CPU %',
                            data: chartData.cpuData,
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            tension: 0.1
                        }},
                        {{
                            label: 'Memory %',
                            data: chartData.memoryData,
                            borderColor: 'rgb(54, 162, 235)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            tension: 0.1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100
                        }}
                    }}
                }}
            }});
        }}
        
        // Prepare data for chart
        function prepareChartData() {{
            if (metricsData.length === 0) {{
                return {{ labels: [], cpuData: [], memoryData: [] }};
            }}
            
            // Get last 50 data points
            const recentMetrics = metricsData.slice(-50);
            
            const labels = recentMetrics.map(m => 
                new Date(m.timestamp).toLocaleTimeString()
            );
            
            const cpuData = recentMetrics.map(m => m.cpu_percent);
            const memoryData = recentMetrics.map(m => m.memory_percent);
            
            return {{ labels, cpuData, memoryData }};
        }}
        
        // Update last updated time
        function updateLastUpdated() {{
            document.getElementById('last-updated').textContent = new Date().toLocaleString();
        }}
        
        // Initialize dashboard when page loads
        window.onload = initDashboard;
    </script>
</body>
</html>
"""
            
            # Write dashboard HTML
            dashboard_file = dashboard_dir / "index.html"
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            
            # Create metrics data file (will be updated by monitoring system)
            metrics_file = dashboard_dir / "monitoring_data.json"
            if not metrics_file.exists():
                with open(metrics_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'metrics': [],
                        'alerts': []
                    }, f, indent=2)
            
            self.logger.info(f"Monitoring dashboard setup at: {dashboard_dir}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to setup dashboard: {e}")
            return False


def create_monitoring_config(args) -> MonitoringConfig:
    """Create monitoring configuration from arguments"""
    config = MonitoringConfig()
    
    # Apply command line arguments
    if args.enable_performance_monitoring is not None:
        config.enable_performance_monitoring = args.enable_performance_monitoring
    
    if args.enable_resource_monitoring is not None:
        config.enable_resource_monitoring = args.enable_resource_monitoring
    
    if args.enable_alerting is not None:
        config.enable_alerting = args.enable_alerting
    
    if args.enable_dashboard is not None:
        config.enable_dashboard = args.enable_dashboard
    
    if args.monitoring_interval:
        config.monitoring_interval_seconds = args.monitoring_interval
    
    if args.metrics_retention_days:
        config.metrics_retention_days = args.metrics_retention_days
    
    # Apply custom thresholds
    if args.cpu_threshold:
        config.alert_thresholds['cpu_percent'] = args.cpu_threshold
    
    if args.memory_threshold:
        config.alert_thresholds['memory_percent'] = args.memory_threshold
    
    if args.error_rate_threshold:
        config.alert_thresholds['error_rate_percent'] = args.error_rate_threshold
    
    if args.response_time_threshold:
        config.alert_thresholds['response_time_seconds'] = args.response_time_threshold
    
    return config


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nMonitoring setup interrupted by user")
    sys.exit(130)


def main():
    """Main monitoring setup execution"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="Monitoring Setup for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Setup monitoring with default config
    %(prog)s --config custom_config.json          # Use custom configuration
    %(prog)s --enable-dashboard                     # Enable monitoring dashboard
    %(prog)s --cpu-threshold 75                    # Set CPU alert threshold to 75%
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='monitoring_data',
        help='Output directory for monitoring data (default: monitoring_data)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['setup', 'start', 'stop', 'status'],
        default='setup',
        help='Monitoring mode (setup, start, stop, status)'
    )
    
    # Monitoring options
    parser.add_argument(
        '--enable-performance-monitoring',
        action='store_true',
        default=None,
        help='Enable performance monitoring'
    )
    
    parser.add_argument(
        '--enable-resource-monitoring',
        action='store_true',
        default=None,
        help='Enable resource monitoring'
    )
    
    parser.add_argument(
        '--enable-alerting',
        action='store_true',
        default=None,
        help='Enable alerting'
    )
    
    parser.add_argument(
        '--enable-dashboard',
        action='store_true',
        default=None,
        help='Enable monitoring dashboard'
    )
    
    parser.add_argument(
        '--monitoring-interval',
        type=float,
        default=5.0,
        help='Monitoring interval in seconds (default: 5.0)'
    )
    
    parser.add_argument(
        '--metrics-retention-days',
        type=int,
        default=7,
        help='Metrics retention period in days (default: 7)'
    )
    
    # Alert thresholds
    parser.add_argument(
        '--cpu-threshold',
        type=float,
        help='CPU usage alert threshold in percent'
    )
    
    parser.add_argument(
        '--memory-threshold',
        type=float,
        help='Memory usage alert threshold in percent'
    )
    
    parser.add_argument(
        '--error-rate-threshold',
        type=float,
        help='Error rate alert threshold in percent'
    )
    
    parser.add_argument(
        '--response-time-threshold',
        type=float,
        help='Response time alert threshold in seconds'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create monitoring configuration
        monitoring_config = create_monitoring_config(args)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Monitoring Setup")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Mode: {args.mode}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Initialize monitoring system
        monitoring_system = MonitoringSystem(config, monitoring_config, output_dir)
        
        if not monitoring_system.setup_components():
            print("ERROR: Failed to setup monitoring components")
            return 1
        
        # Execute based on mode
        if args.mode == 'setup':
            print("Setting up monitoring system...")
            
            # Setup dashboard if enabled
            if monitoring_config.enable_dashboard:
                if monitoring_system.setup_dashboard():
                    print(f"Monitoring dashboard setup at: {output_dir / 'dashboard' / 'index.html'}")
                    print(f"Access dashboard at: file://{output_dir / 'dashboard' / 'index.html'}")
                else:
                    print("ERROR: Failed to setup monitoring dashboard")
                    return 1
            
            # Save monitoring configuration
            config_file = output_dir / "monitoring_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(monitoring_config), f, indent=2, ensure_ascii=False)
            
            print(f"Monitoring configuration saved to: {config_file}")
            print("Monitoring setup completed successfully!")
            
            # Print configuration summary
            print("\nMonitoring Configuration:")
            print(f"  Performance Monitoring: {'Enabled' if monitoring_config.enable_performance_monitoring else 'Disabled'}")
            print(f"  Resource Monitoring: {'Enabled' if monitoring_config.enable_resource_monitoring else 'Disabled'}")
            print(f"  Alerting: {'Enabled' if monitoring_config.enable_alerting else 'Disabled'}")
            print(f"  Dashboard: {'Enabled' if monitoring_config.enable_dashboard else 'Disabled'}")
            print(f"  Monitoring Interval: {monitoring_config.monitoring_interval_seconds}s")
            print(f"  Metrics Retention: {monitoring_config.metrics_retention_days} days")
            print(f"  Alert Thresholds:")
            print(f"    CPU: {monitoring_config.alert_thresholds['cpu_percent']}%")
            print(f"    Memory: {monitoring_config.alert_thresholds['memory_percent']}%")
            print(f"    Error Rate: {monitoring_config.alert_thresholds['error_rate_percent']}%")
            print(f"    Response Time: {monitoring_config.alert_thresholds['response_time_seconds']}s")
            
            return 0
        
        elif args.mode == 'start':
            print("Starting monitoring system...")
            monitoring_system.start_monitoring()
            
            try:
                # Keep running until interrupted
                while True:
                    time.sleep(10)
                    
                    # Save metrics periodically
                    monitoring_system.save_metrics_data()
                    
                    # Print current status
                    current_metrics = monitoring_system.get_current_metrics()
                    if current_metrics:
                        print(f"Status: CPU={current_metrics.cpu_percent:.1f}%, "
                              f"Memory={current_metrics.memory_percent:.1f}%, "
                              f"Errors={current_metrics.error_rate:.1f}%")
            except KeyboardInterrupt:
                print("\nStopping monitoring system...")
                monitoring_system.stop_monitoring()
                print("Monitoring system stopped")
                return 0
        
        elif args.mode == 'stop':
            print("Stop mode not implemented yet")
            return 1
        
        elif args.mode == 'status':
            print("Status mode not implemented yet")
            return 1
        
        else:
            print(f"Unknown mode: {args.mode}")
            return 1
    
    except KeyboardInterrupt:
        print("\nMonitoring setup interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)