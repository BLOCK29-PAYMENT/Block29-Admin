import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Eye, EyeOff, Lock, CreditCard, Smartphone, Monitor } from 'lucide-react';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_stylist-dashboard-5/artifacts/8cebph7y_LOGO%20MARK.jpg";

// POS Terminal equipment data
const posEquipment = [
  { name: 'Valor VL100', brand: 'Valor', type: 'countertop' },
  { name: 'Valor VP300', brand: 'Valor', type: 'portable' },
  { name: 'Dejavoo Z11', brand: 'Dejavoo', type: 'countertop' },
  { name: 'Dejavoo QD4', brand: 'Dejavoo', type: 'portable' },
  { name: 'Clover Flex', brand: 'Clover', type: 'portable' },
  { name: 'Clover Mini', brand: 'Clover', type: 'countertop' },
  { name: 'Clover Station', brand: 'Clover', type: 'station' },
];

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
      {/* Left side - animated branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-cyan-400 via-blue-500 to-blue-700">
        {/* Animated background circles */}
        <div className="absolute inset-0">
          <div className="absolute w-96 h-96 bg-white/10 rounded-full blur-3xl -top-20 -left-20 animate-pulse" />
          <div className="absolute w-80 h-80 bg-cyan-300/20 rounded-full blur-2xl top-1/2 left-1/4 animate-float" />
          <div className="absolute w-64 h-64 bg-blue-400/20 rounded-full blur-2xl bottom-20 right-1/4 animate-float-delayed" />
          <div className="absolute w-72 h-72 bg-white/5 rounded-full blur-3xl top-1/3 right-10 animate-pulse" />
        </div>

        {/* Central Payment Gateway Card */}
        <div className="relative z-10 flex flex-col items-center justify-center w-full p-12">
          {/* Logo at top */}
          <div className="absolute top-8 left-8 flex items-center gap-3">
            <img src={LOGO_URL} alt="SalonBookin" className="w-12 h-12 rounded-lg shadow-lg" />
            <div className="text-white">
              <h1 className="font-bold text-xl tracking-tight">SALONBOOKIN</h1>
              <p className="text-white/70 text-sm">Payment Processing</p>
            </div>
          </div>

          {/* Central Card Mockup */}
          <div className="relative">
            {/* Main Payment Gateway Card */}
            <div className="bg-white rounded-2xl shadow-2xl p-6 w-80 transform hover:scale-105 transition-transform duration-500">
              <div className="flex items-center justify-between mb-4">
                <img src={LOGO_URL} alt="Logo" className="w-10 h-10 rounded-lg" />
                <span className="text-sm font-medium text-slate-600">Payment Gateway</span>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-500">Card Information</label>
                  <div className="flex items-center border rounded-lg px-3 py-2 bg-slate-50">
                    <span className="text-slate-400 text-sm">XXXX XXXX XXXX XXXX</span>
                    <div className="ml-auto flex gap-1">
                      <div className="w-8 h-5 bg-red-500 rounded" />
                      <div className="w-8 h-5 bg-blue-600 rounded" />
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="border rounded-lg px-3 py-2 bg-slate-50 text-slate-400 text-sm">MM/YY</div>
                  <div className="border rounded-lg px-3 py-2 bg-slate-50 text-slate-400 text-sm">CVV</div>
                </div>
                <button className="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white py-2.5 rounded-lg font-medium shadow-lg hover:shadow-xl transition-shadow">
                  Process Payment
                </button>
              </div>
            </div>

            {/* Floating POS Equipment Cards */}
            {/* Valor */}
            <div className="absolute -top-8 -left-20 bg-white rounded-xl shadow-xl p-3 animate-float">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
                  <Monitor className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Valor VL100</p>
                  <p className="text-[10px] text-slate-500">Countertop</p>
                </div>
              </div>
            </div>

            {/* Dejavoo */}
            <div className="absolute -top-4 -right-24 bg-white rounded-xl shadow-xl p-3 animate-float-delayed">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-lg flex items-center justify-center">
                  <Smartphone className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Dejavoo Z11</p>
                  <p className="text-[10px] text-slate-500">Smart Terminal</p>
                </div>
              </div>
            </div>

            {/* Clover */}
            <div className="absolute -bottom-4 -left-28 bg-white rounded-xl shadow-xl p-3 animate-float-slow">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-lg flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Clover Flex</p>
                  <p className="text-[10px] text-slate-500">Portable</p>
                </div>
              </div>
            </div>

            {/* Valor VP300 */}
            <div className="absolute bottom-10 -right-20 bg-white rounded-xl shadow-xl p-3 animate-float">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-purple-600 rounded-lg flex items-center justify-center">
                  <Smartphone className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Valor VP300</p>
                  <p className="text-[10px] text-slate-500">Wireless</p>
                </div>
              </div>
            </div>

            {/* Dejavoo QD4 */}
            <div className="absolute top-1/2 -left-36 bg-white rounded-xl shadow-xl p-3 animate-float-delayed">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-orange-400 to-orange-600 rounded-lg flex items-center justify-center">
                  <Monitor className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Dejavoo QD4</p>
                  <p className="text-[10px] text-slate-500">Android POS</p>
                </div>
              </div>
            </div>

            {/* Clover Station */}
            <div className="absolute top-1/3 -right-32 bg-white rounded-xl shadow-xl p-3 animate-float-slow">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-br from-teal-400 to-teal-600 rounded-lg flex items-center justify-center">
                  <Monitor className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">Clover Station</p>
                  <p className="text-[10px] text-slate-500">Full POS</p>
                </div>
              </div>
            </div>
          </div>

          {/* Stats at bottom */}
          <div className="absolute bottom-8 left-8 right-8">
            <div className="flex items-center justify-between text-white">
              <div>
                <div className="text-3xl font-bold">500+</div>
                <div className="text-white/70 text-sm">Active Merchants</div>
              </div>
              <div className="h-12 w-px bg-white/20" />
              <div>
                <div className="text-3xl font-bold">1,200+</div>
                <div className="text-white/70 text-sm">Terminals</div>
              </div>
              <div className="h-12 w-px bg-white/20" />
              <div>
                <div className="text-3xl font-bold">$2.5M</div>
                <div className="text-white/70 text-sm">Processed Daily</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardHeader className="text-center pb-2">
            <div className="lg:hidden flex justify-center mb-4">
              <img src={LOGO_URL} alt="SalonBookin" className="w-16 h-16 rounded-xl shadow-lg" />
            </div>
            <div className="hidden lg:flex justify-center mb-4">
              <img src={LOGO_URL} alt="SalonBookin" className="w-20 h-20 rounded-xl shadow-lg" />
            </div>
            <CardTitle className="text-2xl font-bold">Welcome!</CardTitle>
            <CardDescription>Please log in to access your account</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-600">Username</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@salonbookin.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-11"
                  data-testid="login-email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-600">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pr-10 h-11"
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
              
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-300" />
                  <span className="text-slate-600">Remember me</span>
                </label>
                <a href="#" className="text-primary hover:underline font-medium">Forgot Password?</a>
              </div>

              <Button 
                type="submit" 
                className="w-full h-11 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 shadow-lg" 
                disabled={loading} 
                data-testid="login-submit"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                    Signing in...
                  </span>
                ) : (
                  'LOGIN'
                )}
              </Button>
            </form>

            <div className="mt-8 pt-6 border-t text-center">
              <p className="text-xs text-slate-500 mb-3">Powered by SALONBOOKIN (v1.0.0)</p>
              <div className="flex justify-center gap-3">
                <div className="px-3 py-1.5 bg-slate-900 text-white text-xs rounded-lg flex items-center gap-1">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                  </svg>
                  App Store
                </div>
                <div className="px-3 py-1.5 bg-slate-900 text-white text-xs rounded-lg flex items-center gap-1">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3,20.5V3.5C3,2.91 3.34,2.39 3.84,2.15L13.69,12L3.84,21.85C3.34,21.6 3,21.09 3,20.5M16.81,15.12L6.05,21.34L14.54,12.85L16.81,15.12M20.16,10.81C20.5,11.08 20.75,11.5 20.75,12C20.75,12.5 20.53,12.9 20.18,13.18L17.89,14.5L15.39,12L17.89,9.5L20.16,10.81M6.05,2.66L16.81,8.88L14.54,11.15L6.05,2.66Z"/>
                  </svg>
                  Google Play
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-xs text-blue-700 mb-2 font-medium">Demo Credentials:</p>
              <p className="text-xs text-blue-600">Email: admin@salonbookin.com</p>
              <p className="text-xs text-blue-600">Password: admin123</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
