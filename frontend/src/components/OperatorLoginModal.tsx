import React, { useState } from 'react';
import { Lock, X, AlertCircle, KeyRound, Sparkles, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import type { OperatorSession } from '../types';

interface OperatorLoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (session: OperatorSession) => void;
}

export const OperatorLoginModal: React.FC<OperatorLoginModalProps> = ({
  isOpen,
  onClose,
  onLoginSuccess
}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [autofillSuccess, setAutofillSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAutofillDemo = async () => {
    setIsAutofilling(true);
    setErrorMessage(null);
    try {
      const creds = await api.getDemoCredentials();
      setUsername(creds.username);
      setPassword(creds.password);
      setAutofillSuccess(true);
      setTimeout(() => setAutofillSuccess(false), 4000);
    } catch (err: any) {
      setErrorMessage(
        err.message || 'Failed to fetch demo credentials from backend environment.'
      );
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const session = await api.loginOperator(username.trim(), password);
      onLoginSuccess(session);
      onClose();
    } catch (err: any) {
      setErrorMessage(
        err.message || 'Invalid operator credentials. Access denied.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Modal Header */}
        <div className="bg-slate-900 text-white p-5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-md">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base leading-tight">Hospital Operator Gate</h3>
              <p className="text-xs text-slate-300">Staff access for Operations Dashboard</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg transition"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-900">
            <div className="flex items-center space-x-1.5 font-semibold mb-1">
              <Sparkles className="w-3.5 h-3.5 text-teal-600 shrink-0" />
              <span>Hackathon Prototype Demo Flow</span>
            </div>
            <p className="text-slate-600 leading-relaxed text-[11px]">
              Protected with server-side HMAC session tokens. Credentials are validated by the backend from environment variables (<code className="font-mono text-teal-800 font-semibold">OPERATOR_USERNAME</code> / <code className="font-mono text-teal-800 font-semibold">OPERATOR_PASSWORD</code>).
            </p>
          </div>

          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {autofillSuccess && (
            <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Demo credentials loaded from backend environment!</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Operator Username
              </label>
              <input
                id="operator-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. operator@aarogya.org"
                className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent placeholder-slate-400"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Operator Password
              </label>
              <input
                id="operator-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>

            {/* Quick Demo Autofill Button */}
            <div className="pt-1">
              <button
                type="button"
                id="btn-autofill-demo"
                onClick={handleAutofillDemo}
                disabled={isAutofilling || isLoading}
                className="w-full py-2 px-3 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-xl transition flex items-center justify-center space-x-2 shadow-2xs"
              >
                <KeyRound className="w-3.5 h-3.5 text-teal-600" />
                <span>
                  {isAutofilling ? 'Fetching from backend...' : 'Autofill Demo Credentials from Backend'}
                </span>
              </button>
            </div>

            {/* Action Buttons */}
            <div className="pt-2 flex space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 px-4 text-xs font-semibold text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-xl transition"
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                id="btn-submit-operator-login"
                disabled={isLoading}
                className="flex-1 py-2.5 px-4 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition shadow-md shadow-teal-600/20 disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <span>Authenticate Operator</span>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Security: Server-Side Authorization</span>
          <span>AarogyaConnect MVP</span>
        </div>
      </div>
    </div>
  );
};

