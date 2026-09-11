import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import Pagination from '../components/Pagination';
import { toast } from 'sonner';
import { Receipt, RefreshCw, Download } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [summary, setSummary] = useState({ count: 0, volume: 0, approved: 0 });
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [merchantFilter, setMerchantFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    fetchTransactions();
  }, [merchantFilter, statusFilter, startDate, endDate, page]);

  useEffect(() => {
    setPage(1);
  }, [merchantFilter, statusFilter, startDate, endDate]);

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchTransactions = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate + 'T23:59:59');

      const response = await axios.get(`${API}/transactions?${params}`);
      setTransactions(response.data.items);
      setTotal(response.data.total);
      setSummary(response.data.summary);
    } catch (error) {
      toast.error('Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate || '2000-01-01',
        end_date: (endDate || new Date().toISOString().split('T')[0]) + 'T23:59:59'
      });
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);

      const response = await axios.get(`${API}/reports/export?${params}`);
      const data = response.data.data;
      if (!data || data.length === 0) {
        toast.error('No data to export');
        return;
      }

      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${row[h] ?? ''}"`).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `transactions_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();

      if (response.data.truncated) {
        toast.warning(`Exported first 10,000 records - narrow the date range for the full set`);
      } else {
        toast.success(`Exported ${data.length} records`);
      }
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const fetchMerchants = async () => {
    try {
      const response = await axios.get(`${API}/merchants?page_size=500`);
      setMerchants(response.data.items);
    } catch (error) {
      console.error('Failed to fetch merchants');
    }
  };

  const getMerchantName = (merchantId) => {
    const merchant = merchants.find(m => m.id === merchantId);
    return merchant?.business_name || 'Unknown';
  };

  const getStatusBadge = (status) => {
    const styles = {
      approved: 'badge-success',
      pending: 'badge-warning',
      declined: 'badge-error'
    };
    return <span className={`badge ${styles[status] || 'badge-pending'}`}>{status}</span>;
  };

  // Summary comes from the backend over the FULL filtered set, not just this page

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transactions</h1>
          <p className="text-slate-500 mt-1">View and export transaction history</p>
        </div>
        <Button variant="outline" onClick={handleExport} data-testid="export-btn">
          <Download size={18} className="mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Transactions (filtered)</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums">{summary.count}</p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Volume (filtered)</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums">${summary.volume.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Approval Rate (filtered)</p>
            <p className="text-3xl font-bold text-emerald-600 tabular-nums">
              {summary.count > 0 ? ((summary.approved / summary.count) * 100).toFixed(1) : 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4 sm:items-end">
            <div>
              <Label className="text-xs text-slate-500">Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-[150px]"
                data-testid="tx-start-date"
              />
            </div>
            <div>
              <Label className="text-xs text-slate-500">End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-[150px]"
                data-testid="tx-end-date"
              />
            </div>
            <Select value={merchantFilter} onValueChange={setMerchantFilter}>
              <SelectTrigger className="w-[200px]" data-testid="tx-merchant-filter">
                <SelectValue placeholder="All Merchants" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Merchants</SelectItem>
                {merchants.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]" data-testid="tx-status-filter">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="declined">Declined</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={fetchTransactions}>
              <RefreshCw size={18} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No transactions found</p>
              <p className="text-sm mt-1">Transactions will appear here once processed</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Transaction ID</th>
                    <th>Merchant</th>
                    <th>Amount</th>
                    <th>Card Type</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.id} data-testid={`tx-row-${tx.id}`}>
                      <td className="font-mono text-sm">{tx.id?.slice(0, 12)}...</td>
                      <td>{getMerchantName(tx.merchant_id)}</td>
                      <td className="font-medium tabular-nums">${tx.amount?.toFixed(2)}</td>
                      <td>{tx.card_type}</td>
                      <td>{getStatusBadge(tx.status)}</td>
                      <td className="text-slate-500 text-sm">
                        {new Date(tx.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
