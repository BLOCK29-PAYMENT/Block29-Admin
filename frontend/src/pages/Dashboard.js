import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Store, Monitor, Receipt, TrendingUp, AlertCircle, Clock, CheckCircle, Radio } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ['#0066CC', '#10B981', '#F59E0B', '#EF4444'];

const HUB_STATUS_STYLES = {
  ONLINE: 'badge-success',
  DEGRADED: 'badge-warning',
  OFFLINE: 'badge-error',
  UNKNOWN: 'badge-pending',
  NOT_CONFIGURED: 'badge-pending',
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [hubStatus, setHubStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchHubStatus();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHubStatus = async () => {
    try {
      const response = await axios.get(`${API}/hub/status`);
      setHubStatus(response.data);
    } catch (error) {
      setHubStatus({ overall: 'UNKNOWN', configured: false });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const merchantStatusData = [
    { name: 'Active', value: stats?.merchants?.active || 0 },
    { name: 'Pending', value: stats?.merchants?.pending || 0 },
    { name: 'Suspended', value: (stats?.merchants?.total || 0) - (stats?.merchants?.active || 0) - (stats?.merchants?.pending || 0) },
  ].filter(d => d.value > 0);

  const chartData = stats?.transactions?.weekly || [];

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard Overview</h1>
          <p className="text-slate-500 mt-1">Monitor your merchant processing operations</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Clock size={16} />
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="stats-card" data-testid="stats-merchants">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Total Merchants</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{stats?.merchants?.total || 0}</p>
                <p className="text-sm text-emerald-600 mt-1 flex items-center gap-1">
                  <TrendingUp size={14} />
                  {stats?.merchants?.active || 0} active
                </p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <Store className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stats-card" data-testid="stats-terminals">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Terminals</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{stats?.terminals?.total || 0}</p>
                <p className="text-sm text-emerald-600 mt-1 flex items-center gap-1">
                  <CheckCircle size={14} />
                  {stats?.terminals?.live || 0} live
                </p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-emerald-100 flex items-center justify-center">
                <Monitor className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stats-card" data-testid="stats-transactions">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Transactions</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{stats?.transactions?.total || 0}</p>
                <p className="text-sm text-slate-500 mt-1">All time</p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-amber-100 flex items-center justify-center">
                <Receipt className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stats-card" data-testid="stats-pending">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Pending Review</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{stats?.merchants?.pending || 0}</p>
                <p className="text-sm text-amber-600 mt-1 flex items-center gap-1">
                  <AlertCircle size={14} />
                  Needs attention
                </p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment Hub summary - live data, links to the Hub console */}
      <Card>
        <CardContent className="pt-5">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Radio className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">Payment Hub</p>
                <p className="text-xs text-slate-500">
                  {hubStatus?.checked_at
                    ? `Last check: ${new Date(hubStatus.checked_at).toLocaleTimeString()} · env: ${hubStatus.environment}`
                    : 'Checking...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className={`badge ${HUB_STATUS_STYLES[hubStatus?.overall] || 'badge-pending'}`}>
                {String(hubStatus?.overall || 'UNKNOWN').replace(/_/g, ' ')}
              </span>
              <Link to="/hub" className="text-sm font-medium text-primary hover:underline" data-testid="open-hub-link">
                Open Payment Hub →
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transaction Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Transactions - Last 4 Weeks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {chartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No transactions in the last 4 weeks
                </div>
              ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
                  <YAxis stroke="#64748B" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'white', 
                      border: '1px solid #E2E8F0',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="transactions" fill="#0066CC" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Merchant Status Pie */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Merchant Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {merchantStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={merchantStatusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {merchantStatusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  No merchant data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {stats?.transactions?.recent?.length > 0 ? (
            <div className="space-y-3">
              {stats.transactions.recent.slice(0, 5).map((tx, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${tx.status === 'approved' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <div>
                      <p className="text-sm font-medium">Transaction #{tx.id?.slice(0, 8)}</p>
                      <p className="text-xs text-slate-500">{tx.card_type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium tabular-nums">${tx.amount?.toFixed(2)}</p>
                    <p className="text-xs text-slate-500">{new Date(tx.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No recent transactions</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
