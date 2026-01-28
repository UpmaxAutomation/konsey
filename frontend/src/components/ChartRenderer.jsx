/**
 * ChartRenderer - Renders charts from structured data in markdown responses
 *
 * Supports bar, line, and pie charts using Recharts library.
 * Data format expected from markdown code blocks:
 *
 * ```chart:bar
 * {
 *   "data": [{"name": "A", "value": 10}, {"name": "B", "value": 20}],
 *   "xKey": "name",
 *   "yKey": "value",
 *   "title": "My Chart"
 * }
 * ```
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import './ChartRenderer.css';

// Default color palette for charts
const COLORS = [
  '#3b82f6', // blue
  '#22c55e', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
];

/**
 * Parse chart configuration from JSON string
 * @param {string} jsonString - JSON string with chart config
 * @returns {object|null} Parsed config or null if invalid
 */
function parseChartConfig(jsonString) {
  try {
    const config = JSON.parse(jsonString);
    if (!config.data || !Array.isArray(config.data)) {
      console.warn('ChartRenderer: Invalid data format - expected array');
      return null;
    }
    return config;
  } catch (e) {
    console.warn('ChartRenderer: Failed to parse JSON:', e.message);
    return null;
  }
}

/**
 * Render a bar chart
 */
function RenderBarChart({ data, xKey, yKey, title, colors = COLORS }) {
  return (
    <div className="chart-container">
      {title && <h4 className="chart-title">{title}</h4>}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border-primary)' }}
          />
          <YAxis
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border-primary)' }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Render a line chart
 */
function RenderLineChart({ data, xKey, yKey, yKeys, title, colors = COLORS }) {
  // Support multiple Y keys for multi-line charts
  const yKeysArray = yKeys || [yKey];

  return (
    <div className="chart-container">
      {title && <h4 className="chart-title">{title}</h4>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border-primary)' }}
          />
          <YAxis
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border-primary)' }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '8px',
            }}
          />
          <Legend />
          {yKeysArray.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colors[index % colors.length]}
              strokeWidth={2}
              dot={{ fill: colors[index % colors.length], r: 4 }}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Render a pie chart
 */
function RenderPieChart({ data, nameKey, valueKey, title, colors = COLORS }) {
  return (
    <div className="chart-container">
      {title && <h4 className="chart-title">{title}</h4>}
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            labelLine={{ stroke: 'var(--text-muted)' }}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              borderRadius: '8px',
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Main ChartRenderer component
 * @param {string} type - Chart type: 'bar', 'line', or 'pie'
 * @param {string} children - JSON string with chart configuration
 */
export default function ChartRenderer({ type, children }) {
  const config = useMemo(() => parseChartConfig(children), [children]);

  if (!config) {
    return (
      <div className="chart-error">
        <span>Unable to render chart - invalid data format</span>
        <pre>{children}</pre>
      </div>
    );
  }

  const { data, xKey, yKey, yKeys, nameKey, valueKey, title, colors } = config;

  switch (type) {
    case 'bar':
      return <RenderBarChart data={data} xKey={xKey || 'name'} yKey={yKey || 'value'} title={title} colors={colors} />;
    case 'line':
      return <RenderLineChart data={data} xKey={xKey || 'name'} yKey={yKey || 'value'} yKeys={yKeys} title={title} colors={colors} />;
    case 'pie':
      return <RenderPieChart data={data} nameKey={nameKey || xKey || 'name'} valueKey={valueKey || yKey || 'value'} title={title} colors={colors} />;
    default:
      return (
        <div className="chart-error">
          <span>Unknown chart type: {type}</span>
        </div>
      );
  }
}

/**
 * Check if a language string represents a chart code block
 * @param {string} language - Code block language identifier
 * @returns {boolean} True if it's a chart block
 */
export function isChartLanguage(language) {
  return language?.startsWith('chart:');
}

/**
 * Extract chart type from language string
 * @param {string} language - Code block language identifier (e.g., "chart:bar")
 * @returns {string} Chart type (e.g., "bar")
 */
export function getChartType(language) {
  return language?.split(':')[1] || 'bar';
}
