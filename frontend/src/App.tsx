import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import MyWork from './pages/MyWork';
import LeadDetail from './pages/LeadDetail';
import PropertyVerification from './pages/PropertyVerification';
import SettingsEditor from './pages/SettingsEditor';
import { Building2, CheckSquare, Settings, LogOut, UserCheck } from 'lucide-react';

export const App: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [user, setUser] = useState<any>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeTab, setActiveTab] = useState<'MY_WORK' | 'VERIFICATION' | 'SETTINGS' | 'LEAD_DETAIL'>('MY_WORK');
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  const handleLoginSuccess = (userData: any, userToken: string) => {
    setUser(userData);
    setToken(userToken);
    setActiveTab('MY_WORK');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-600 rounded-lg">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-extrabold tracking-tight">Omshiv Buildvision CRM</h1>
              <p className="text-[10px] text-slate-400 font-mono">Propira Real Estate Engine</p>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="flex items-center gap-1 sm:gap-2 text-xs font-semibold">
            <button
              onClick={() => {
                setActiveTab('MY_WORK');
                setSelectedLeadId(null);
              }}
              className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-colors ${
                activeTab === 'MY_WORK' || activeTab === 'LEAD_DETAIL'
                  ? 'bg-slate-800 text-green-400'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <CheckSquare className="w-4 h-4" /> My Work
            </button>

            <button
              onClick={() => setActiveTab('VERIFICATION')}
              className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-colors ${
                activeTab === 'VERIFICATION' ? 'bg-slate-800 text-green-400' : 'text-slate-300 hover:text-white'
              }`}
            >
              <UserCheck className="w-4 h-4" /> Verification Queue
            </button>

            <button
              onClick={() => setActiveTab('SETTINGS')}
              className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-colors ${
                activeTab === 'SETTINGS' ? 'bg-slate-800 text-green-400' : 'text-slate-300 hover:text-white'
              }`}
            >
              <Settings className="w-4 h-4" /> Settings & Audit
            </button>
          </nav>

          {/* User Badge & Logout */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <div className="text-xs font-bold text-white">{user?.name || 'Staff Member'}</div>
              <div className="text-[10px] text-slate-400 font-mono">{user?.employee_id || 'EMP-XXXX'}</div>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
        {activeTab === 'SETTINGS' && <SettingsEditor />}
      </main>
    </div>
  );
};
export default App;
