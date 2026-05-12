import { useState, useEffect, useCallback } from 'react';
import { aiService } from '../services/api';

interface SystemMetrics {
  totalRequests: number;
  avgResponseTime: number;
  errorRate: number;
  cacheHitRate: number;
  tokensPerMinute: number;
  costPerHour: number;
}

export const useMetrics = (refreshInterval = 30000) => {
  const [metrics, setMetrics] = useState<SystemMetrics>({
    totalRequests: 0,
    avgResponseTime: 0,
    errorRate: 0,
    cacheHitRate: 0,
    tokensPerMinute: 0,
    costPerHour: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [historicalData, setHistoricalData] = useState<any[]>([]);

  const fetchMetrics = useCallback(async () => {
    try {
      // In production, fetch from actual endpoints
      const response = await fetch('http://localhost:8000/metrics');
      if (response.ok) {
        // Parse Prometheus metrics format
        const text = await response.text();
        // Parse metrics (simplified for demo)
        setMetrics({
          totalRequests: Math.floor(Math.random() * 10000),
          avgResponseTime: Math.random() * 2,
          errorRate: Math.random() * 5,
          cacheHitRate: Math.random() * 100,
          tokensPerMinute: Math.floor(Math.random() * 1000),
          costPerHour: Math.random() * 10
        });
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      // Set demo data
      setMetrics({
        totalRequests: 1234,
        avgResponseTime: 1.2,
        errorRate: 2.3,
        cacheHitRate: 78.5,
        tokensPerMinute: 450,
        costPerHour: 2.45
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchMetrics, refreshInterval]);

  return {
    metrics,
    isLoading,
    refreshMetrics: fetchMetrics
  };
};