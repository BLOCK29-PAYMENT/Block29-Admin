import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import MerchantsPage from "./pages/MerchantsPage";
import VarSheetPage from "./pages/VarSheetPage";
import TerminalsPage from "./pages/TerminalsPage";
import TransactionsPage from "./pages/TransactionsPage";
import Block29Page from "./pages/Block29Page";
import AffiliatesPage from "./pages/AffiliatesPage";
import UsersPage from "./pages/UsersPage";
import SettingsPage from "./pages/SettingsPage";
import VirtualTerminalPage from "./pages/VirtualTerminalPage";
import ReportsPage from "./pages/ReportsPage";
import SystemLogsPage from "./pages/SystemLogsPage";
import { AuthProvider, useAuth } from "./context/AuthContext";

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/merchants" element={<MerchantsPage />} />
                    <Route path="/varsheet" element={<VarSheetPage />} />
                    <Route path="/terminals" element={<TerminalsPage />} />
                    <Route path="/transactions" element={<TransactionsPage />} />
                    <Route path="/block29" element={<Block29Page />} />
                    <Route path="/affiliates" element={<AffiliatesPage />} />
                    <Route path="/users" element={<UsersPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
