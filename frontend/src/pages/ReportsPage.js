import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { BarChart3, Download, RefreshCw, FileSpreadsheet } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const COLORS = ['#0066CC', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

export default function ReportsPage() {
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('transactions');
  
  // Filters
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [merchantFilter, setMerchantFilter] = useState('all');
  
  // Report data
  const [transactionReport, setTransactionReport] = useState(null);
  const [batchReport, setBatchReport] = useState(null);

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchMerchants = async () => {
    try {
      const response = await axios.get(`${API}/merchants`);
      setMerchants(response.data);
    } catch (error) {
      console.error('Failed to fetch merchants');
    }
  };

  const fetchTransactionReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate + 'T23:59:59'
      });
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);
      
      const response = await axios.get(`${API}/reports/transactions?${params}`);
      setTransactionReport(response.data);
    } catch (error) {
      toast.error('Failed to fetch transaction report');
    } finally {
      setLoading(false);
    }
  };

  const fetchBatchReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate + 'T23:59:59'
      });
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);
      
      const response = await axios.get(`${API}/reports/batches?${params}`);
      setBatchReport(response.data);
    } catch (error) {
      toast.error('Failed to fetch batch report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate + 'T23:59:59'
      });
      if (merchantFilter !== 'all') params.append('merchant_id', merchantFilter);
      
      const response = await axios.get(`${API}/reports/export?${params}`);
      
      // Convert to CSV
      const data = response.data.data;
      if (data.length === 0) {
        toast.error('No data to export');
        return;
      }
      
      const headers = Object.keys(data[0]);
      const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${row[h] || ''}"`).join(','))
      ].join('\n');
      
      // Download
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `transactions_${startDate}_${endDate}.csv`;
      a.click();
      
      toast.success(`Exported ${data.length} records`);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const generateReport = () => {
    switch (activeTab) {
      case 'transactions':
        fetchTransactionReport();
        break;
      case 'batches':
        fetchBatchReport();
        break;
    }
  };

  // Chart data transformations
  const cardTypeChartData = transactionReport?.by_card_type 
    ? Object.entries(transactionReport.by_card_type).map(([name, data]) => ({
        name,
        count: data.count,
        amount: data.amount
      }))
    : [];

  const batchChartData = batchReport?.batches?.slice(0, 14).reverse() || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-slate-500 mt-1">Transaction, batch, and settlement reports</p>
        </div>
        <Button onClick={handleExport} variant="outline" data-testid="export-csv-btn">
          <Download size={18} className="mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <Label>Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-[160px]"
                data-testid="report-start-date"
              />
            </div>
            <div>
              <Label>End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-[160px]"
                data-testid="report-end-date"
              />
            </div>
            <div>
              <Label>Merchant</Label>
              <Select value={merchantFilter} onValueChange={setMerchantFilter}>
                <SelectTrigger className="w-[200px]" data-testid="report-merchant-filter">
                  <SelectValue placeholder="All Merchants" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Merchants</SelectItem>
                  {merchants.map((m) => (
                    <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={generateReport} disabled={loading} data-testid="generate-report-btn">
              {loading ? <RefreshCw className="animate-spin mr-2" size={16} /> : <BarChart3 size={16} className="mr-2" />}
              Generate Report
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Report Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="transactions">Transaction Report</TabsTrigger>
          <TabsTrigger value="batches">Batch Report</TabsTrigger>
        </TabsList>

        {/* Transaction Report */}
        <TabsContent value="transactions" className="space-y-6">
          {transactionReport ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Total Transactions</p>
                    <p className="text-2xl font-bold tabular-nums">{transactionReport.summary.total_transactions}</p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Total Volume</p>
                    <p className="text-2xl font-bold tabular-nums text-emerald-600">
                      ${transactionReport.summary.total_amount.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Approval Rate</p>
                    <p className="text-2xl font-bold tabular-nums">{transactionReport.summary.approval_rate}%</p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Refunds</p>
                    <p className="text-2xl font-bold tabular-nums text-red-600">
                      ${transactionReport.summary.refund_amount.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">By Card Type</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      {cardTypeChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={cardTypeChartData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={100}
                              dataKey="amount"
                              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            >
                              {cardTypeChartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-slate-400">
                          No data available
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Transaction Count by Card</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      {cardTypeChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={cardTypeChartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                            <XAxis dataKey="name" fontSize={12} />
                            <YAxis fontSize={12} />
                            <Tooltip />
                            <Bar dataKey="count" fill="#0066CC" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-slate-400">
                          No data available
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Transaction Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Transaction Details ({transactionReport.transactions.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto max-h-[400px]">
                    <table className="data-table">
                      <thead className="sticky top-0 bg-slate-50">
                        <tr>
                          <th>Date</th>
                          <th>Type</th>
                          <th>Amount</th>
                          <th>Card</th>
                          <th>Status</th>
                          <th>Auth Code</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactionReport.transactions.slice(0, 100).map((tx) => (
                          <tr key={tx.id}>
                            <td className="text-sm">{new Date(tx.created_at).toLocaleString()}</td>
                            <td className="capitalize">{tx.transaction_type || 'sale'}</td>
                            <td className="tabular-nums font-medium">${tx.amount?.toFixed(2)}</td>
                            <td>{tx.card_type} {tx.card_last_four ? `****${tx.card_last_four}` : ''}</td>
                            <td>
                              <span className={`badge ${tx.status === 'approved' ? 'badge-success' : 'badge-error'}`}>
                                {tx.status}
                              </span>
                            </td>
                            <td className="font-mono text-sm">{tx.auth_code || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="py-12 text-center text-slate-400">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Select date range and click "Generate Report"</p>
            </Card>
          )}
        </TabsContent>

        {/* Batch Report */}
        <TabsContent value="batches" className="space-y-6">
          {batchReport ? (
            <>
              {/* Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Total Batches</p>
                    <p className="text-2xl font-bold tabular-nums">{batchReport.summary.total_batches}</p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Total Sales</p>
                    <p className="text-2xl font-bold tabular-nums text-emerald-600">
                      ${batchReport.summary.total_sales.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Total Refunds</p>
                    <p className="text-2xl font-bold tabular-nums text-red-600">
                      ${batchReport.summary.total_refunds.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
                <Card className="stats-card">
                  <CardContent className="pt-5">
                    <p className="overline mb-1">Net Settlement</p>
                    <p className="text-2xl font-bold tabular-nums text-blue-600">
                      ${batchReport.summary.net_settlement.toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Daily Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Daily Settlement Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    {batchChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={batchChartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                          <XAxis dataKey="date" fontSize={10} />
                          <YAxis fontSize={12} tickFormatter={(v) => `$${v}`} />
                          <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
                          <Line type="monotone" dataKey="net_amount" stroke="#0066CC" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-400">
                        No batch data available
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Batch Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Daily Batches</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Transactions</th>
                          <th>Sales</th>
                          <th>Refunds</th>
                          <th>Net Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {batchReport.batches.map((batch) => (
                          <tr key={batch.date}>
                            <td className="font-medium">{batch.date}</td>
                            <td className="tabular-nums">{batch.transaction_count}</td>
                            <td className="tabular-nums text-emerald-600">${batch.sales_amount.toLocaleString()}</td>
                            <td className="tabular-nums text-red-600">${batch.refund_amount.toLocaleString()}</td>
                            <td className="tabular-nums font-semibold">${batch.net_amount.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="py-12 text-center text-slate-400">
              <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Select date range and click "Generate Report"</p>
            </Card>
          )}
        </TabsContent>

      </Tabs>
    </div>
  );
}
