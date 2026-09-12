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
import { Plus, Search, MoreVertical, Edit, Trash2, Store, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function MerchantsPage() {
  const [merchants, setMerchants] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMerchant, setEditingMerchant] = useState(null);
  const [formData, setFormData] = useState({
    business_name: '',
    dba: '',
    tax_id: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    status: 'pending'
  });

  useEffect(() => {
    const timer = setTimeout(fetchMerchants, search ? 350 : 0);
    return () => clearTimeout(timer);
  }, [statusFilter, search, page]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, search]);

  const fetchMerchants = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (search) params.append('search', search);

      const response = await axios.get(`${API}/merchants?${params}`);
      setMerchants(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      toast.error('Failed to fetch merchants');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingMerchant) {
        await axios.put(`${API}/merchants/${editingMerchant.id}`, formData);
        toast.success('Merchant updated successfully');
      } else {
        await axios.post(`${API}/merchants`, formData);
        toast.success('Merchant created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchMerchants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEdit = (merchant) => {
    setEditingMerchant(merchant);
    setFormData({
      business_name: merchant.business_name || '',
      dba: merchant.dba || '',
      tax_id: merchant.tax_id || '',
      contact_email: merchant.contact_email || '',
      contact_phone: merchant.contact_phone || '',
      address: merchant.address || '',
      status: merchant.status || 'pending'
    });
    setDialogOpen(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this merchant?')) return;
    
    try {
      await axios.delete(`${API}/merchants/${id}`);
      toast.success('Merchant deleted');
      fetchMerchants();
    } catch (error) {
      toast.error('Failed to delete merchant');
    }
  };

  const resetForm = () => {
    setEditingMerchant(null);
    setFormData({
      business_name: '',
      dba: '',
      tax_id: '',
      contact_email: '',
      contact_phone: '',
      address: '',
      status: 'pending'
    });
  };

  const getStatusBadge = (status) => {
    const styles = {
      active: 'badge-success',
      pending: 'badge-warning',
      suspended: 'badge-error'
    };
    return <span className={`badge ${styles[status] || 'badge-pending'}`}>{status}</span>;
  };

  const filteredMerchants = merchants;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Merchants</h1>
          <p className="text-slate-500 mt-1">Manage your merchant accounts</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button data-testid="add-merchant-btn">
              <Plus size={18} className="mr-2" />
              Add Merchant
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingMerchant ? 'Edit Merchant' : 'Add New Merchant'}</DialogTitle>
              <DialogDescription>
                {editingMerchant ? 'Update merchant information' : 'Enter the merchant details below'}
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label htmlFor="business_name">Business Name *</Label>
                  <Input
                    id="business_name"
                    value={formData.business_name}
                    onChange={(e) => setFormData({...formData, business_name: e.target.value})}
                    required
                    data-testid="merchant-business-name"
                  />
                </div>
                <div>
                  <Label htmlFor="dba">DBA</Label>
                  <Input
                    id="dba"
                    value={formData.dba}
                    onChange={(e) => setFormData({...formData, dba: e.target.value})}
                    data-testid="merchant-dba"
                  />
                </div>
                <div>
                  <Label htmlFor="tax_id">Tax ID</Label>
                  <Input
                    id="tax_id"
                    value={formData.tax_id}
                    onChange={(e) => setFormData({...formData, tax_id: e.target.value})}
                    data-testid="merchant-tax-id"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_email">Email</Label>
                  <Input
                    id="contact_email"
                    type="email"
                    value={formData.contact_email}
                    onChange={(e) => setFormData({...formData, contact_email: e.target.value})}
                    data-testid="merchant-email"
                  />
                </div>
                <div>
                  <Label htmlFor="contact_phone">Phone</Label>
                  <Input
                    id="contact_phone"
                    value={formData.contact_phone}
                    onChange={(e) => setFormData({...formData, contact_phone: e.target.value})}
                    data-testid="merchant-phone"
                  />
                </div>
                <div className="col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({...formData, address: e.target.value})}
                    data-testid="merchant-address"
                  />
                </div>
                <div>
                  <Label htmlFor="status">Status</Label>
                  <Select value={formData.status} onValueChange={(v) => setFormData({...formData, status: v})}>
                    <SelectTrigger data-testid="merchant-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="suspended">Suspended</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" data-testid="merchant-submit-btn">
                  {editingMerchant ? 'Update' : 'Create'} Merchant
                </Button>
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
                placeholder="Search merchants..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="merchant-search"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]" data-testid="merchant-status-filter">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={fetchMerchants} data-testid="refresh-btn">
              <RefreshCw size={18} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredMerchants.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Store className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No merchants found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Business Name</th>
                    <th>DBA</th>
                    <th>Contact</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th className="w-[50px]"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMerchants.map((merchant) => (
                    <tr key={merchant.id} data-testid={`merchant-row-${merchant.id}`}>
                      <td className="font-medium">{merchant.business_name}</td>
                      <td className="text-slate-600">{merchant.dba || '-'}</td>
                      <td>
                        <div className="text-sm">{merchant.contact_email || '-'}</div>
                        <div className="text-xs text-slate-500">{merchant.contact_phone || ''}</div>
                      </td>
                      <td>{getStatusBadge(merchant.status)}</td>
                      <td className="text-slate-500 text-sm">
                        {new Date(merchant.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" data-testid={`merchant-actions-${merchant.id}`}>
                              <MoreVertical size={16} />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEdit(merchant)}>
                              <Edit size={14} className="mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleDelete(merchant.id)}
                              className="text-red-600"
                            >
                              <Trash2 size={14} className="mr-2" />
                              Delete
                            </DropdownMenuItem>
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
