import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Eye, EyeOff, Store, UtensilsCrossed, AudioLines } from 'lucide-react';

const products = [
  {
    name: 'AsterPOS',
    domain: 'asterpos.com',
    description: 'Point of sale platform',
    icon: Store,
    color: 'from-blue-400 to-blue-600',
  },
  {
    name: 'Chain29',
    domain: 'chain29.com',
    description: 'Restaurant chain app',
    icon: UtensilsCrossed,
    color: 'from-emerald-400 to-emerald-600',
  },
  {
    name: 'Agent9',
    domain: 'agent9.com',
    description: 'Voice AI engine',
    icon: AudioLines,
    color: 'from-purple-400 to-purple-600',
  },
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
      {/* Left side - ecosystem branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-blue-700">
        <div className="absolute inset-0">
          <div className="absolute w-96 h-96 bg-white/5 rounded-full blur-3xl -top-20 -left-20 animate-pulse" />
          <div className="absolute w-80 h-80 bg-blue-400/10 rounded-full blur-2xl top-1/2 left-1/4 animate-float" />
          <div className="absolute w-64 h-64 bg-cyan-400/10 rounded-full blur-2xl bottom-20 right-1/4 animate-float-delayed" />
        </div>

        <div className="relative z-10 flex flex-col justify-center w-full p-16">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-12 h-12 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center font-bold text-white shadow-lg">
              B29
            </div>
            <div className="text-white">
              <h1 className="font-bold text-xl tracking-tight">BLOCK29</h1>
              <p className="text-white/60 text-sm">Company Admin</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white leading-tight mb-3">
            One admin for the whole ecosystem
          </h2>
          <p className="text-white/60 mb-10 max-w-md">
            Merchants, terminals, transactions, and users across every Block29 product — managed from a single place.
          </p>

          <div className="space-y-4 max-w-md">
            {products.map((p) => (
              <div key={p.name} className="flex items-center gap-4 bg-white/5 border border-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className={`w-11 h-11 rounded-lg bg-gradient-to-br ${p.color} flex items-center justify-center flex-shrink-0`}>
                  <p.icon className="w-5 h-5 text-white" />
                </div>
                <div className="min-w-0">
                  <p className="text-white font-semibold">{p.name}</p>
                  <p className="text-white/50 text-sm truncate">{p.description} · {p.domain}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 rounded-xl bg-slate-900 flex items-center justify-center font-bold text-white text-lg shadow-lg">
                B29
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">Block29 Admin</CardTitle>
            <CardDescription>Sign in with your admin account</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-600">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@block29.com"
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
                  'Sign In'
                )}
              </Button>
            </form>

            <div className="mt-8 pt-6 border-t text-center">
              <p className="text-xs text-slate-400">Block29 internal admin · authorized staff only</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
