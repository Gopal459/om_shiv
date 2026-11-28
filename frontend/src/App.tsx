import React, { useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useParams, useLocation, useSearchParams } from 'react-router-dom';
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
import ModuleHub from './pages/ModuleHub';
import PropertyHub from './pages/PropertyHub';
import PropertyForm from './pages/PropertyForm';
import BlogManager from './pages/BlogManager';
import AIAgentHub from './pages/AIAgentHub';
import AIApprovalsQueue from './pages/AIApprovalsQueue';
import FranchiseHub from './pages/FranchiseHub';
import WebsiteFormsHub from './pages/WebsiteFormsHub';
import { ThemeProvider } from './context/ThemeContext';

const LeadDetailPage: React.FC = () => {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  if (!leadId) {
    return <Navigate to="/leads" replace />;
  }
  return <LeadDetail leadId={leadId} onBack={() => navigate('/leads')} />;
};

const PropertyCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fromLead = searchParams.get('fromLead');
  const targetBack = fromLead ? `/leads/${encodeURIComponent(fromLead)}` : '/properties';
  return (
    <PropertyForm
      fromLeadId={fromLead}
      onBack={() => navigate(targetBack)}
      onSuccess={() => navigate(targetBack)}
    />
  );
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
    const pathToTab: Record<string, string> = {
      DASHBOARD: '/dashboard',
      STAFF: '/staff',
      MY_WORK: '/leads',
      LEADS: '/leads',
      LEAD_DETAIL: '/leads',
      VERIFICATION: '/verifications',
      RECYCLE_BIN: '/recycle-bin',
      DYNAMIC_MASTERS: '/masters',
      SETTINGS: '/settings',
      WEBSITE_FORMS: '/website-forms',
      OPPORTUNITIES: '/opportunities',
      PROPERTY: '/properties',
      HOMEPAGE: '/homepage',
      BLOG: '/blogs',
      PROPIRA_USERS: '/users',
      PAGES: '/pages',
      FRANCHISE: '/franchise',
      AI_AGENTS: '/ai-agents',
      AI_APPROVALS: '/ai-approvals',
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
        <Route path="/ai-agents" element={<AIAgentHub />} />
        <Route path="/ai-approvals" element={<AIApprovalsQueue />} />

        {/* 11 Enterprise Module Hub Routes */}
        <Route path="/website-forms" element={<WebsiteFormsHub />} />
        <Route
          path="/opportunities"
          element={
            <ModuleHub
              title="Opportunities & Pipeline Conversion"
              subtitle="Stage progression tracking, scheduled site visits, negotiations, and closed won property transactions."
              badge="Deal Conversion"
              stats={[
                { label: 'Active Opportunities', value: 52, change: 'Stage in discussion' },
                { label: 'Site Visits Scheduled', value: 19, change: 'Today & tomorrow' },
                { label: 'In Negotiation', value: 8, change: 'High closing prob.' },
                { label: 'Closed Won (This Month)', value: 14, change: 'Verified deals' },
              ]}
              shortcuts={[
                { label: 'Prioritized Lead & Opportunity Queue', desc: 'Review leads organized by temperature and follow-up SLA', path: '/leads' },
                { label: 'Property Inventory Cross-Match', desc: 'Match qualified buyer requirements with active properties', path: '/properties' },
              ]}
            />
          }
        />
        <Route path="/properties" element={<PropertyHub />} />
        <Route path="/properties/create" element={<PropertyCreatePage />} />
        <Route
          path="/homepage"
          element={
            <ModuleHub
              title="Homepage CMS & Featured Displays"
              subtitle="Manage promotional hero banners, curated project showcases, and spotlight property listings."
              badge="Content Management"
              stats={[
                { label: 'Active Hero Banners', value: 3, change: 'Rotating slides' },
                { label: 'Featured Projects', value: 6, change: 'Jaipur Prime' },
                { label: 'Promotional Highlights', value: 4, change: 'Exclusive listings' },
                { label: 'Click-Through Rate', value: '4.8%', change: '+0.6% vs avg' },
              ]}
              shortcuts={[
                { label: 'Configure System Settings & SLAs', desc: 'Update system-wide parameters and quiet hours', path: '/settings' },
                { label: 'Manage Dynamic Property Masters', desc: 'Add new unit types, amenities, and floor schemas', path: '/masters' },
              ]}
            />
          }
        />
        <Route path="/blogs" element={<BlogManager />} />
        <Route
          path="/users"
          element={
            <ModuleHub
              title="Propira Registered Users Directory"
              subtitle="Manage verified buyers, tenants, property owners, and seller accounts."
              badge="Customer Hub"
              stats={[
                { label: 'Registered Buyers', value: 520, change: 'Active OTP accounts' },
                { label: 'Verified Owners', value: 86, change: 'Direct listings' },
                { label: 'WhatsApp Sessions', value: 412, change: 'Dual-channel OTP' },
                { label: 'Active Inquiries', value: 142, change: 'Pipeline engaged' },
              ]}
              shortcuts={[
                { label: 'Staff & Internal Panel Users', desc: 'Manage CRM employees, roles, and granular permissions', path: '/staff' },
                { label: 'Sales & Verification Queues', desc: 'Handle owner verification requests and buyer matches', path: '/verifications' },
              ]}
            />
          }
        />
        <Route
          path="/pages"
          element={
            <ModuleHub
              title="CMS Static Pages & Policy Manager"
              subtitle="Manage About Us, Terms of Service, Privacy Policy, and Service Locations."
              badge="Static Content"
              stats={[
                { label: 'Published Pages', value: 7, change: 'Live on portal' },
                { label: 'Serviceable Pincodes', value: 34, change: 'Jaipur & outskirts' },
                { label: 'Legal Compliance', value: '100%', change: 'RERA Aligned' },
                { label: 'Last Revision', value: 'Nov 2026', change: 'Current version' },
              ]}
              shortcuts={[
                { label: 'Manage Pincode Serviceability', desc: 'Add or edit active pincode master entries', path: '/masters' },
                { label: 'Security & Audit Ledger', desc: 'Verify system parameters and changes', path: '/settings' },
              ]}
            />
          }
        />
        <Route path="/franchise" element={<FranchiseHub />} />

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
