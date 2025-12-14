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
import { Plus, Users, Search, DollarSign, Store, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AffiliatesPage() {
  const [assignments, setAssignments] = useState([]);
  const [agents, setAgents] = useState([]);
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    agent_id: '',
    merchant_id: '',
    commission_rate: '',
    level: 1
  });

  useEffect(() => {
    fetchAssignments();
    fetchAgents();
    fetchMerchants();
  }, []);

  const fetchAssignments = async () => {
    try {
      const response = await axios.get(`${API}/agents/merchants`);
      setAssignments(response.data);
    } catch (error) {
      console.error('Failed to fetch assignments');
    } finally {
      setLoading(false);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await axios.get(`${API}/agents`);
      setAgents(response.data);
    } catch (error) {
      console.error('Failed to fetch agents');
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
      await axios.post(`${API}/agents/merchants`, {
        ...formData,
        commission_rate: parseFloat(formData.commission_rate),
        level: parseInt(formData.level)
      });
      toast.success('Assignment created');
      setDialogOpen(false);
      fetchAssignments();
      setFormData({ agent_id: '', merchant_id: '', commission_rate: '', level: 1 });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create assignment');
    }
  };

  const getAgentName = (agentId) => {
    const agent = agents.find(a => a.id === agentId);
    return agent?.name || 'Unknown';
  };

  const getMerchantName = (merchantId) => {
    const merchant = merchants.find(m => m.id === merchantId);
    return merchant?.business_name || 'Unknown';
  };

  const totalCommissions = assignments.reduce((sum, a) => sum + (a.commission_rate || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Affiliates & Agents</h1>
          <p className="text-slate-500 mt-1">Manage agent-merchant relationships and commissions</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="assign-merchant-btn">
              <Plus size={18} className="mr-2" />
              Assign Merchant
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Assign Merchant to Agent</DialogTitle>
              <DialogDescription>Set up commission relationship between agent and merchant</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Agent</Label>
                <Select value={formData.agent_id} onValueChange={(v) => setFormData({...formData, agent_id: v})}>
                  <SelectTrigger data-testid="affiliate-agent-select">
                    <SelectValue placeholder="Select agent" />
                  </SelectTrigger>
                  <SelectContent>
                    {agents.map((a) => (
                      <SelectItem key={a.id} value={a.id}>{a.name} ({a.email})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Merchant</Label>
                <Select value={formData.merchant_id} onValueChange={(v) => setFormData({...formData, merchant_id: v})}>
                  <SelectTrigger data-testid="affiliate-merchant-select">
                    <SelectValue placeholder="Select merchant" />
                  </SelectTrigger>
                  <SelectContent>
                    {merchants.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Commission Rate (%)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={formData.commission_rate}
                    onChange={(e) => setFormData({...formData, commission_rate: e.target.value})}
                    placeholder="e.g., 2.5"
                    data-testid="commission-rate-input"
                  />
                </div>
                <div>
                  <Label>Level</Label>
                  <Select value={String(formData.level)} onValueChange={(v) => setFormData({...formData, level: parseInt(v)})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Level 1 (Direct)</SelectItem>
                      <SelectItem value="2">Level 2</SelectItem>
                      <SelectItem value="3">Level 3</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="affiliate-submit-btn">Create Assignment</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Total Agents</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{agents.length}</p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Assignments</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{assignments.length}</p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-emerald-100 flex items-center justify-center">
                <Store className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="overline mb-1">Avg Commission</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">
                  {assignments.length > 0 ? (totalCommissions / assignments.length).toFixed(2) : 0}%
                </p>
              </div>
              <div className="h-12 w-12 rounded-lg bg-amber-100 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Assignments Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Agent-Merchant Assignments</CardTitle>
            <Button variant="outline" size="sm" onClick={fetchAssignments}>
              <RefreshCw size={16} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : assignments.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No assignments found</p>
              <p className="text-sm mt-1">Create an assignment to link agents with merchants</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Merchant</th>
                    <th>Commission Rate</th>
                    <th>Level</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.map((a) => (
                    <tr key={a.id} data-testid={`assignment-row-${a.id}`}>
                      <td className="font-medium">{getAgentName(a.agent_id)}</td>
                      <td>{getMerchantName(a.merchant_id)}</td>
                      <td className="tabular-nums">{a.commission_rate}%</td>
                      <td>
                        <span className="badge badge-info">Level {a.level}</span>
                      </td>
                      <td className="text-slate-500 text-sm">
                        {new Date(a.created_at).toLocaleDateString()}
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
