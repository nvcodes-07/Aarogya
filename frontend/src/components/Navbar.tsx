import React from 'react';
import { PhoneCall, ShieldAlert, HeartPulse, Sparkles, Database, Lock, LogOut, ShieldCheck } from 'lucide-react';
import type { OperatorSession } from '../types';

interface NavbarProps {
  activeTab: 'patient' | 'dashboard';
  setActiveTab: (tab: 'patient' | 'dashboard') => void;
  backendHealth: {
    connected: boolean;
    hospital: string;
    model: string;
    ai_enabled: boolean;
  };
  operatorSession: OperatorSession | null;
  onOpenOperatorLogin: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  backendHealth,
  operatorSession,
  onOpenOperatorLogin,
  onLogout
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      {/* Verified Emergency Notice Banner */}
      <div className="bg-rose-700 text-white text-xs px-4 py-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 font-medium">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-white shrink-0 animate-pulse" />
          <span>
            <strong>REAL EMERGENCY ADVISORY:</strong> For medical emergencies, call National Emergency Services (<strong>108 / 112</strong>) immediately. All hospital phone numbers on this site are simulated demo contacts. This prototype cannot dispatch real ambulances.
          </span>
        </div>
        <div className="flex items-center space-x-2 text-rose-200 text-[11px] shrink-0 font-mono">
          <span className="px-1.5 py-0.5 rounded bg-rose-800/80 border border-rose-600">Simulated Demo</span>
          <span>Indore, MP</span>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Hospital Brand Identity */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-md shadow-teal-600/20">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-900 text-lg tracking-tight">AarogyaConnect AI</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider bg-teal-50 text-teal-700 px-2 py-0.5 rounded border border-teal-200">
                  Hospital Operations
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium leading-none">
                Aarogya Multispeciality Hospital <span className="text-slate-300 hidden sm:inline">•</span> <span className="text-teal-700 font-normal italic hidden sm:inline">"From patient conversations to completed hospital workflows."</span>
              </p>
            </div>
          </div>

          {/* Navigation Controls */}
          {operatorSession ? (
            /* Operator Logged In: Can switch between Patient Assistant and Operations Dashboard */
            <nav className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
              <button
                id="nav-patient-assistant"
                onClick={() => setActiveTab('patient')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === 'patient'
                    ? 'bg-white text-teal-700 shadow-xs border border-slate-200/80'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="w-4 h-4 text-teal-600" />
                <span>Patient Assistant</span>
              </button>
              <button
                id="nav-operations-dashboard"
                onClick={() => setActiveTab('dashboard')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === 'dashboard'
                    ? 'bg-white text-teal-700 shadow-xs border border-slate-200/80'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Database className="w-4 h-4 text-cyan-600" />
                <span>Operations Dashboard</span>
              </button>
            </nav>
          ) : (
            /* Patient Mode: Only Patient Assistant is visible. Hospital-wide dashboard is hidden. */
            <div className="flex items-center space-x-2 text-xs font-semibold text-teal-800 bg-teal-50/80 px-3.5 py-1.5 rounded-lg border border-teal-200">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <span>Patient Portal</span>
            </div>
          )}

          {/* Right Action Area */}
          <div className="flex items-center space-x-3">
            {/* System Mode Indicator */}
            <div
              className={`hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs ${
                backendHealth.connected
                  ? backendHealth.ai_enabled
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
              title={
                backendHealth.ai_enabled
                  ? 'Connected to configured LLM provider'
                  : 'Operating in Deterministic Fallback Demo mode (executing real backend operations & database writes)'
              }
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  backendHealth.connected
                    ? backendHealth.ai_enabled
                      ? 'bg-emerald-500 animate-pulse'
                      : 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
              />
              <span className="font-semibold">
                {backendHealth.connected
                  ? backendHealth.ai_enabled
                    ? `AI Mode (${backendHealth.model})`
                    : 'Deterministic Fallback Demo'
                  : 'Backend Disconnected'}
              </span>
            </div>

            {/* Operator Auth Gate Entry / Session Status */}
            {operatorSession ? (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-1.5 text-xs bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  <span className="font-medium max-w-[130px] truncate" title={operatorSession.username}>
                    {operatorSession.username}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 bg-teal-100 text-teal-800 rounded font-semibold">
                    Operator
                  </span>
                </div>
                <button
                  id="btn-operator-logout"
                  onClick={onLogout}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold transition"
                  title="Logout operator session"
                >
                  <LogOut className="w-3.5 h-3.5 text-rose-600" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <button
                id="btn-open-operator-login"
                onClick={onOpenOperatorLogin}
                className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 hover:border-teal-300 text-slate-700 hover:text-teal-800 text-xs font-semibold border border-slate-300 transition shadow-2xs"
                title="Hospital Staff & Operator Dashboard Login"
              >
                <Lock className="w-3.5 h-3.5 text-slate-500" />
                <span>Operator Login</span>
              </button>
            )}

            {/* Fictional Demo Contact */}
            <div className="hidden xl:flex items-center space-x-1.5 text-xs text-slate-500 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50/50">
              <PhoneCall className="w-3.5 h-3.5 text-slate-400" />
              <span>Demo Desk: <strong className="font-mono">0731-4999000</strong></span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
