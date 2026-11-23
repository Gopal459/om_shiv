import React, { useState } from 'react';
import { Phone, ShieldCheck, MessageSquare, AlertCircle } from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: any, token: string) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [mobile, setMobile] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [otp, setOtp] = useState('');
  const [channel, setChannel] = useState<'WHATSAPP' | 'SMS_FALLBACK' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);

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
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to request OTP');
      }
      setSessionId(data.session_id);
      setChannel(data.channel);
      setResendCountdown(30);
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
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Invalid OTP');
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

  const handleManualSmsFallback = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await fetch('/v1/auth/fallback-sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setChannel('SMS_FALLBACK');
      setResendCountdown(60);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Omshiv Buildvision CRM
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Propira Property Engine & Dual-Channel Login
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-xl rounded-xl sm:px-10 border border-slate-200">
          {error && (
            <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-3 flex items-center text-red-700 text-sm">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!sessionId ? (
            <form onSubmit={handleRequestOtp} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  Registered Mobile Number
                </label>
                <div className="mt-2 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Phone className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="tel"
                    required
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    placeholder="Enter 10-digit mobile"
                    className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-green-500 focus:border-green-500 text-sm"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || mobile.length < 10}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
              >
                {loading ? 'Sending OTP...' : 'Send WhatsApp OTP'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-6">
              <div>
                <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
                  <span>Code sent via:</span>
                  <span className="font-semibold text-green-700 flex items-center">
                    <MessageSquare className="w-3.5 h-3.5 mr-1" />
                    {channel === 'SMS_FALLBACK' ? 'SMS Fallback' : 'WhatsApp'}
                  </span>
                </div>
                <label className="block text-sm font-medium text-slate-700">
                  Enter 6-Digit OTP
                </label>
                <input
                  type="text"
                  maxLength={6}
                  required
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="123456"
                  className="mt-2 block w-full px-3 py-2 text-center tracking-widest text-lg font-bold border border-slate-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
              >
                <ShieldCheck className="w-5 h-5 mr-2" />
                {loading ? 'Verifying...' : 'Verify & Enter CRM'}
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={handleManualSmsFallback}
                  disabled={loading}
                  className="text-xs text-slate-500 hover:text-green-700 underline"
                >
                  Didn't receive on WhatsApp? Resend via SMS
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
export default Login;
