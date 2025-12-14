import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { ScrollText, RefreshCw, Download, Search, Filter, User, Clock, Activity, FileText, CreditCard, Store, Terminal } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ACTION_COLORS = {
  CREATE: 'bg-emerald-100 text-emerald-800',
  UPDATE: 'bg-blue-100 text-blue-800',
  DELETE: 'bg-red-100 text-red-800',
  VIRTUAL_TERMINAL: 'bg-purple-100 text-purple-800',
  REFUND: 'bg-amber-100 text-amber-800',
  EXPORT: 'bg-slate-100 text-slate-800',
  LOGIN: 'bg-cyan-100 text-cyan-800',
  UPLOAD: 'bg-indigo-100 text-indigo-800',
  PROVISION: 'bg-orange-100 text-orange-800'
};

const RESOURCE_ICONS = {
  merchant: Store,
  terminal: Terminal,
  transaction: CreditCard,
  varsheet: FileText,
  user: User,
  report: Activity,
  block29: Activity
};

export default function SystemLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionTypes, setActionTypes] = useState([]);
  const [resourceTypes, setResourceTypes] = useState([]);
  
  // Filters
  const [actionFilter, setActionFilter] = useState('all');
  const [resourceFilter, setResourceFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

  useEffect(() => {
    fetchLogs();
    fetchFilterOptions();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '200' });
      if (actionFilter !== 'all') params.append('action', actionFilter);
      if (resourceFilter !== 'all') params.append('resource_type', resourceFilter);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate + 'T23:59:59');
      
      const response = await axios.get(`${API}/logs?${params}`);
      setLogs(response.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Admin access required');
      } else {
        toast.error('Failed to fetch logs');
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const response = await axios.get(`${API}/logs/actions`);
      setActionTypes(response.data.actions);
      setResourceTypes(response.data.resource_types);
    } catch (error) {
      // Use defaults
      setActionTypes(['CREATE', 'UPDATE', 'DELETE', 'VIRTUAL_TERMINAL', 'REFUND', 'EXPORT', 'LOGIN']);
      setResourceTypes(['merchant', 'terminal', 'transaction', 'varsheet', 'user', 'report']);
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate + 'T23:59:59'
      });
      
      const response = await axios.get(`${API}/logs/export?${params}`);
      const data = response.data.data;
      
      if (data.length === 0) {
        toast.error('No logs to export');
        return;
      }
      
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${row[h] || ''}"`).join(','))
      ].join('\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${startDate}_${endDate}.csv`;
      a.click();
      
      toast.success(`Exported ${data.length} records`);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const filteredLogs = logs.filter(log => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      log.user_email?.toLowerCase().includes(query) ||
      log.action?.toLowerCase().includes(query) ||
      log.resource_type?.toLowerCase().includes(query) ||
      log.resource_id?.toLowerCase().includes(query) ||
      JSON.stringify(log.details || {}).toLowerCase().includes(query)
    );
  });

  const getActionBadge = (action) => {
    const colorClass = ACTION_COLORS[action] || 'bg-slate-100 text-slate-800';
    return <span className={`badge ${colorClass}`}>{action}</span>;
  };

  const getResourceIcon = (resourceType) => {
    const Icon = RESOURCE_ICONS[resourceType] || Activity;
    return <Icon size={14} className="text-slate-400" />;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const formatDetails = (details) => {
    if (!details || Object.keys(details).length === 0) return '-';
    return Object.entries(details)
      .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
      .join(', ');
  };

  // Stats
  const todayLogs = logs.filter(l => l.timestamp?.startsWith(new Date().toISOString().split('T')[0]));
  const uniqueUsers = [...new Set(logs.map(l => l.user_email).filter(Boolean))];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">System Logs</h1>
          <p className="text-slate-500 mt-1">Audit trail of all admin actions</p>
        </div>
        <Button onClick={handleExport} variant="outline" data-testid="export-logs-btn">
          <Download size={18} className="mr-2" />
          Export Logs
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Total Logs</p>
                <p className="text-2xl font-bold tabular-nums">{logs.length}</p>
              </div>
              <ScrollText className="h-8 w-8 text-slate-300" />
            </div>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Today's Activity</p>
                <p className="text-2xl font-bold tabular-nums">{todayLogs.length}</p>
              </div>
              <Clock className="h-8 w-8 text-slate-300" />
            </div>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Active Users</p>
                <p className="text-2xl font-bold tabular-nums">{uniqueUsers.length}</p>
              </div>
              <User className="h-8 w-8 text-slate-300" />
            </div>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Action Types</p>
                <p className="text-2xl font-bold tabular-nums">{actionTypes.length}</p>
              </div>
              <Activity className="h-8 w-8 text-slate-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                <Input
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                  data-testid="log-search"
                />
              </div>
            </div>
            <div>
              <Label>Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-[140px]"
              />
            </div>
            <div>
              <Label>End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-[140px]"
              />
            </div>
            <div>
              <Label>Action</Label>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger className="w-[150px]" data-testid="log-action-filter">
                  <SelectValue placeholder="All Actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  {actionTypes.map((a) => (
                    <SelectItem key={a} value={a}>{a}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Resource</Label>
              <Select value={resourceFilter} onValueChange={setResourceFilter}>
                <SelectTrigger className="w-[150px]" data-testid="log-resource-filter">
                  <SelectValue placeholder="All Resources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Resources</SelectItem>
                  {resourceTypes.map((r) => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={fetchLogs} disabled={loading} data-testid="apply-filters-btn">
              {loading ? <RefreshCw className="animate-spin" size={16} /> : <Filter size={16} />}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <ScrollText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No logs found</p>
              <p className="text-sm mt-1">Try adjusting your filters</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Resource ID</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log, index) => (
                    <tr key={log.id || index} data-testid={`log-row-${index}`}>
                      <td className="text-sm whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Clock size={14} className="text-slate-400" />
                          {formatTimestamp(log.timestamp)}
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <User size={14} className="text-slate-400" />
                          <span className="text-sm">{log.user_email || log.user_id || 'System'}</span>
                        </div>
                      </td>
                      <td>{getActionBadge(log.action)}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          {getResourceIcon(log.resource_type)}
                          <span className="capitalize">{log.resource_type}</span>
                        </div>
                      </td>
                      <td className="font-mono text-xs text-slate-500">
                        {log.resource_id ? `${log.resource_id.slice(0, 12)}...` : '-'}
                      </td>
                      <td className="text-sm text-slate-600 max-w-[300px] truncate" title={formatDetails(log.details)}>
                        {formatDetails(log.details)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
