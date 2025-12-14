import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { useAuth } from '../context/AuthContext';
import { Settings, Bell, Shield, Database, Globe, Save } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { user } = useAuth();

  const handleSave = () => {
    toast.success('Settings saved');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">Manage your account and system preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Settings */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings size={20} />
              Profile Settings
            </CardTitle>
            <CardDescription>Update your personal information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Full Name</Label>
                <Input defaultValue={user?.name} data-testid="settings-name" />
              </div>
              <div>
                <Label>Email</Label>
                <Input defaultValue={user?.email} type="email" data-testid="settings-email" />
              </div>
            </div>
            <div>
              <Label>Role</Label>
              <Input value={user?.role} disabled className="bg-slate-50" />
            </div>
            <Separator />
            <div className="space-y-4">
              <h3 className="font-medium">Change Password</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Current Password</Label>
                  <Input type="password" data-testid="current-password" />
                </div>
                <div>
                  <Label>New Password</Label>
                  <Input type="password" data-testid="new-password" />
                </div>
              </div>
            </div>
            <Button onClick={handleSave} data-testid="save-profile-btn">
              <Save size={16} className="mr-2" />
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Quick Settings */}
        <div className="space-y-6">
          {/* Notifications */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bell size={18} />
                Notifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Email Alerts</p>
                  <p className="text-xs text-slate-500">Get notified via email</p>
                </div>
                <Switch defaultChecked data-testid="email-alerts-switch" />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Terminal Alerts</p>
                  <p className="text-xs text-slate-500">New terminal events</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Transaction Alerts</p>
                  <p className="text-xs text-slate-500">High-value transactions</p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>

          {/* Security */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield size={18} />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Two-Factor Auth</p>
                  <p className="text-xs text-slate-500">Extra security layer</p>
                </div>
                <Switch data-testid="2fa-switch" />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Session Timeout</p>
                  <p className="text-xs text-slate-500">Auto logout after 24h</p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database size={20} />
            System Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="overline mb-1">Version</p>
              <p className="font-mono text-lg">v1.0.0</p>
            </div>
            <div>
              <p className="overline mb-1">API Endpoint</p>
              <p className="font-mono text-sm text-slate-600 truncate">{process.env.REACT_APP_BACKEND_URL}</p>
            </div>
            <div>
              <p className="overline mb-1">Environment</p>
              <p className="font-mono text-lg">Production</p>
            </div>
            <div>
              <p className="overline mb-1">Provider</p>
              <p className="font-mono text-lg">Luqra</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
