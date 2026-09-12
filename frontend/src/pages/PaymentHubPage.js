import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';
import { Activity, RefreshCw, Link2, ClipboardCheck, AlertTriangle, Server } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Honest status rendering: UNKNOWN is never shown as healthy.
const STATUS_STYLES = {
  ONLINE: 'badge-success',
  PASS: 'badge-success',
  READY: 'badge-success',
  online: 'badge-success',
  DEGRADED: 'badge-warning',
  WARN: 'badge-warning',
  OFFLINE: 'badge-error',
  offline: 'badge-error',
  FAIL: 'badge-error',
  NOT_READY: 'badge-error',
  UNKNOWN: 'badge-pending',
  unknown: 'badge-pending',
  NOT_CONFIGURED: 'badge-pending',
};

const StatusBadge = ({ status }) => (
  <span className={`badge ${STATUS_STYLES[status] || 'badge-pending'}`}>
    {String(status || 'UNKNOWN').replace(/_/g, ' ').toUpperCase()}
  </span>
);

const EnvBadge = ({ environment }) => (
  <span className={`badge ${environment === 'production' ? 'badge-error' : 'badge-info'}`}
    title="Payment Hub environment">
    {String(environment || 'unknown').toUpperCase()}
  </span>
);

export default function PaymentHubPage() {
  const { hasRole } = useAuth();
  const canDiagnose = hasRole('SUPER_ADMIN', 'OPERATIONS', 'SUPPORT');
  const canOperate = hasRole('SUPER_ADMIN', 'OPERATIONS');

  const [status, setStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(true);

  const [merchants, setMerchants] = useState([]);
  const [adminTerminals, setAdminTerminals] = useState([]);
  const [links, setLinks] = useState({ merchant_links: [], terminal_links: [] });

  const [hubViewMerchant, setHubViewMerchant] = useState('');
  const [hubView, setHubView] = useState(null);
  const [hubViewLoading, setHubViewLoading] = useState(false);
  const [pingResults, setPingResults] = useState({});
  const [pinging, setPinging] = useState({});
  const [bulkState, setBulkState] = useState(null);

  const [readinessMerchant, setReadinessMerchant] = useState('');
  const [readiness, setReadiness] = useState(null);
  const [readinessLoading, setReadinessLoading] = useState(false);

  const [events, setEvents] = useState(null);

  const [linkDialog, setLinkDialog] = useState(null); // {type: 'merchant'|'terminal', record}
  const [linkValue, setLinkValue] = useState('');
  const [linkSerial, setLinkSerial] = useState('');

  const fetchStatus = useCallback(async (manual = false) => {
    setStatusLoading(true);
    try {
      const response = await axios.get(`${API}/hub/status${manual ? '?manual=true' : ''}`);
      setStatus(response.data);
    } catch (error) {
      toast.error('Failed to reach admin backend for Hub status');
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchLinksAndMerchants();
  }, [fetchStatus]);

  const fetchLinksAndMerchants = async () => {
    try {
      const [m, t, l] = await Promise.all([
        axios.get(`${API}/merchants?page_size=500`),
        axios.get(`${API}/admin/terminals?page_size=200`),
        axios.get(`${API}/hub/links`),
      ]);
      setMerchants(m.data.items);
      setAdminTerminals(t.data.items);
      setLinks(l.data);
    } catch (error) {
      console.error('Failed to fetch link data');
    }
  };

  const fetchHubView = async (merchantId) => {
    if (!merchantId) return;
    setHubViewLoading(true);
    setHubView(null);
    setBulkState(null);
    try {
      const response = await axios.get(`${API}/hub/merchants/${merchantId}/hub-view`);
      setHubView(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load Hub view');
    } finally {
      setHubViewLoading(false);
    }
  };

  const fetchEvents = async () => {
    setEvents({ loading: true });
    try {
      const response = await axios.get(`${API}/hub/events`);
      setEvents(response.data);
    } catch (error) {
      setEvents({ stats: { status: 'UNKNOWN', detail: 'Admin backend request failed' } });
    }
  };

  const hubProfiles = hubView?.lookup?.status === 'ONLINE'
    ? (hubView.lookup.data?.profiles || [])
    : [];

  const pingProfile = async (profileId) => {
    setPinging((p) => ({ ...p, [profileId]: true }));
    try {
      const response = await axios.post(`${API}/hub/profiles/${profileId}/ping`);
      setPingResults((r) => ({ ...r, [profileId]: response.data }));
      if (response.data.state === 'online') toast.success(`Ping OK (${response.data.latency_ms} ms)`);
      else toast.error(`Ping ${response.data.state.toUpperCase()}: ${response.data.detail || ''}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ping request failed');
    } finally {
      setPinging((p) => ({ ...p, [profileId]: false }));
    }
  };

  const bulkPing = async () => {
    const ids = hubProfiles.map((p) => String(p.id)).filter(Boolean);
    if (!ids.length) {
      toast.error('No Hub processor profiles to ping');
      return;
    }
    setBulkState({ running: true, total: Math.min(ids.length, 50) });
    try {
      const response = await axios.post(`${API}/hub/profiles/bulk-ping`, { profile_ids: ids.slice(0, 50) });
      setBulkState({ done: true, ...response.data });
      const next = {};
      response.data.results.forEach((r) => {
        next[r.profile_id] = { state: r.state, latency_ms: r.latency_ms, detail: r.detail };
      });
      setPingResults((prev) => ({ ...prev, ...next }));
    } catch (error) {
      setBulkState(null);
      toast.error(error.response?.data?.detail || 'Bulk ping failed');
    }
  };

  const runReadiness = async () => {
    if (!readinessMerchant) return;
    setReadinessLoading(true);
    setReadiness(null);
    try {
      const response = await axios.get(`${API}/hub/merchants/${readinessMerchant}/readiness`);
      setReadiness(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Readiness check failed');
    } finally {
      setReadinessLoading(false);
    }
  };

  const saveLink = async () => {
    if (!linkDialog || !linkValue.trim()) return;
    try {
      if (linkDialog.type === 'merchant') {
        const response = await axios.put(`${API}/hub/links/merchants/${linkDialog.record.id}`, {
          hub_merchant_id: linkValue.trim(),
        });
        if (response.data.verified_against_hub) {
          toast.success('Mapping saved and verified against the live Hub');
        } else {
          toast.warning(`Mapping saved but NOT verified: ${response.data.verification_detail || 'Hub unreachable'}`);
        }
      } else {
        await axios.put(`${API}/hub/links/terminals/${linkDialog.record.id}`, {
          hub_terminal_id: linkValue.trim(),
          terminal_serial: linkSerial.trim() || null,
        });
        toast.success('Terminal mapping saved');
      }
      setLinkDialog(null);
      setLinkValue('');
      setLinkSerial('');
      fetchLinksAndMerchants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save mapping');
    }
  };

  const merchantLink = (id) => links.merchant_links.find((l) => l.merchant_id === id);
  const terminalLink = (id) => links.terminal_links.find((l) => l.terminal_id === id);
  const notConfigured = status && !status.configured;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
            Payment Hub
            {status && <EnvBadge environment={status.environment} />}
          </h1>
          <p className="text-slate-500 mt-1">Live operations console for AsterPOS Payment Hub - real diagnostics only, nothing simulated</p>
        </div>
        <Button variant="outline" onClick={() => fetchStatus(true)} disabled={statusLoading} data-testid="hub-refresh-btn">
          <RefreshCw size={16} className={`mr-2 ${statusLoading ? 'animate-spin' : ''}`} />
          Run Health Checks
        </Button>
      </div>

      {notConfigured && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-5 flex items-start gap-3">
            <AlertTriangle className="text-amber-600 mt-0.5" size={20} />
            <div>
              <p className="font-medium text-amber-800">Payment Hub is not configured</p>
              <p className="text-sm text-amber-700 mt-1">
                Set <code className="font-mono">PAYMENT_HUB_URL</code> and <code className="font-mono">PAYMENT_HUB_ADMIN_KEY</code> in
                the admin backend environment. Until then every Hub status below shows NOT CONFIGURED - nothing is simulated.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Hub Status</p>
            <div className="text-2xl font-bold">{status ? <StatusBadge status={status.overall} /> : '...'}</div>
            <p className="text-xs text-slate-500 mt-2">
              Last check: {status?.checked_at ? new Date(status.checked_at).toLocaleTimeString() : '-'}
            </p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Merchants Linked</p>
            <p className="text-3xl font-bold tabular-nums">{links.merchant_links.length}</p>
            <p className="text-xs text-slate-500 mt-2">of {merchants.length} admin merchants</p>
          </CardContent>
        </Card>
        <Card className="stats-card">
          <CardContent className="pt-5">
            <p className="overline mb-1">Hub Alerts</p>
            <p className="text-3xl font-bold tabular-nums">
              {status?.alerts?.alerts ? status.alerts.alerts.length : status?.alerts ? 0 : '—'}
            </p>
            <p className="text-xs text-slate-500 mt-2">{status?.alerts ? 'from Hub metrics' : 'Not available'}</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="terminals">Merchant Terminals</TabsTrigger>
          <TabsTrigger value="readiness">Go-Live Readiness</TabsTrigger>
          <TabsTrigger value="links">Mappings</TabsTrigger>
          <TabsTrigger value="events" onClick={fetchEvents}>Events</TabsTrigger>
        </TabsList>

        {/* OVERVIEW */}
        <TabsContent value="overview" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Server size={18} /> Connectivity Tests</CardTitle>
              <CardDescription>Live results from the Hub API · correlation ID {status?.correlation_id || '-'}</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead><tr><th>Test</th><th>Status</th><th>Latency</th><th>Detail</th></tr></thead>
                  <tbody>
                    {(status?.checks || []).map((c) => (
                      <tr key={c.test}>
                        <td className="font-medium">{c.test}</td>
                        <td><StatusBadge status={c.status} /></td>
                        <td className="tabular-nums">{c.latency_ms != null ? `${c.latency_ms} ms` : '-'}</td>
                        <td className="text-sm text-slate-500">{c.detail || '-'}</td>
                      </tr>
                    ))}
                    {!status?.checks?.length && (
                      <tr><td colSpan={4} className="text-center text-slate-400 py-8">Run health checks to see results</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {status?.dependencies && (
            <Card>
              <CardHeader><CardTitle className="text-base">Hub Dependencies (from /ready)</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs bg-slate-50 rounded-lg p-4 overflow-x-auto">{JSON.stringify(status.dependencies, null, 2)}</pre>
              </CardContent>
            </Card>
          )}

          {status?.alerts && (
            <Card>
              <CardHeader><CardTitle className="text-base">Triggered Hub Alerts</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs bg-slate-50 rounded-lg p-4 overflow-x-auto max-h-[300px]">{JSON.stringify(status.alerts, null, 2)}</pre>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* MERCHANT TERMINALS */}
        <TabsContent value="terminals" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hub View of a Merchant</CardTitle>
              <CardDescription>
                Live from the Hub: processor profiles, terminals, and routing. Ping runs a real device probe
                (SPIn ConnectionStatus / Valor device info) through the Hub.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 items-end flex-wrap">
                <div className="min-w-[240px]">
                  <Label>Merchant</Label>
                  <Select value={hubViewMerchant} onValueChange={(v) => { setHubViewMerchant(v); fetchHubView(v); }}>
                    <SelectTrigger data-testid="hubview-merchant-select"><SelectValue placeholder="Select merchant..." /></SelectTrigger>
                    <SelectContent>
                      {merchants.map((m) => <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                {canOperate && hubProfiles.length > 0 && (
                  <Button onClick={bulkPing} disabled={bulkState?.running} data-testid="bulk-ping-btn">
                    {bulkState?.running ? 'Pinging...' : `Ping All Profiles (${hubProfiles.length})`}
                  </Button>
                )}
              </div>

              {hubViewLoading && <div className="py-8 text-center text-slate-400">Loading from Hub...</div>}

              {hubView && !hubView.linked && (
                <div className="py-6 text-center text-slate-500">
                  <p>{hubView.detail}</p>
                  <p className="text-sm mt-1">Link it on the Mappings tab first.</p>
                </div>
              )}

              {hubView?.linked && hubView.lookup?.status !== 'ONLINE' && (
                <div className="py-6 text-center text-slate-400">
                  <StatusBadge status={hubView.lookup?.status || 'UNKNOWN'} />
                  <p className="mt-2 text-sm">{hubView.lookup?.detail || 'Hub lookup unavailable'}</p>
                </div>
              )}

              {hubView?.linked && hubView.lookup?.status === 'ONLINE' && (
                <>
                  {bulkState?.done && (
                    <div className="text-sm flex gap-4">
                      <span className="text-emerald-600 font-medium">Online: {bulkState.counts.online}</span>
                      <span className="text-red-600 font-medium">Offline: {bulkState.counts.offline}</span>
                      <span className="text-slate-500 font-medium">Unknown: {bulkState.counts.unknown}</span>
                      <span className="text-slate-400">({bulkState.pinged} pinged)</span>
                    </div>
                  )}
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead><tr><th>Profile</th><th>Processor</th><th>Cached Status</th><th>Live Ping</th><th></th></tr></thead>
                      <tbody>
                        {hubProfiles.map((p) => {
                          const id = String(p.id);
                          const ping = pingResults[id];
                          return (
                            <tr key={id}>
                              <td className="font-mono text-sm">{p.display_name || id.slice(0, 12)}</td>
                              <td className="capitalize">{p.processor || '-'}</td>
                              <td>{p.connectivity_status ? <StatusBadge status={p.connectivity_status} /> : <span className="badge badge-pending">NOT REPORTED</span>}</td>
                              <td className="text-sm">
                                {ping ? (
                                  <span className="flex items-center gap-2">
                                    <StatusBadge status={ping.state} />
                                    {ping.latency_ms != null && <span className="tabular-nums text-slate-500">{ping.latency_ms} ms</span>}
                                  </span>
                                ) : '-'}
                              </td>
                              <td>
                                {canDiagnose && (
                                  <Button variant="outline" size="sm" disabled={pinging[id]} onClick={() => pingProfile(id)} data-testid={`ping-${id}`}>
                                    {pinging[id] ? 'Pinging...' : 'Ping'}
                                  </Button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                        {!hubProfiles.length && (
                          <tr><td colSpan={5} className="text-center text-slate-400 py-6">Hub reports no processor profiles for this merchant</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {hubView.routing?.status === 'ONLINE' && hubView.routing.data && (
                    <div>
                      <p className="font-medium text-sm mb-2">Routing / Payment Path (live from Hub)</p>
                      <pre className="text-xs bg-slate-50 rounded-lg p-4 overflow-x-auto">{JSON.stringify(hubView.routing.data, null, 2)}</pre>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* READINESS */}
        <TabsContent value="readiness" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><ClipboardCheck size={18} /> Merchant Go-Live Readiness</CardTitle>
              <CardDescription>Computed from real records and live Hub/device responses. Unknown critical checks block READY.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 items-end flex-wrap">
                <div className="min-w-[240px]">
                  <Label>Merchant</Label>
                  <Select value={readinessMerchant} onValueChange={setReadinessMerchant}>
                    <SelectTrigger data-testid="readiness-merchant-select"><SelectValue placeholder="Select merchant..." /></SelectTrigger>
                    <SelectContent>
                      {merchants.map((m) => <SelectItem key={m.id} value={m.id}>{m.business_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={runReadiness} disabled={!readinessMerchant || readinessLoading} data-testid="run-readiness-btn">
                  {readinessLoading ? <RefreshCw size={16} className="animate-spin mr-2" /> : <Activity size={16} className="mr-2" />}
                  Run Readiness Check
                </Button>
                {readiness && <StatusBadge status={readiness.overall} />}
              </div>

              {readiness && (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
                    <tbody>
                      {readiness.checks.map((c) => (
                        <tr key={c.check}>
                          <td className="font-medium">{c.check}{c.critical && <span className="text-xs text-slate-400 ml-2">critical</span>}</td>
                          <td><StatusBadge status={c.status} /></td>
                          <td className="text-sm text-slate-500">{c.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="text-xs text-slate-400 mt-2">Correlation ID: {readiness.correlation_id}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* MAPPINGS */}
        <TabsContent value="links" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><Link2 size={18} /> Merchant Mappings</CardTitle>
              <CardDescription>
                Persisted references to Hub merchant records (Hub user UUID, hub_mid, or Hub id).
                Saving verifies the identifier against the live Hub.
                {merchants.length >= 500 && ' Showing the first 500 merchants - use the Merchants page search to find others.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead><tr><th>Merchant</th><th>Status</th><th>Hub Merchant ID</th><th>Environment</th><th></th></tr></thead>
                  <tbody>
                    {merchants.map((m) => {
                      const link = merchantLink(m.id);
                      return (
                        <tr key={m.id}>
                          <td className="font-medium">{m.business_name}</td>
                          <td><span className={`badge ${m.status === 'active' ? 'badge-success' : 'badge-warning'}`}>{m.status}</span></td>
                          <td className="font-mono text-sm">{link ? link.hub_merchant_id : <span className="text-slate-400">not linked</span>}</td>
                          <td className="text-sm text-slate-500">{link?.environment || '-'}</td>
                          <td>
                            {canOperate && (
                              <Button variant="outline" size="sm" onClick={() => { setLinkDialog({ type: 'merchant', record: m }); setLinkValue(link?.hub_merchant_id || ''); }}>
                                {link ? 'Edit Link' : 'Link to Hub'}
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Terminal Mappings</CardTitle>
              <CardDescription>
                Admin terminal registry rows mapped to Hub terminal IDs / device serials.
                {adminTerminals.length >= 200 && ' Showing the first 200 terminals.'}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead><tr><th>Terminal #</th><th>Merchant</th><th>Hub Terminal ID</th><th>Serial</th><th></th></tr></thead>
                  <tbody>
                    {adminTerminals.map((t) => {
                      const link = terminalLink(t.id);
                      const merchant = merchants.find((m) => m.id === t.merchant_id);
                      return (
                        <tr key={t.id}>
                          <td className="font-mono">{t.terminal_number || '-'}</td>
                          <td>{merchant?.business_name || 'Unknown'}</td>
                          <td className="font-mono text-sm">{link ? link.hub_terminal_id : <span className="text-slate-400">not linked</span>}</td>
                          <td className="font-mono text-sm">{link?.terminal_serial || '-'}</td>
                          <td>
                            {canOperate && (
                              <Button variant="outline" size="sm" onClick={() => { setLinkDialog({ type: 'terminal', record: t }); setLinkValue(link?.hub_terminal_id || ''); setLinkSerial(link?.terminal_serial || ''); }}>
                                {link ? 'Edit Link' : 'Link to Hub'}
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {!adminTerminals.length && (
                      <tr><td colSpan={5} className="text-center text-slate-400 py-6">No terminals in the admin registry yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* EVENTS */}
        <TabsContent value="events" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hub Event Delivery</CardTitle>
              <CardDescription>Live from the Hub event-delivery API. No card data or secrets are displayed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {events?.loading ? (
                <div className="py-8 text-center text-slate-400">Loading from Hub...</div>
              ) : events ? (
                <>
                  <div>
                    <p className="font-medium text-sm mb-2 flex items-center gap-2">Delivery Stats <StatusBadge status={events.stats?.status || 'UNKNOWN'} /></p>
                    {events.stats?.status === 'ONLINE'
                      ? <pre className="text-xs bg-slate-50 rounded-lg p-4 overflow-x-auto">{JSON.stringify(events.stats.data, null, 2)}</pre>
                      : <p className="text-sm text-slate-500">{events.stats?.detail}</p>}
                  </div>
                  <div>
                    <p className="font-medium text-sm mb-2 flex items-center gap-2">Undelivered Events <StatusBadge status={events.undelivered?.status || 'UNKNOWN'} /></p>
                    {events.undelivered?.status === 'ONLINE'
                      ? <pre className="text-xs bg-slate-50 rounded-lg p-4 overflow-x-auto max-h-[360px]">{JSON.stringify(events.undelivered.data, null, 2)}</pre>
                      : <p className="text-sm text-slate-500">{events.undelivered?.detail}</p>}
                  </div>
                </>
              ) : (
                <div className="py-8 text-center text-slate-400">Open this tab to load Hub event data</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Link dialog */}
      <Dialog open={!!linkDialog} onOpenChange={(open) => !open && setLinkDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{linkDialog?.type === 'merchant' ? 'Link Merchant to Payment Hub' : 'Link Terminal to Payment Hub'}</DialogTitle>
            <DialogDescription>
              {linkDialog?.type === 'merchant'
                ? 'Enter the Hub identifier (Hub user UUID, hub_mid, or numeric Hub id). It is verified against the live Hub before saving.'
                : 'Enter the Hub terminal id (and optionally the device serial).'} Environment: {status?.environment || 'unknown'}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>{linkDialog?.type === 'merchant' ? 'Hub Merchant Identifier' : 'Hub Terminal ID'}</Label>
              <Input value={linkValue} onChange={(e) => setLinkValue(e.target.value)} className="font-mono" data-testid="hub-link-input" />
            </div>
            {linkDialog?.type === 'terminal' && (
              <div>
                <Label>Terminal Serial (optional)</Label>
                <Input value={linkSerial} onChange={(e) => setLinkSerial(e.target.value)} className="font-mono" />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLinkDialog(null)}>Cancel</Button>
            <Button onClick={saveLink} disabled={!linkValue.trim()} data-testid="hub-link-save">Verify & Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
