import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import { Upload, FileText, CheckCircle, AlertCircle, RefreshCw, Save, Zap, Play, MapPin, CreditCard, Network, Building, Phone, Globe } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function VarSheetPage() {
  const [merchants, setMerchants] = useState([]);
  const [varsheets, setVarsheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [selectedMerchant, setSelectedMerchant] = useState('');
  const [selectedVarsheet, setSelectedVarsheet] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetchMerchants();
    fetchVarsheets();
  }, []);

  const fetchMerchants = async () => {
    try {
      const response = await axios.get(`${API}/merchants`);
      setMerchants(response.data);
    } catch (error) {
      console.error('Failed to fetch merchants:', error);
    }
  };

  const fetchVarsheets = async () => {
    try {
      const response = await axios.get(`${API}/admin/varsheets`);
      setVarsheets(response.data);
    } catch (error) {
      console.error('Failed to fetch varsheets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!selectedMerchant) {
      toast.error('Please select a merchant first');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF files are supported');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('merchant_id', selectedMerchant);

    try {
      const response = await axios.post(`${API}/admin/varsheet/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('VAR Sheet uploaded successfully');
      setSelectedVarsheet(response.data);
      fetchVarsheets();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  }, [selectedMerchant]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleParse = async () => {
    if (!selectedVarsheet) return;
    
    setParsing(true);
    try {
      const response = await axios.post(`${API}/admin/varsheet/${selectedVarsheet.id}/parse`);
      setParsedData(response.data.parsed_json);
      setSelectedVarsheet({ ...selectedVarsheet, ...response.data });
      toast.success(`VAR Sheet parsed - ${response.data.parsed_json?.confidence_score || 0}% confidence`);
      fetchVarsheets();
    } catch (error) {
      toast.error('Parsing failed');
    } finally {
      setParsing(false);
    }
  };

  const handleSaveParsedData = async () => {
    if (!selectedVarsheet || !parsedData) return;
    
    try {
      await axios.put(`${API}/admin/varsheet/${selectedVarsheet.id}`, parsedData);
      toast.success('Changes saved');
      fetchVarsheets();
    } catch (error) {
      toast.error('Failed to save changes');
    }
  };

  const handleCreateTerminal = async () => {
    if (!selectedVarsheet || !parsedData) return;
    
    try {
      const terminalData = {
        merchant_id: selectedVarsheet.merchant_id,
        provider: 'tsys',
        v_number: parsedData.v_number_primary,
        merchant_number: parsedData.merchant_number,
        terminal_number: parsedData.terminal_number,
        bin: parsedData.bin,
        chain: parsedData.chain,
        store_number: parsedData.store_number,
        agent_code: parsedData.agent,
        edc_primary: parsedData.edc_primary,
        edc_secondary: parsedData.edc_secondary,
        amex_se: parsedData.amex_se,
        disc_se: parsedData.disc_se,
        aba: parsedData.aba,
        reimbursement_att: parsedData.reimbursement_att,
        card_types: parsedData.card_types,
        networks: parsedData.networks,
        raw_comments: parsedData.raw_comments,
        provisioning_status: 'draft'
      };
      
      await axios.post(`${API}/admin/terminals`, terminalData);
      toast.success('Terminal profile created');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create terminal');
    }
  };

  const selectVarsheet = async (vs) => {
    setSelectedVarsheet(vs);
    if (vs.parsed_json) {
      setParsedData(vs.parsed_json);
    } else {
      setParsedData(null);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      success: 'badge-success',
      needs_review: 'badge-warning',
      failed: 'badge-error',
      pending: 'badge-pending'
    };
    return <span className={`badge ${styles[status] || 'badge-pending'}`}>{status}</span>;
  };

  const updateField = (field, value) => {
    setParsedData({ ...parsedData, [field]: value });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">VAR Sheet Setup (TSYS)</h1>
        <p className="text-slate-500 mt-1">Upload and parse TSYS VAR Form / Express Keysheets for terminal provisioning</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Section */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload size={20} />
              Upload VAR Sheet
            </CardTitle>
            <CardDescription>Select a merchant and upload the PDF</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Select Merchant</Label>
              <Select value={selectedMerchant} onValueChange={setSelectedMerchant}>
                <SelectTrigger data-testid="varsheet-merchant-select">
                  <SelectValue placeholder="Choose merchant..." />
                </SelectTrigger>
                <SelectContent>
                  {merchants.map((m) => (
                    <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div
              className={`upload-zone ${dragOver ? 'dragover' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-upload').click()}
              data-testid="varsheet-upload-zone"
            >
              <input
                id="file-upload"
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0])}
              />
              <FileText className="w-12 h-12 mx-auto mb-3 text-slate-400" />
              {uploading ? (
                <p className="text-sm text-slate-600">Uploading...</p>
              ) : (
                <>
                  <p className="text-sm text-slate-600">Drop TSYS VAR Sheet PDF here</p>
                  <p className="text-xs text-slate-400 mt-1">or click to browse</p>
                </>
              )}
            </div>

            {/* Recent Uploads */}
            <div>
              <Label className="mb-2 block">Recent Uploads</Label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {varsheets.map((vs) => (
                  <div
                    key={vs.id}
                    onClick={() => selectVarsheet(vs)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedVarsheet?.id === vs.id 
                        ? 'border-primary bg-primary/5' 
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    data-testid={`varsheet-item-${vs.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">{vs.filename}</span>
                      {getStatusBadge(vs.parse_status)}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {new Date(vs.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                {varsheets.length === 0 && (
                  <p className="text-sm text-slate-400 text-center py-4">No uploads yet</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Parsed Results */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Parsed Results</CardTitle>
                <CardDescription>
                  {selectedVarsheet 
                    ? `Editing: ${selectedVarsheet.filename}` 
                    : 'Select a VAR sheet to view/edit'}
                  {parsedData?.confidence_score && (
                    <span className="ml-2 text-emerald-600 font-medium">
                      ({parsedData.confidence_score}% confidence)
                    </span>
                  )}
                </CardDescription>
              </div>
              {selectedVarsheet && (
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={handleParse}
                    disabled={parsing}
                    data-testid="parse-varsheet-btn"
                  >
                    {parsing ? <RefreshCw className="animate-spin mr-2" size={16} /> : <Play size={16} className="mr-2" />}
                    Parse PDF
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedVarsheet && parsedData ? (
              <Tabs defaultValue="merchant" className="w-full">
                <TabsList className="mb-4 flex-wrap">
                  <TabsTrigger value="merchant">Merchant Info</TabsTrigger>
                  <TabsTrigger value="terminal">Terminal IDs</TabsTrigger>
                  <TabsTrigger value="location">Location</TabsTrigger>
                  <TabsTrigger value="cards">Card Types</TabsTrigger>
                  <TabsTrigger value="networks">Networks</TabsTrigger>
                  <TabsTrigger value="comments">Comments/SE</TabsTrigger>
                </TabsList>

                {/* MERCHANT INFO TAB */}
                <TabsContent value="merchant" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <Building size={18} />
                    <span className="font-medium">Merchant Information</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label>Merchant Name</Label>
                      <Input
                        value={parsedData.merchant_name || ''}
                        onChange={(e) => updateField('merchant_name', e.target.value)}
                        data-testid="parsed-merchant-name"
                      />
                    </div>
                    <div>
                      <Label>Merchant Number</Label>
                      <Input
                        value={parsedData.merchant_number || ''}
                        onChange={(e) => updateField('merchant_number', e.target.value)}
                        className="font-mono"
                        data-testid="parsed-merchant-number"
                      />
                    </div>
                    <div>
                      <Label>Terminal Status</Label>
                      <Input
                        value={parsedData.terminal_status || ''}
                        onChange={(e) => updateField('terminal_status', e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>V Number (Primary)</Label>
                      <Input
                        value={parsedData.v_number_primary || ''}
                        onChange={(e) => updateField('v_number_primary', e.target.value)}
                        className="font-mono"
                        data-testid="parsed-v-number"
                      />
                    </div>
                    <div>
                      <Label>V Number (Secondary)</Label>
                      <Input
                        value={parsedData.v_number_secondary || ''}
                        onChange={(e) => updateField('v_number_secondary', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Industry Type</Label>
                      <Select 
                        value={parsedData.industry_type || ''} 
                        onValueChange={(v) => updateField('industry_type', v)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Retail">Retail</SelectItem>
                          <SelectItem value="Restaurant">Restaurant</SelectItem>
                          <SelectItem value="QSR">QSR</SelectItem>
                          <SelectItem value="Lodging">Lodging</SelectItem>
                          <SelectItem value="Direct Marketing">Direct Marketing</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>VISA MCC</Label>
                      <Input
                        value={parsedData.visa_mcc || ''}
                        onChange={(e) => updateField('visa_mcc', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                  </div>
                </TabsContent>

                {/* TERMINAL IDS TAB */}
                <TabsContent value="terminal" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <CreditCard size={18} />
                    <span className="font-medium">Terminal & Processing IDs</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Terminal #</Label>
                      <Input
                        value={parsedData.terminal_number || ''}
                        onChange={(e) => updateField('terminal_number', e.target.value)}
                        className="font-mono"
                        data-testid="parsed-terminal-number"
                      />
                    </div>
                    <div>
                      <Label>BIN</Label>
                      <Input
                        value={parsedData.bin || ''}
                        onChange={(e) => updateField('bin', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Agent</Label>
                      <Input
                        value={parsedData.agent || ''}
                        onChange={(e) => updateField('agent', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Chain</Label>
                      <Input
                        value={parsedData.chain || ''}
                        onChange={(e) => updateField('chain', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Store Number</Label>
                      <Input
                        value={parsedData.store_number || ''}
                        onChange={(e) => updateField('store_number', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Location Number</Label>
                      <Input
                        value={parsedData.location_number || ''}
                        onChange={(e) => updateField('location_number', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>EDC Primary</Label>
                      <Input
                        value={parsedData.edc_primary || ''}
                        onChange={(e) => updateField('edc_primary', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>EDC Secondary</Label>
                      <Input
                        value={parsedData.edc_secondary || ''}
                        onChange={(e) => updateField('edc_secondary', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                  </div>
                </TabsContent>

                {/* LOCATION TAB */}
                <TabsContent value="location" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <MapPin size={18} />
                    <span className="font-medium">Location Information</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label>Street Address</Label>
                      <Input
                        value={parsedData.street_address || ''}
                        onChange={(e) => updateField('street_address', e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>City</Label>
                      <Input
                        value={parsedData.city || ''}
                        onChange={(e) => updateField('city', e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>State</Label>
                      <Input
                        value={parsedData.state || ''}
                        onChange={(e) => updateField('state', e.target.value)}
                        maxLength={2}
                        className="uppercase"
                      />
                    </div>
                    <div>
                      <Label>Postal Code</Label>
                      <Input
                        value={parsedData.postal_code || ''}
                        onChange={(e) => updateField('postal_code', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Phone</Label>
                      <Input
                        value={parsedData.phone || ''}
                        onChange={(e) => updateField('phone', e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>Country</Label>
                      <Input
                        value={parsedData.country || ''}
                        onChange={(e) => updateField('country', e.target.value)}
                        maxLength={2}
                      />
                    </div>
                    <div>
                      <Label>Currency Code</Label>
                      <Input
                        value={parsedData.currency_code || ''}
                        onChange={(e) => updateField('currency_code', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div>
                      <Label>Time Zone</Label>
                      <Input
                        value={parsedData.time_zone || ''}
                        onChange={(e) => updateField('time_zone', e.target.value)}
                      />
                    </div>
                    <div>
                      <Label>Time Zone Differential</Label>
                      <Input
                        value={parsedData.time_zone_differential || ''}
                        onChange={(e) => updateField('time_zone_differential', e.target.value)}
                        className="font-mono"
                      />
                    </div>
                  </div>
                </TabsContent>

                {/* CARD TYPES TAB */}
                <TabsContent value="cards" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <CreditCard size={18} />
                    <span className="font-medium">Accepted Card Types</span>
                  </div>
                  <div>
                    <Label>Card Types (comma separated)</Label>
                    <Input
                      value={parsedData.card_types?.join(', ') || ''}
                      onChange={(e) => updateField('card_types', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                      placeholder="VISA, MasterCard, American Express, JCB, Discover, ATM/Debit"
                      data-testid="parsed-card-types"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Common: VISA, MasterCard, American Express, JCB, Discover, ATM/Debit
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-4">
                    {parsedData.card_types?.map((card, idx) => (
                      <span key={idx} className="badge badge-info">{card}</span>
                    ))}
                  </div>
                </TabsContent>

                {/* NETWORKS TAB */}
                <TabsContent value="networks" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <Network size={18} />
                    <span className="font-medium">Networks & Sharing Groups</span>
                  </div>
                  <div>
                    <Label>Networks (comma separated)</Label>
                    <Input
                      value={parsedData.networks?.join(', ') || ''}
                      onChange={(e) => updateField('networks', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                      placeholder="Pulse, Interlink, STAR, Maestro, NYCE, ACCEL, EBT POS, Visa PAVD"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Common TSYS Networks: Pulse, Interlink, STAR, Maestro, NYCE, ACCEL, EBT POS, Visa PAVD
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-4">
                    {parsedData.networks?.map((network, idx) => (
                      <span key={idx} className="badge badge-success">{network}</span>
                    ))}
                  </div>
                  <Separator className="my-4" />
                  <div>
                    <Label>Host Capture Participant</Label>
                    <Select 
                      value={parsedData.host_capture_participant || ''} 
                      onValueChange={(v) => updateField('host_capture_participant', v)}
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Y">Yes (Y)</SelectItem>
                        <SelectItem value="N">No (N)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </TabsContent>

                {/* COMMENTS/SE TAB */}
                <TabsContent value="comments" className="space-y-4">
                  <div className="flex items-center gap-2 mb-4 text-slate-600">
                    <Globe size={18} />
                    <span className="font-medium">Financial Identifiers (from Comments)</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>AMEX SE</Label>
                      <Input
                        value={parsedData.amex_se || ''}
                        onChange={(e) => updateField('amex_se', e.target.value)}
                        className="font-mono"
                        placeholder="10-digit"
                      />
                    </div>
                    <div>
                      <Label>Discover SE</Label>
                      <Input
                        value={parsedData.disc_se || ''}
                        onChange={(e) => updateField('disc_se', e.target.value)}
                        className="font-mono"
                        placeholder="15-digit"
                      />
                    </div>
                    <div>
                      <Label>ABA / Routing Number</Label>
                      <Input
                        value={parsedData.aba || ''}
                        onChange={(e) => updateField('aba', e.target.value)}
                        className="font-mono"
                        placeholder="9-digit"
                      />
                    </div>
                    <div>
                      <Label>Reimbursement ATT</Label>
                      <Input
                        value={parsedData.reimbursement_att || ''}
                        onChange={(e) => updateField('reimbursement_att', e.target.value)}
                        className="font-mono uppercase"
                        maxLength={1}
                      />
                    </div>
                    <div className="col-span-2">
                      <Label>Raw Comments</Label>
                      <Textarea
                        value={parsedData.raw_comments || ''}
                        onChange={(e) => updateField('raw_comments', e.target.value)}
                        rows={4}
                        placeholder="Full comments section from VAR sheet..."
                      />
                    </div>
                  </div>
                  
                  {/* Extraction Notes */}
                  {parsedData.extraction_notes?.length > 0 && (
                    <div className="mt-4 p-4 bg-slate-50 rounded-lg">
                      <Label className="mb-2 block">Extraction Notes</Label>
                      <ul className="text-xs text-slate-600 space-y-1">
                        {parsedData.extraction_notes.map((note, idx) => (
                          <li key={idx}>• {note}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </TabsContent>

                {/* Actions */}
                <div className="flex gap-3 mt-6 pt-6 border-t">
                  <Button variant="outline" onClick={handleSaveParsedData} data-testid="save-draft-btn">
                    <Save size={16} className="mr-2" />
                    Save Draft
                  </Button>
                  <Button variant="outline" onClick={handleCreateTerminal} data-testid="provision-terminal-btn">
                    <Zap size={16} className="mr-2" />
                    Create Terminal Profile
                  </Button>
                  <Button data-testid="mark-live-btn">
                    <CheckCircle size={16} className="mr-2" />
                    Mark Live
                  </Button>
                </div>
              </Tabs>
            ) : selectedVarsheet ? (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 mx-auto mb-3 text-amber-500" />
                <p className="text-slate-600">This VAR sheet has not been parsed yet</p>
                <Button className="mt-4" onClick={handleParse} disabled={parsing}>
                  {parsing ? 'Parsing...' : 'Parse VAR Sheet'}
                </Button>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select a VAR sheet from the list to view parsed data</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
