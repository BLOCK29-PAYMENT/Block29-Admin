import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import { CreditCard, CheckCircle, XCircle, RefreshCw, DollarSign, User, Mail, Phone, FileText } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function VirtualTerminalPage() {
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [formData, setFormData] = useState({
    merchant_id: '',
    transaction_type: 'sale',
    amount: '',
    card_number: '',
    card_expiry: '',
    card_cvv: '',
    cardholder_name: '',
    customer_email: '',
    customer_phone: '',
    description: ''
  });

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchMerchants = async () => {
    try {
      const response = await axios.get(`${API}/merchants`);
      setMerchants(response.data);
    } catch (error) {
      console.error('Failed to fetch merchants');
    }
  };

  const formatCardNumber = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = matches && matches[0] || '';
    const parts = [];
    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }
    return parts.length ? parts.join(' ') : value;
  };

  const formatExpiry = (value) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      return v.substring(0, 2) + '/' + v.substring(2, 4);
    }
    return v;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const response = await axios.post(`${API}/virtual-terminal/process`, {
        ...formData,
        amount: parseFloat(formData.amount),
        card_number: formData.card_number.replace(/\s/g, '')
      });
      
      setResult(response.data);
      
      if (response.data.status === 'approved') {
        toast.success('Transaction Approved!');
      } else {
        toast.error('Transaction Declined');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Transaction failed');
      setResult({ status: 'error', response_message: error.response?.data?.detail || 'Processing error' });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      merchant_id: formData.merchant_id,
      transaction_type: 'sale',
      amount: '',
      card_number: '',
      card_expiry: '',
      card_cvv: '',
      cardholder_name: '',
      customer_email: '',
      customer_phone: '',
      description: ''
    });
    setResult(null);
  };

  const getCardBrand = (number) => {
    const num = number.replace(/\s/g, '');
    if (num.startsWith('4')) return { brand: 'VISA', color: 'bg-blue-600' };
    if (/^5[1-5]/.test(num)) return { brand: 'MasterCard', color: 'bg-red-500' };
    if (/^3[47]/.test(num)) return { brand: 'AMEX', color: 'bg-blue-800' };
    if (num.startsWith('6011')) return { brand: 'Discover', color: 'bg-orange-500' };
    return { brand: '', color: 'bg-slate-400' };
  };

  const cardInfo = getCardBrand(formData.card_number);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Virtual Terminal</h1>
        <p className="text-slate-500 mt-1">Process card-not-present transactions manually</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Transaction Form */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard size={20} />
              New Transaction
            </CardTitle>
            <CardDescription>Enter card details to process a payment</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Merchant & Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Merchant *</Label>
                  <Select 
                    value={formData.merchant_id} 
                    onValueChange={(v) => setFormData({...formData, merchant_id: v})}
                  >
                    <SelectTrigger data-testid="vt-merchant-select">
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
                  <Label>Transaction Type</Label>
                  <Select 
                    value={formData.transaction_type} 
                    onValueChange={(v) => setFormData({...formData, transaction_type: v})}
                  >
                    <SelectTrigger data-testid="vt-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sale">Sale</SelectItem>
                      <SelectItem value="authorization">Authorization Only</SelectItem>
                      <SelectItem value="refund">Refund</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Amount */}
              <div>
                <Label>Amount *</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0.00"
                    value={formData.amount}
                    onChange={(e) => setFormData({...formData, amount: e.target.value})}
                    className="pl-10 text-2xl font-semibold h-14"
                    required
                    data-testid="vt-amount"
                  />
                </div>
              </div>

              <Separator />

              {/* Card Information */}
              <div className="space-y-4">
                <h3 className="font-medium flex items-center gap-2">
                  <CreditCard size={16} />
                  Card Information
                </h3>
                <div>
                  <Label>Card Number *</Label>
                  <div className="relative">
                    <Input
                      placeholder="1234 5678 9012 3456"
                      value={formData.card_number}
                      onChange={(e) => setFormData({...formData, card_number: formatCardNumber(e.target.value)})}
                      maxLength={19}
                      className="font-mono pr-20"
                      required
                      data-testid="vt-card-number"
                    />
                    {cardInfo.brand && (
                      <span className={`absolute right-3 top-1/2 -translate-y-1/2 ${cardInfo.color} text-white text-xs px-2 py-1 rounded font-medium`}>
                        {cardInfo.brand}
                      </span>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Expiry Date *</Label>
                    <Input
                      placeholder="MM/YY"
                      value={formData.card_expiry}
                      onChange={(e) => setFormData({...formData, card_expiry: formatExpiry(e.target.value)})}
                      maxLength={5}
                      className="font-mono"
                      required
                      data-testid="vt-card-expiry"
                    />
                  </div>
                  <div>
                    <Label>CVV *</Label>
                    <Input
                      type="password"
                      placeholder="***"
                      value={formData.card_cvv}
                      onChange={(e) => setFormData({...formData, card_cvv: e.target.value.replace(/\D/g, '').slice(0, 4)})}
                      maxLength={4}
                      className="font-mono"
                      required
                      data-testid="vt-card-cvv"
                    />
                  </div>
                </div>
                <div>
                  <Label>Cardholder Name *</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                    <Input
                      placeholder="John Doe"
                      value={formData.cardholder_name}
                      onChange={(e) => setFormData({...formData, cardholder_name: e.target.value})}
                      className="pl-10"
                      required
                      data-testid="vt-cardholder"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Customer Information */}
              <div className="space-y-4">
                <h3 className="font-medium">Customer Information (Optional)</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                      <Input
                        type="email"
                        placeholder="customer@email.com"
                        value={formData.customer_email}
                        onChange={(e) => setFormData({...formData, customer_email: e.target.value})}
                        className="pl-10"
                        data-testid="vt-email"
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Phone</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                      <Input
                        placeholder="(555) 123-4567"
                        value={formData.customer_phone}
                        onChange={(e) => setFormData({...formData, customer_phone: e.target.value})}
                        className="pl-10"
                        data-testid="vt-phone"
                      />
                    </div>
                  </div>
                </div>
                <div>
                  <Label>Description/Notes</Label>
                  <div className="relative">
                    <FileText className="absolute left-3 top-3 text-slate-400" size={16} />
                    <Input
                      placeholder="Order #12345, Phone order, etc."
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      className="pl-10"
                      data-testid="vt-description"
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button 
                  type="submit" 
                  className="flex-1 h-12 text-lg"
                  disabled={loading || !formData.merchant_id}
                  data-testid="vt-submit"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <RefreshCw className="animate-spin" size={18} />
                      Processing...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <CreditCard size={18} />
                      Process ${formData.amount || '0.00'}
                    </span>
                  )}
                </Button>
                <Button type="button" variant="outline" onClick={resetForm} data-testid="vt-reset">
                  Clear
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Result Panel */}
        <div className="space-y-6">
          {/* Transaction Result */}
          {result && (
            <Card className={result.status === 'approved' ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}>
              <CardContent className="pt-6">
                <div className="text-center">
                  {result.status === 'approved' ? (
                    <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
                  ) : (
                    <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                  )}
                  <h3 className={`text-2xl font-bold ${result.status === 'approved' ? 'text-emerald-700' : 'text-red-700'}`}>
                    {result.status === 'approved' ? 'APPROVED' : 'DECLINED'}
                  </h3>
                  <p className="text-sm mt-1 text-slate-600">{result.response_message}</p>
                  
                  {result.status === 'approved' && (
                    <div className="mt-4 pt-4 border-t border-emerald-200 space-y-2 text-left">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Amount:</span>
                        <span className="font-semibold">${result.amount?.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Auth Code:</span>
                        <span className="font-mono font-semibold">{result.auth_code}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Card:</span>
                        <span className="font-mono">****{result.card_last_four}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Transaction ID:</span>
                        <span className="font-mono text-xs">{result.id?.slice(0, 12)}...</span>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Tips</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-slate-600 space-y-2">
              <p>• <strong>Sale</strong> - Immediate charge to card</p>
              <p>• <strong>Authorization</strong> - Reserve funds only</p>
              <p>• <strong>Refund</strong> - Return funds to card</p>
              <Separator className="my-3" />
              <p className="text-xs text-slate-500">Test Card: 4111 1111 1111 1111</p>
              <p className="text-xs text-slate-500">Expiry: Any future date</p>
              <p className="text-xs text-slate-500">CVV: Any 3 digits</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
