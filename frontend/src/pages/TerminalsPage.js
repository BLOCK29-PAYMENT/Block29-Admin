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
import { toast } from 'sonner';
import { Plus, Search, MoreVertical, Monitor, Zap, Link, CheckCircle, RefreshCw, Copy } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TerminalsPage() {
  const [terminals, setTerminals] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pairingToken, setPairingToken] = useState(null);
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
    fetchTerminals();
    fetchMerchants();
  }, [statusFilter]);

  const fetchTerminals = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('provisioning_status', statusFilter);
      
      const response = await axios.get(`${API}/admin/terminals?${params}`);
      setTerminals(response.data);
    } catch (error) {
      toast.error('Failed to fetch terminals');
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/terminals`, {
        ...formData,
        provider: 'luqra',
        provisioning_status: 'draft'
      });
      toast.success('Terminal created successfully');
      setDialogOpen(false);
      resetForm();
      fetchTerminals();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create terminal');
    }
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

  const handleGeneratePairing = async (terminalId) => {
    try {
      const response = await axios.post(`${API}/admin/terminals/${terminalId}/pair`);
      setPairingToken(response.data.pairing_token);
      toast.success('Pairing token generated');
    } catch (error) {
      toast.error('Failed to generate pairing token');
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

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const resetForm = () => {
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

  const getStatusBadge = (status) => {
    const styles = {
      live: 'badge-success',
      provisioned: 'badge-info',
      ready: 'badge-warning',
      draft: 'badge-pending'
    };
    return <span className={`badge ${styles[status] || 'badge-pending'}`}>{status}</span>;
  };

  const getMerchantName = (merchantId) => {
    const merchant = merchants.find(m => m.id === merchantId);
    return merchant?.business_name || 'Unknown';
  };

  const filteredTerminals = terminals.filter(t => 
    t.terminal_number?.toLowerCase().includes(search.toLowerCase()) ||
    t.merchant_number?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Terminals & Devices</h1>
          <p className="text-slate-500 mt-1">Manage terminal profiles and provisioning</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-terminal-btn">
              <Plus size={18} className="mr-2" />
              Add Terminal
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Terminal</DialogTitle>
              <DialogDescription>Create a new terminal profile</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Merchant</Label>
                <Select value={formData.merchant_id} onValueChange={(v) => setFormData({...formData, merchant_id: v})}>
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
                <Button type="submit" data-testid="terminal-submit-btn">Create Terminal</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Pairing Token Display */}
      {pairingToken && (
        <Card className="bg-emerald-50 border-emerald-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-emerald-800">Pairing Token Generated</p>
                <p className="text-2xl font-mono font-bold text-emerald-900 mt-1">{pairingToken}</p>
                <p className="text-xs text-emerald-600 mt-1">Expires in 24 hours</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => copyToClipboard(pairingToken)}>
                  <Copy size={14} className="mr-1" />
                  Copy
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setPairingToken(null)}>
                  Dismiss
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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
                <SelectItem value="ready">Ready</SelectItem>
                <SelectItem value="provisioned">Provisioned</SelectItem>
                <SelectItem value="live">Live</SelectItem>
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
                            {terminal.provisioning_status === 'draft' && (
                              <DropdownMenuItem onClick={() => handleProvision(terminal.id)}>
                                <Zap size={14} className="mr-2" />
                                Provision
                              </DropdownMenuItem>
                            )}
                            {terminal.provisioning_status === 'provisioned' && (
                              <>
                                <DropdownMenuItem onClick={() => handleGeneratePairing(terminal.id)}>
                                  <Link size={14} className="mr-2" />
                                  Generate Pairing Token
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleMarkLive(terminal.id)}>
                                  <CheckCircle size={14} className="mr-2" />
                                  Mark Live
                                </DropdownMenuItem>
                              </>
                            )}
                            {terminal.provisioning_status === 'live' && (
                              <DropdownMenuItem onClick={() => handleGeneratePairing(terminal.id)}>
                                <Link size={14} className="mr-2" />
                                Regenerate Pairing Token
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
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
