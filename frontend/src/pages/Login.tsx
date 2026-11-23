import React, { useState } from 'react';
import { Lock, User, Phone, ShieldCheck, AlertCircle, Building2, KeyRound, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface LoginProps {
  onLoginSuccess: (user: any, token: string) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const { toggleTheme, isDark } = useTheme();
  const [loginMode, setLoginMode] = useState<'PASSWORD' | 'OTP'>('PASSWORD');

  // Username/Password state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // OTP state
  const [mobile, setMobile] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [otp, setOtp] = useState('');
  const [channel, setChannel] = useState<'WHATSAPP' | 'SMS_FALLBACK' | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Handle Admin / Staff Password Login
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/v1/auth/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const text = await res.text();
      let data: any = null;
      try {
        data = JSON.parse(text);
      } catch {
        // Not JSON
      }

      if (!res.ok) {
        throw new Error(data?.detail || text || `Server error (${res.status})`);
      }
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      onLoginSuccess(data.user, data.access_token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Quick helper to fill admin credentials
  const fillAdminCredentials = () => {
    setUsername('admin');
    setPassword('Admin@123');
    setError('');
  };

  // Handle WhatsApp OTP Flow
  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/v1/auth/request-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mobile }),
      });
      const text = await res.text();
      let data: any = null;
      try { data = JSON.parse(text); } catch {}
      if (!res.ok) throw new Error(data?.detail || text || 'Failed to request OTP');
      setSessionId(data.session_id);
      setChannel(data.channel);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/v1/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, otp }),
      });
      const text = await res.text();
      let data: any = null;
      try { data = JSON.parse(text); } catch {}
      if (!res.ok) throw new Error(data?.detail || text || 'Invalid OTP');
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      onLoginSuccess(data.user, data.access_token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`min-h-screen flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 transition-colors duration-300 relative ${
        isDark ? 'bg-slate-950 text-white' : 'bg-slate-50 text-slate-900'
      }`}
    >
      {/* Top Floating Theme Switcher */}
      <div className="absolute top-4 right-4">
        <button
          onClick={toggleTheme}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all shadow-sm ${
            isDark
              ? 'bg-slate-900 border-slate-800 text-amber-300 hover:bg-slate-800'
              : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-100 shadow-slate-200/50'
          }`}
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {isDark ? (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span>Light Mode</span>
            </>
          ) : (
            <>
              <Moon className="w-4 h-4 text-slate-700" />
              <span>Dark Mode</span>
            </>
          )}
        </button>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex p-3 bg-gradient-to-tr from-emerald-600 to-green-500 rounded-2xl shadow-xl shadow-emerald-900/30 mb-3">
          <Building2 className="w-8 h-8 text-white" />
        </div>
        <h1
          className={`text-2xl font-black tracking-tight sm:text-3xl ${
            isDark ? 'text-white' : 'text-slate-900'
          }`}
        >
          Omshiv Buildvision CRM
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Propira Enterprise Real Estate Engine & Admin Portal
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div
          className={`py-8 px-6 sm:px-10 rounded-3xl border shadow-2xl transition-all ${
            isDark
              ? 'bg-slate-900/90 border-slate-800 backdrop-blur-md shadow-black/40'
              : 'bg-white border-slate-200/80 shadow-slate-200/60'
          }`}
        >
          {/* Mode Tabs */}
          <div
            className={`flex rounded-xl p-1 mb-6 border ${
              isDark
                ? 'bg-slate-950 border-slate-800'
                : 'bg-slate-100 border-slate-200'
            }`}
          >
            <button
              type="button"
              onClick={() => {
                setLoginMode('PASSWORD');
                setError('');
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                loginMode === 'PASSWORD'
                  ? 'bg-gradient-to-r from-emerald-600 to-green-600 text-white shadow-sm'
                  : isDark
                  ? 'text-slate-400 hover:text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Admin / Staff Login</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMode('OTP');
                setError('');
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                loginMode === 'OTP'
                  ? 'bg-gradient-to-r from-emerald-600 to-green-600 text-white shadow-sm'
                  : isDark
                  ? 'text-slate-400 hover:text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Phone className="w-3.5 h-3.5" />
              <span>WhatsApp OTP</span>
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-rose-50 dark:bg-rose-950/80 border border-rose-200 dark:border-rose-700/60 rounded-xl p-3 flex items-center text-rose-800 dark:text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0 text-rose-600 dark:text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* PASSWORD MODE */}
          {loginMode === 'PASSWORD' && (
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Username / Email / Employee ID
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. admin or EMP-0001"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-emerald-900/30 transition-all hover:-translate-y-0.5 active:translate-y-0"
                >
                  {loading ? 'Authenticating...' : 'Sign In to Admin Console'}
                </button>
              </div>

              {/* Demo auto-fill helper */}
              <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 text-center">
                <button
                  type="button"
                  onClick={fillAdminCredentials}
                  className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline font-mono font-bold"
                >
                  ⚡ Auto-fill Super Admin (admin / Admin@123)
                </button>
              </div>
            </form>
          )}

          {/* OTP MODE */}
          {loginMode === 'OTP' && (
            <div className="space-y-4">
              {!sessionId ? (
                <form onSubmit={handleRequestOtp} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Registered 10-Digit Mobile Number
                    </label>
                    <div className="relative">
                      <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="tel"
                        required
                        value={mobile}
                        onChange={(e) => setMobile(e.target.value)}
                        placeholder="9829012345"
                        className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 px-4 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-emerald-900/30 transition-all"
                  >
                    {loading ? 'Sending OTP...' : 'Send WhatsApp OTP'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <div className="p-3 bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 rounded-xl text-xs text-emerald-800 dark:text-emerald-300">
                    OTP sent via {channel === 'WHATSAPP' ? 'WhatsApp' : 'SMS Fallback'} to +91 {mobile}
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Enter 6-Digit Verification Code
                    </label>
                    <input
                      type="text"
                      required
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                      placeholder="123456"
                      maxLength={6}
                      className="w-full text-center tracking-widest font-mono text-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl py-2 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 px-4 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-emerald-900/30 transition-all"
                  >
                    {loading ? 'Verifying...' : 'Verify & Enter Console'}
                  </button>
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => setSessionId('')}
                      className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-white underline"
                    >
                      Use a different number
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          <div className="mt-6 flex items-center justify-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Role-Based Permissions & TLS 256-Bit Encryption</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
