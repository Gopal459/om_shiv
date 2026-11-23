import React, { useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useParams, useLocation } from 'react-router-dom';
import Login from './pages/Login';
import AdminLayout, { AdminTab } from './layouts/AdminLayout';
import AdminDashboard from './pages/AdminDashboard';
import StaffManager from './pages/StaffManager';
import MyWork from './pages/MyWork';
import LeadDetail from './pages/LeadDetail';
import PropertyVerification from './pages/PropertyVerification';
import RecycleBinView from './pages/RecycleBinView';
import DynamicMastersEditor from './pages/DynamicMastersEditor';
import SettingsEditor from './pages/SettingsEditor';
import { ThemeProvider } from './context/ThemeContext';

const LeadDetailPage: React.FC = () => {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  if (!leadId) {
    return <Navigate to="/leads" replace />;
  }
  return <LeadDetail leadId={leadId} onBack={() => navigate('/leads')} />;
};

const AppContent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'));
  const [user, setUser] = useState<any>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLoginSuccess = (userData: any, userToken: string) => {
    setUser(userData);
    setToken(userToken);
    const origin = (location.state as any)?.from?.pathname || '/dashboard';
    navigate(origin, { replace: true });
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    navigate('/login', { replace: true });
  };

  const handleDashboardNavigate = (tab: AdminTab) => {
    const pathToTab: Record<AdminTab, string> = {
      DASHBOARD: '/dashboard',
      STAFF: '/staff',
      MY_WORK: '/leads',
      LEAD_DETAIL: '/leads',
      VERIFICATION: '/verifications',
      RECYCLE_BIN: '/recycle-bin',
      DYNAMIC_MASTERS: '/masters',
      SETTINGS: '/settings',
    };
    navigate(pathToTab[tab] || '/dashboard');
  };

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLoginSuccess={handleLoginSuccess} />} />
        <Route path="*" element={<Navigate to="/login" state={{ from: location }} replace />} />
      </Routes>
    );
  }

  return (
    <AdminLayout user={user} onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/dashboard"
          element={<AdminDashboard onNavigate={handleDashboardNavigate} />}
        />
        <Route path="/staff" element={<StaffManager />} />
        <Route
          path="/leads"
          element={<MyWork onSelectLead={(id) => navigate(`/leads/${id}`)} />}
        />
        <Route path="/leads/:leadId" element={<LeadDetailPage />} />
        <Route path="/verifications" element={<PropertyVerification />} />
        <Route path="/recycle-bin" element={<RecycleBinView />} />
        <Route path="/masters" element={<DynamicMastersEditor />} />
        <Route path="/settings" element={<SettingsEditor />} />
        <Route path="/login" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AdminLayout>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
