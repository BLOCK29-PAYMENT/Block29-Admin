import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { Search, Receipt, RefreshCw, Download, Filter } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [merchantFilter, setMerchantFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchTransactions();
    fetchMerchants();
  }, [merchantFilter, statusFilter]);

  const fetchTransactions = async () => {
    try {
      const params = new URLSearchParams();
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      const response = await axios.get(`${API}/transactions?${params}`);
      setTransactions(response.data);
    } catch (error) {
      toast.error('Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  const fetchMerchants = async () => {
    try {
      const response = await axios.get(`${API}/merchants`);
      setMerchants(response.data);
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

  const totalAmount = transactions.reduce((sum, tx) => sum + (tx.amount || 0), 0);
  const approvedCount = transactions.filter(tx => tx.status === 'approved').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transactions & Batches</h1>
          <p className="text-slate-500 mt-1">View and manage transaction history</p>
        </div>
        <Button variant="outline" data-testid="export-btn">
          <Download size={18} className="mr-2" />
          Export
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Total Transactions</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums">{transactions.length}</p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Total Volume</p>
            <p className="text-3xl font-bold text-slate-900 tabular-nums">${totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Approval Rate</p>
            <p className="text-3xl font-bold text-emerald-600 tabular-nums">
              {transactions.length > 0 ? ((approvedCount / transactions.length) * 100).toFixed(1) : 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
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
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
