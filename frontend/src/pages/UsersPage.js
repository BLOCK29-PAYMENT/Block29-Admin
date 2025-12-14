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
import { Plus, UserCog, Shield, RefreshCw, Search, Mail } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLES = [
  { value: 'SUPER_ADMIN', label: 'Super Admin', description: 'Full system access', color: 'badge-error' },
  { value: 'OPERATIONS', label: 'Operations', description: 'VAR sheets, terminals, provisioning', color: 'badge-info' },
  { value: 'SUPPORT', label: 'Support', description: 'View data, transactions', color: 'badge-success' },
  { value: 'RISK', label: 'Risk', description: 'Compliance and risk management', color: 'badge-warning' },
  { value: 'READ_ONLY', label: 'Read Only', description: 'View only access', color: 'badge-pending' }
];

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'READ_ONLY'
  });
  const { user: currentUser, hasRole } = useAuth();

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      // If not authorized, show current user only
      if (error.response?.status === 403) {
        toast.error('Insufficient permissions to view all users');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/auth/register`, formData);
      toast.success('User created successfully');
      setDialogOpen(false);
      fetchUsers();
      setFormData({ email: '', password: '', name: '', role: 'READ_ONLY' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await axios.put(`${API}/users/${userId}/role?role=${newRole}`);
      toast.success('Role updated');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const getRoleBadge = (role) => {
    const roleInfo = ROLES.find(r => r.value === role);
    return <span className={`badge ${roleInfo?.color || 'badge-pending'}`}>{roleInfo?.label || role}</span>;
  };

  const filteredUsers = users.filter(u => 
    u.name?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  const isSuperAdmin = hasRole('SUPER_ADMIN');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Users & Roles</h1>
          <p className="text-slate-500 mt-1">Manage user accounts and permissions</p>
        </div>
        {isSuperAdmin && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-user-btn">
                <Plus size={18} className="mr-2" />
                Add User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New User</DialogTitle>
                <DialogDescription>Create a new user account</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label>Full Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    required
                    data-testid="user-name-input"
                  />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    required
                    data-testid="user-email-input"
                  />
                </div>
                <div>
                  <Label>Password</Label>
                  <Input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required
                    data-testid="user-password-input"
                  />
                </div>
                <div>
                  <Label>Role</Label>
                  <Select value={formData.role} onValueChange={(v) => setFormData({...formData, role: v})}>
                    <SelectTrigger data-testid="user-role-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          <div>
                            <span className="font-medium">{r.label}</span>
                            <span className="text-slate-500 ml-2 text-xs">{r.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" data-testid="user-submit-btn">Create User</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Role Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield size={20} />
            Role Permissions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {ROLES.map((role) => (
              <div key={role.value} className="p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  {getRoleBadge(role.value)}
                </div>
                <p className="text-xs text-slate-500">{role.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      {isSuperAdmin && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <Input
                  placeholder="Search users..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                  data-testid="user-search"
                />
              </div>
              <Button variant="outline" onClick={fetchUsers}>
                <RefreshCw size={18} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <UserCog className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No users found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Created</th>
                    {isSuperAdmin && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.id} data-testid={`user-row-${user.id}`}>
                      <td className="font-medium">
                        {user.name}
                        {user.id === currentUser?.id && (
                          <span className="ml-2 text-xs text-primary">(You)</span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-2 text-slate-600">
                          <Mail size={14} />
                          {user.email}
                        </div>
                      </td>
                      <td>{getRoleBadge(user.role)}</td>
                      <td className="text-slate-500 text-sm">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      {isSuperAdmin && (
                        <td>
                          {user.id !== currentUser?.id && (
                            <Select 
                              value={user.role} 
                              onValueChange={(v) => handleRoleChange(user.id, v)}
                            >
                              <SelectTrigger className="w-[140px]" data-testid={`role-select-${user.id}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {ROLES.map((r) => (
                                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </td>
                      )}
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
