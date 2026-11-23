import React, { useState } from 'react';
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

const AppContent: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [user, setUser] = useState<any>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const [activeTab, setActiveTab] = useState<AdminTab>('DASHBOARD');
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  const handleLoginSuccess = (userData: any, userToken: string) => {
    setUser(userData);
    setToken(userToken);
    setActiveTab('DASHBOARD');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setActiveTab('DASHBOARD');
    setSelectedLeadId(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <AdminLayout
      user={user}
      activeTab={activeTab}
      onSelectTab={(tab) => {
        setActiveTab(tab);
        if (tab !== 'MY_WORK' && tab !== 'LEAD_DETAIL') {
          setSelectedLeadId(null);
        }
      }}
      onLogout={handleLogout}
    >
      {activeTab === 'DASHBOARD' && (
        <AdminDashboard
          onNavigate={(tab) => {
            setActiveTab(tab);
            if (tab !== 'MY_WORK') setSelectedLeadId(null);
          }}
        />
      )}

      {activeTab === 'STAFF' && <StaffManager />}

      {activeTab === 'MY_WORK' && (
        <MyWork
          onSelectLead={(id) => {
            setSelectedLeadId(id);
            setActiveTab('LEAD_DETAIL');
          }}
        />
      )}

      {activeTab === 'LEAD_DETAIL' && selectedLeadId && (
        <LeadDetail
          leadId={selectedLeadId}
          onBack={() => {
            setSelectedLeadId(null);
            setActiveTab('MY_WORK');
          }}
        />
      )}

      {activeTab === 'VERIFICATION' && <PropertyVerification />}

      {activeTab === 'RECYCLE_BIN' && <RecycleBinView />}

      {activeTab === 'DYNAMIC_MASTERS' && <DynamicMastersEditor />}

      {activeTab === 'SETTINGS' && <SettingsEditor />}
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
