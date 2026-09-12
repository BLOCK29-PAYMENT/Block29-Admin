import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import Pagination from '../components/Pagination';
import { toast } from 'sonner';
import { Plus, Search, MoreVertical, Monitor, Zap, CheckCircle, RefreshCw, Info, Edit } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TerminalsPage() {
  const [terminals, setTerminals] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTerminal, setEditingTerminal] = useState(null);
  const [formData, setFormData] = useState({
    merchant_id: '',
    terminal_number: '',
    v_number: '',
    merchant_number: '',
    bin: '',
    chain: '',
    store_number: ''
  });

  useEffect(() => {
    const timer = setTimeout(fetchTerminals, search ? 350 : 0);
    return () => clearTimeout(timer);
  }, [statusFilter, search, page]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, search]);

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchTerminals = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (statusFilter !== 'all') params.append('provisioning_status', statusFilter);
      if (search) params.append('search', search);

      const response = await axios.get(`${API}/admin/terminals?${params}`);
      setTerminals(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Failed to fetch terminals');
    } finally {
      setLoading(false);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTerminal) {
        const { merchant_id, ...updateData } = formData;
        await axios.put(`${API}/admin/terminals/${editingTerminal.id}`, updateData);
        toast.success('Terminal updated');
      } else {
        await axios.post(`${API}/admin/terminals`, {
          ...formData,
          provider: 'tsys',
          provisioning_status: 'draft'
        });
        toast.success('Terminal created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchTerminals();
    } catch (error) {
      toast.error(error.response?.data?.detail || (editingTerminal ? 'Failed to update terminal' : 'Failed to create terminal'));
    }
  };

  const handleEdit = (terminal) => {
    setEditingTerminal(terminal);
    setFormData({
      merchant_id: terminal.merchant_id || '',
      terminal_number: terminal.terminal_number || '',
      v_number: terminal.v_number || '',
      merchant_number: terminal.merchant_number || '',
      bin: terminal.bin || '',
      chain: terminal.chain || '',
      store_number: terminal.store_number || ''
    });
    setDialogOpen(true);
  };

  const handleProvision = async (terminalId) => {
    try {
      await axios.post(`${API}/admin/terminals/${terminalId}/provision`);
      toast.success('Terminal provisioned');
      fetchTerminals();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Provisioning failed');
    }
  };

  const handleMarkLive = async (terminalId) => {
    try {
      await axios.post(`${API}/admin/terminals/${terminalId}/mark-live`);
      toast.success('Terminal marked as live');
      fetchTerminals();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark live');
    }
  };

  const resetForm = () => {
    setEditingTerminal(null);
    setFormData({
      merchant_id: '',
      terminal_number: '',
      v_number: '',
      merchant_number: '',
      bin: '',
      chain: '',
      store_number: ''
    });
  };

  // Honest status labels: these track internal state only - no processor API
  // is contacted, so we never claim a terminal was remotely "provisioned".
  const STATUS_LABELS = {
    draft: { label: 'Draft', style: 'badge-pending' },
    provisioned: { label: 'Provisioning Tracked', style: 'badge-info' },
    live: { label: 'Live (Confirmed)', style: 'badge-success' }
  };

  const getStatusBadge = (status) => {
    const info = STATUS_LABELS[status] || { label: status, style: 'badge-pending' };
    return <span className={`badge ${info.style}`}>{info.label}</span>;
  };

  const getMerchantName = (merchantId) => {
    const merchant = merchants.find(m => m.id === merchantId);
    return merchant?.business_name || 'Unknown';
  };

  const filteredTerminals = terminals;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Terminals & Devices</h1>
          <p className="text-slate-500 mt-1 flex items-center gap-1.5">
            <Info size={14} className="text-slate-400" />
            Internal terminal registry - status changes are tracked here; no processor API is contacted
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button data-testid="add-terminal-btn">
              <Plus size={18} className="mr-2" />
              Add Terminal
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingTerminal ? 'Edit Terminal' : 'Add New Terminal'}</DialogTitle>
              <DialogDescription>{editingTerminal ? 'Update terminal profile details' : 'Create a new terminal profile'}</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Merchant</Label>
                <Select value={formData.merchant_id} disabled={!!editingTerminal} onValueChange={(v) => setFormData({...formData, merchant_id: v})}>
                  <SelectTrigger data-testid="terminal-merchant-select">
                    <SelectValue placeholder="Select merchant" />
                  </SelectTrigger>
                  <SelectContent>
                    {merchants.length === 0 ? (
                      <div className="p-2 text-sm text-slate-500 text-center">No merchants available. Create one first.</div>
                    ) : (
                      merchants.map((m) => (
                        <SelectItem key={m.id} value={m.id} data-testid={`merchant-option-${m.id}`}>
                          {m.business_name}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Terminal Number</Label>
                  <Input
                    value={formData.terminal_number}
                    onChange={(e) => setFormData({...formData, terminal_number: e.target.value})}
                    className="font-mono"
                    data-testid="terminal-number-input"
                  />
                </div>
                <div>
                  <Label>V Number</Label>
                  <Input
                    value={formData.v_number}
                    onChange={(e) => setFormData({...formData, v_number: e.target.value})}
                    className="font-mono"
                  />
                </div>
                <div>
                  <Label>Merchant Number</Label>
                  <Input
                    value={formData.merchant_number}
                    onChange={(e) => setFormData({...formData, merchant_number: e.target.value})}
                    className="font-mono"
                  />
                </div>
                <div>
                  <Label>BIN</Label>
                  <Input
                    value={formData.bin}
                    onChange={(e) => setFormData({...formData, bin: e.target.value})}
                    className="font-mono"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="terminal-submit-btn">{editingTerminal ? 'Update' : 'Create'} Terminal</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <Input
                placeholder="Search terminals..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="terminal-search"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]" data-testid="terminal-status-filter">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="provisioned">Provisioning Tracked</SelectItem>
                <SelectItem value="live">Live (Confirmed)</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={fetchTerminals}>
              <RefreshCw size={18} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Terminals Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredTerminals.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No terminals found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Terminal #</th>
                    <th>Merchant</th>
                    <th>V Number</th>
                    <th>Merchant #</th>
                    <th>Provider</th>
                    <th>Status</th>
                    <th className="w-[50px]"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTerminals.map((terminal) => (
                    <tr key={terminal.id} data-testid={`terminal-row-${terminal.id}`}>
                      <td className="font-mono font-medium">{terminal.terminal_number || '-'}</td>
                      <td>{getMerchantName(terminal.merchant_id)}</td>
                      <td className="font-mono text-slate-600">{terminal.v_number || '-'}</td>
                      <td className="font-mono text-slate-600">{terminal.merchant_number || '-'}</td>
                      <td className="capitalize">{terminal.provider}</td>
                      <td>{getStatusBadge(terminal.provisioning_status)}</td>
                      <td>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" data-testid={`terminal-actions-${terminal.id}`}>
                              <MoreVertical size={16} />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEdit(terminal)}>
                              <Edit size={14} className="mr-2" />
                              Edit
                            </DropdownMenuItem>
                            {terminal.provisioning_status === 'draft' && (
                              <DropdownMenuItem onClick={() => handleProvision(terminal.id)}>
                                <Zap size={14} className="mr-2" />
                                Record Provisioning
                              </DropdownMenuItem>
                            )}
                            {terminal.provisioning_status === 'provisioned' && (
                              <DropdownMenuItem onClick={() => handleMarkLive(terminal.id)}>
                                <CheckCircle size={14} className="mr-2" />
                                Confirm Live
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
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
