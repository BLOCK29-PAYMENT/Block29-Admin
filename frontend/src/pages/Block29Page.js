import { useEffect, useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
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
import { toast } from 'sonner';
import { Plus, Zap, Server, RefreshCw, CheckCircle, Clock, AlertCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Block29Page() {
  const [provisions, setProvisions] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    merchant_id: '',
    processor: 'clover',
    terminal_data: {}
  });

  useEffect(() => {
    fetchProvisions();
    fetchMerchants();
  }, []);

  const fetchProvisions = async () => {
    try {
      const response = await axios.get(`${API}/block29/provisions`);
      setProvisions(response.data);
    } catch (error) {
      console.error('Failed to fetch provisions');
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
      await axios.post(`${API}/block29/provision-terminal`, formData);
      toast.success('Provisioning request submitted');
      setDialogOpen(false);
      fetchProvisions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Provisioning failed');
    }
  };

  const getMerchantName = (merchantId) => {
    const merchant = merchants.find(m => m.id === merchantId);
    return merchant?.business_name || 'Unknown';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-emerald-500" size={18} />;
      case 'pending':
        return <Clock className="text-amber-500" size={18} />;
      case 'failed':
        return <AlertCircle className="text-red-500" size={18} />;
      default:
        return <Clock className="text-blue-500" size={18} />;
    }
  };

  const processors = [
    { value: 'clover', label: 'Clover', color: 'bg-green-100 text-green-800' },
    { value: 'dejavoo', label: 'Dejavoo', color: 'bg-blue-100 text-blue-800' },
    { value: 'valor', label: 'Valor PayTech', color: 'bg-purple-100 text-purple-800' }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Block29 Internal Gateway</h1>
          <p className="text-slate-500 mt-1">Terminal provisioning and processor routing</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="provision-btn">
              <Plus size={18} className="mr-2" />
              New Provision
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Provision Terminal</DialogTitle>
              <DialogDescription>Submit a new terminal provisioning request to Block29</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Merchant</Label>
                <Select value={formData.merchant_id} onValueChange={(v) => setFormData({...formData, merchant_id: v})}>
                  <SelectTrigger data-testid="block29-merchant-select">
                    <SelectValue placeholder="Select merchant" />
                  </SelectTrigger>
                  <SelectContent>
                    {merchants.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Processor</Label>
                <Select value={formData.processor} onValueChange={(v) => setFormData({...formData, processor: v})}>
                  <SelectTrigger data-testid="block29-processor-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {processors.map((p) => (
                      <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="block29-submit-btn">
                  <Zap size={16} className="mr-2" />
                  Submit Provision
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Gateway Architecture */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server size={20} />
            Routing Architecture
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center gap-4 py-6">
            <div className="text-center p-4 bg-slate-100 rounded-lg">
              <div className="w-12 h-12 bg-slate-800 rounded-lg flex items-center justify-center mx-auto mb-2">
                <Zap className="text-white" size={24} />
              </div>
              <p className="text-sm font-medium">POS Terminal</p>
            </div>
            <div className="flex-1 border-t-2 border-dashed border-slate-300 max-w-[100px]" />
            <div className="text-center p-4 bg-primary/10 rounded-lg border-2 border-primary">
              <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center mx-auto mb-2">
                <Server className="text-white" size={24} />
              </div>
              <p className="text-sm font-medium text-primary">Block29 API</p>
            </div>
            <div className="flex-1 border-t-2 border-dashed border-slate-300 max-w-[100px]" />
            <div className="flex flex-col gap-2">
              {processors.map((p) => (
                <div key={p.value} className={`px-3 py-1.5 rounded-md text-xs font-medium ${p.color}`}>
                  {p.label}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Provisions List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Provisioning History</CardTitle>
            <Button variant="outline" size="sm" onClick={fetchProvisions}>
              <RefreshCw size={16} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : provisions.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Server className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No provisioning requests</p>
              <p className="text-sm mt-1">Submit a new provision to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Provision ID</th>
                    <th>Merchant</th>
                    <th>Processor</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {provisions.map((p) => (
                    <tr key={p.id} data-testid={`provision-row-${p.id}`}>
                      <td className="font-mono text-sm">{p.id?.slice(0, 12)}...</td>
                      <td>{getMerchantName(p.merchant_id)}</td>
                      <td>
                        <span className={`badge ${processors.find(pr => pr.value === p.processor)?.color || 'badge-pending'}`}>
                          {p.processor}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(p.status)}
                          <span className="capitalize">{p.status}</span>
                        </div>
                      </td>
                      <td className="text-slate-500 text-sm">
                        {new Date(p.created_at).toLocaleString()}
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
