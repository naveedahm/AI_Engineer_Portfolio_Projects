import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface MetricsChartProps {
  title: string;
  data: any[];
  dataKey: string;
  color?: string;
  type?: 'line' | 'area' | 'bar';
}

export const MetricsChart: React.FC<MetricsChartProps> = ({
  title,
  data,
  dataKey,
  color = '#8884d8',
  type = 'line'
}) => {
  const ChartComponent = {
    line: LineChart,
    area: AreaChart,
    bar: BarChart
  }[type];

  const DataComponent = {
    line: Line,
    area: Area,
    bar: Bar
  }[type];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <ChartComponent data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" />
          <YAxis />
          <Tooltip />
          <Legend />
          <DataComponent
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            fill={color}
            fillOpacity={0.3}
          />
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
};