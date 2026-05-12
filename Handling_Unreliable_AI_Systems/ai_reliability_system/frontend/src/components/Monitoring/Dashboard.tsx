import React, { useState, useEffect } from 'react';
import { MetricsChart } from './MetricsChart';
import { AlertPanel } from './AlertPanel';
import { Activity, DollarSign, Zap, Shield, TrendingUp, AlertTriangle } from 'lucide-react';

interface Metrics {
  totalRequests: number;
  avgResponseTime: number;
  errorRate: number;
  totalCost: number;
  cacheHitRate: number;
  rateLimitHits: number;
}

export const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Metrics>({
    totalRequests: 0,
    avgResponseTime: 0,
    errorRate: 0,
    totalCost: 0,
    cacheHitRate: 0,
    rateLimitHits: 0
  });

  const [chartData, setChartData] = useState<any[]>([]);

  useEffect(() => {
    // Simulate fetching metrics
    const fetchMetrics = async () => {
      // In production, fetch from /metrics endpoint
      setMetrics({
        totalRequests: 1234,
        avgResponseTime: 1.2,
        errorRate: 2.3,
        totalCost: 12.45,
        cacheHitRate: 78.5,
        rateLimitHits: 3
      });

      // Generate chart data
      const data = Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        requests: Math.floor(Math.random() * 100),
        latency: Math.random() * 2,
        errors: Math.floor(Math.random() * 10)
      }));
      setChartData(data);
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const MetricCard = ({ title, value, unit, icon: Icon, color }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold mt-1">
            {value}
            {unit && <span className="text-sm text-gray-500 ml-1">{unit}</span>}
          </p>
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <AlertPanel />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard
          title="Total Requests"
          value={metrics.totalRequests.toLocaleString()}
          unit=""
          icon={Activity}
          color="bg-blue-500"
        />
        <MetricCard
          title="Avg Response Time"
          value={metrics.avgResponseTime}
          unit="s"
          icon={Zap}
          color="bg-green-500"
        />
        <MetricCard
          title="Error Rate"
          value={metrics.errorRate}
          unit="%"
          icon={AlertTriangle}
          color="bg-red-500"
        />
        <MetricCard
          title="Total Cost"
          value={`$${metrics.totalCost}`}
          unit=""
          icon={DollarSign}
          color="bg-yellow-500"
        />
        <MetricCard
          title="Cache Hit Rate"
          value={metrics.cacheHitRate}
          unit="%"
          icon={Shield}
          color="bg-purple-500"
        />
        <MetricCard
          title="Rate Limit Hits"
          value={metrics.rateLimitHits}
          unit=""
          icon={TrendingUp}
          color="bg-orange-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MetricsChart
          title="Request Volume (Last 24 hours)"
          data={chartData}
          dataKey="requests"
          color="#3B82F6"
        />
        <MetricsChart
          title="Response Latency (Seconds)"
          data={chartData}
          dataKey="latency"
          color="#10B981"
        />
      </div>
    </div>
  );
};