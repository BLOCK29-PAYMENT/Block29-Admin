import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Eye, EyeOff, Lock } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_stylist-dashboard-5/artifacts/8cebph7y_LOGO%20MARK.jpg";

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(email, password);
      toast.success('Welcome back!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <img src={LOGO_URL} alt="SalonBookin" className="w-12 h-12 rounded-lg" />
          <div>
            <h1 className="text-white font-bold text-xl">SALONBOOKIN</h1>
            <p className="text-slate-400 text-sm">Admin Platform</p>
          </div>
        </div>
        
        <div>
          <h2 className="text-white text-4xl font-bold leading-tight mb-4">
            Manage your POS & Merchant Processing
          </h2>
          <p className="text-slate-400 text-lg">
            Internal admin platform for VAR sheet processing, terminal provisioning, and Block29 gateway management.
          </p>
        </div>

        <div className="flex items-center gap-8 text-slate-400 text-sm">
          <div>
            <div className="text-2xl font-bold text-white">500+</div>
            <div>Active Merchants</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">1,200+</div>
            <div>Terminals</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">$2.5M</div>
            <div>Processed Daily</div>
          </div>
        </div>
      </div>

      {/* Right side - login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardHeader className="text-center pb-2">
            <div className="lg:hidden flex justify-center mb-4">
              <img src={LOGO_URL} alt="SalonBookin" className="w-14 h-14 rounded-lg" />
            </div>
            <CardTitle className="text-2xl">Welcome back</CardTitle>
            <CardDescription>Sign in to your admin account</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@salonbookin.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  data-testid="login-email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pr-10"
                    data-testid="login-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit">
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Signing in...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Lock size={16} />
                    Sign in
                  </span>
                )}
              </Button>
            </form>

            <div className="mt-6 p-4 bg-slate-100 rounded-lg">
              <p className="text-xs text-slate-600 mb-2 font-medium">Demo Credentials:</p>
              <p className="text-xs text-slate-500">Email: admin@salonbookin.com</p>
              <p className="text-xs text-slate-500">Password: admin123</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
