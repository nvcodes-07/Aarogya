import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { FormattedMessage } from './components/FormattedMessage';
import { OperatorLoginModal } from './components/OperatorLoginModal';
import {
  AvailableSlotsCard,
  ProposedBookingCard,
  ConfirmedAppointmentCard,
  SimulatedAmbulanceCard,
  SupportTicketCard,
  EscalationCard
} from './components/ChatCards';
import { api } from './services/api';
import {
  Calendar,
  Truck,
  Ticket,
  UserCheck,
  Send,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  HelpCircle,
  Activity,
  AlertCircle,
  Inbox,
  Lock,
  ShieldCheck,
  ArrowLeft,
  Search,
  Check,
  Clock,
  Building
} from 'lucide-react';
import type {
  ChatMessage,
  PendingBooking,
  Appointment,
  AmbulanceRequest,
  SupportTicket,
  HumanEscalation,
  AgentActionLog,
  DashboardStats,
  OperatorSession
} from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'patient' | 'dashboard'>('patient');
  const [operatorSession, setOperatorSession] = useState<OperatorSession | null>(null);
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);

  const [backendHealth, setBackendHealth] = useState({
    connected: false,
    hospital: 'Aarogya Multispeciality Hospital',
    model: 'Deterministic Fallback Demo',
    ai_enabled: false
  });

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: `Hello! I am **AarogyaConnect AI**, the digital customer operations assistant for **Aarogya Multispeciality Hospital**.\n\n*"From patient conversations to completed hospital workflows."*\n\nI can execute actual hospital operations for you:\n• **Book Doctor Appointments** (Cardiology, Orthopedics, Dermatology, General Medicine)\n• **Register Ambulance Assistance** (Simulated prototype demo request)\n• **Answer Hospital Policies & FAQs** (OPD timings, visiting hours, cashless insurance, test prep)\n• **File Support Grievances & Callbacks** (Billing delays, human escalation)\n\nHow can I help you today?`,
      suggested_prompts: [
        "Book a doctor's appointment.",
        "Find a cardiologist.",
        "Request an ambulance.",
        "Ask about hospital OPD timings.",
        "Register a billing complaint.",
        "Speak to a human representative."
      ]
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [pendingBooking, setPendingBooking] = useState<PendingBooking | null>(null);
  const [sessionId] = useState(() => 'sess_' + Math.random().toString(36).substring(2, 9));
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Dashboard State
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [ambulanceRequests, setAmbulanceRequests] = useState<AmbulanceRequest[]>([]);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [escalations, setEscalations] = useState<HumanEscalation[]>([]);
  const [actionLogs, setActionLogs] = useState<AgentActionLog[]>([]);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Poll Health
  const fetchHealth = async () => {
    try {
      const data = await api.checkHealth();
      setBackendHealth({
        connected: true,
        hospital: data.hospital,
        model: data.model,
        ai_enabled: data.ai_enabled
      });
    } catch {
      setBackendHealth(prev => ({ ...prev, connected: false }));
    }
  };

  // Check stored operator token on initial mount
  useEffect(() => {
    fetchHealth();

    // Clean up any legacy localStorage token
    if (typeof window !== 'undefined' && localStorage.getItem('aarogya_operator_token')) {
      localStorage.removeItem('aarogya_operator_token');
    }

    const token = api.getStoredOperatorToken();
    if (token) {
      api.getOperatorProfile()
        .then((profile) => {
          setOperatorSession({
            access_token: token,
            token_type: 'bearer',
            expires_at: 0,
            username: profile.username,
            role: profile.role,
            hospital: profile.hospital
          });
          if (window.location.hash === '#dashboard') {
            setActiveTab('dashboard');
          }
        })
        .catch(() => {
          api.setOperatorToken(null);
          setOperatorSession(null);
          setActiveTab('patient');
          window.location.hash = '#patient';
        });
    } else {
      setActiveTab('patient');
      if (window.location.hash === '#dashboard') {
        window.location.hash = '#patient';
      }
    }

    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash === '#dashboard') {
        const currentToken = api.getStoredOperatorToken();
        if (currentToken) {
          setActiveTab('dashboard');
        } else {
          setActiveTab('patient');
          window.location.hash = '#patient';
          setShowLoginModal(true);
        }
      } else {
        setActiveTab('patient');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    const interval = setInterval(fetchHealth, 15000);
    return () => {
      clearInterval(interval);
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  // Fetch Dashboard Data (Server-Side Authorized Operators Only)
  const loadDashboardData = async () => {
    if (!operatorSession) return;
    setIsLoadingDashboard(true);
    setDashboardError(null);
    try {
      const [s, apts, ambs, tkts, escs, acts] = await Promise.all([
        api.getDashboardStats(),
        api.getAppointments(30),
        api.getAmbulanceRequests(30),
        api.getTickets(30),
        api.getEscalations(30),
        api.getActionLogs(30)
      ]);
      setStats(s);
      setAppointments(apts);
      setAmbulanceRequests(ambs);
      setTickets(tkts);
      setEscalations(escs);
      setActionLogs(acts);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      if (err.message?.includes('401') || err.message?.toLowerCase().includes('authorization')) {
        setOperatorSession(null);
        setDashboardError('Operator session expired or invalid. Please re-authenticate.');
      } else {
        setDashboardError(err.message || 'Failed to fetch dashboard records from backend.');
      }
    } finally {
      setIsLoadingDashboard(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'dashboard' && operatorSession) {
      loadDashboardData();
    }
  }, [activeTab, operatorSession]);

  // Operator Auth Handlers
  const handleOperatorLoginSuccess = (session: OperatorSession) => {
    setOperatorSession(session);
    setActiveTab('dashboard');
    window.location.hash = '#dashboard';
  };

  const handleOperatorLogout = async () => {
    await api.logoutOperator();
    setOperatorSession(null);
    setActiveTab('patient');
    window.location.hash = '#patient';
    setStats(null);
    setAppointments([]);
    setAmbulanceRequests([]);
    setTickets([]);
    setEscalations([]);
    setActionLogs([]);
    setDashboardError(null);
  };

  // Operator Status Update Handlers
  const handleUpdateTicketStatus = async (ticketId: number, newStatus: string) => {
    setUpdatingId(`tkt-${ticketId}`);
    try {
      const updated = await api.updateTicketStatus(ticketId, newStatus);
      setTickets(prev => prev.map(t => t.id === ticketId ? updated : t));
      loadDashboardData();
    } catch (err: any) {
      alert(`Could not update ticket status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleUpdateEscalationStatus = async (escalationId: number, newStatus: string) => {
    setUpdatingId(`esc-${escalationId}`);
    try {
      const updated = await api.updateEscalationStatus(escalationId, newStatus);
      setEscalations(prev => prev.map(e => e.id === escalationId ? updated : e));
      loadDashboardData();
    } catch (err: any) {
      alert(`Could not update escalation status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  // Helper to determine if a record is recent (created within 1 hour)
  const isRecentRecord = (dateStr: string) => {
    try {
      const recTime = new Date(dateStr).getTime();
      const diffMinutes = (Date.now() - recTime) / (1000 * 60);
      return diffMinutes >= 0 && diffMinutes < 60;
    } catch {
      return false;
    }
  };

  // Handle Send Message (Public Patient Portal)
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isSending) return;

    setInputMessage('');
    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsSending(true);

    try {
      const history = messages.slice(-6).map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await api.sendMessage({
        message: text,
        session_id: sessionId,
        history,
        pending_booking: pendingBooking
      });

      setPendingBooking(res.pending_booking || null);
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.reply,
        action_performed: res.action_performed,
        action_reference: res.action_reference,
        pending_booking: res.pending_booking || undefined,
        structured_data: res.structured_data,
        suggested_prompts: res.suggested_prompts
      };
      setMessages(prev => [...prev, assistantMsg]);

      if (res.action_performed && operatorSession) {
        loadDashboardData();
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: `⚠️ **Connection Error:** Could not reach hospital backend operations server (${err.message || 'Check if server is active on port 8000'}). Please try again.`
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 antialiased selection:bg-teal-100 selection:text-teal-900">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          window.location.hash = `#${tab}`;
        }}
        backendHealth={backendHealth}
        operatorSession={operatorSession}
        onOpenOperatorLogin={() => setShowLoginModal(true)}
        onLogout={handleOperatorLogout}
      />

      {/* Operator Login Modal */}
      <OperatorLoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onLoginSuccess={handleOperatorLoginSuccess}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'patient' ? (
          /* ============================================================ */
          /* PHASE 4: PATIENT ASSISTANT TAB (DEFAULT LANDING EXPERIENCE) */
          /* ============================================================ */
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
            {/* Left Quick Operations Sidebar */}
            <div className="lg:col-span-1 space-y-4">
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center space-x-2 text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                  <span>Suggested Prompts</span>
                </div>
                <div className="space-y-2">
                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Book a doctor's appointment.")}
                    className="w-full text-left p-3 rounded-xl bg-teal-50/80 hover:bg-teal-100 border border-teal-200 text-teal-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <Calendar className="w-4 h-4 text-teal-600 shrink-0" />
                    <span>Book a doctor's appointment</span>
                  </button>

                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Find a cardiologist.")}
                    className="w-full text-left p-3 rounded-xl bg-sky-50/80 hover:bg-sky-100 border border-sky-200 text-sky-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <Search className="w-4 h-4 text-sky-600 shrink-0" />
                    <span>Find a cardiologist</span>
                  </button>

                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Request an ambulance.")}
                    className="w-full text-left p-3 rounded-xl bg-rose-50/80 hover:bg-rose-100 border border-rose-200 text-rose-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <Truck className="w-4 h-4 text-rose-600 shrink-0" />
                    <span>Request an ambulance</span>
                  </button>

                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Ask about hospital OPD timings.")}
                    className="w-full text-left p-3 rounded-xl bg-indigo-50/80 hover:bg-indigo-100 border border-indigo-200 text-indigo-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <Clock className="w-4 h-4 text-indigo-600 shrink-0" />
                    <span>Ask about hospital OPD timings</span>
                  </button>

                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Register a billing complaint.")}
                    className="w-full text-left p-3 rounded-xl bg-amber-50/80 hover:bg-amber-100 border border-amber-200 text-amber-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <Ticket className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Register a billing complaint</span>
                  </button>

                  <button
                    disabled={isSending}
                    onClick={() => handleSendMessage("Speak to a human representative.")}
                    className="w-full text-left p-3 rounded-xl bg-purple-50/80 hover:bg-purple-100 border border-purple-200 text-purple-900 text-xs font-semibold flex items-center space-x-2.5 transition shadow-2xs disabled:opacity-50"
                  >
                    <UserCheck className="w-4 h-4 text-purple-600 shrink-0" />
                    <span>Speak to a human representative</span>
                  </button>
                </div>
              </div>

              {/* Verified Hospital Policy Note */}
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs text-xs text-slate-600 space-y-2.5">
                <div className="flex items-center space-x-2 text-teal-700 font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Real Hospital Operations</span>
                </div>
                <p className="leading-relaxed">
                  Every confirmed booking, grievance, or simulated ambulance record writes directly to the hospital's SQLite database.
                </p>
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Engine:</span>
                  <span className="font-semibold text-teal-800">
                    {backendHealth.ai_enabled ? 'LLM Tool Calling' : 'Deterministic Fallback'}
                  </span>
                </div>
              </div>

              {/* Operator Portal Banner (Separate from Patient Nav) */}
              <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white p-4 rounded-2xl shadow-xs text-xs space-y-2.5">
                <div className="flex items-center space-x-2 font-bold text-teal-300">
                  <Lock className="w-4 h-4" />
                  <span>Hospital Staff Gateway</span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Hospital operators can log in to view the live booking roster, simulated ambulance queue, and support tickets.
                </p>
                {operatorSession ? (
                  <button
                    onClick={() => {
                      setActiveTab('dashboard');
                      window.location.hash = '#dashboard';
                    }}
                    className="w-full py-2 px-3 bg-teal-600 hover:bg-teal-500 text-white font-semibold rounded-lg text-xs transition flex items-center justify-center space-x-1.5 shadow-sm"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Open Operations Dashboard</span>
                  </button>
                ) : (
                  <button
                    id="btn-sidebar-operator-login"
                    onClick={() => setShowLoginModal(true)}
                    className="w-full py-2 px-3 bg-slate-700 hover:bg-slate-600 text-teal-200 font-semibold rounded-lg text-xs transition flex items-center justify-center space-x-1.5 border border-slate-600"
                  >
                    <Lock className="w-3.5 h-3.5 text-teal-400" />
                    <span>Operator Sign In</span>
                  </button>
                )}
              </div>
            </div>

            {/* Main Chat Interface */}
            <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[740px]">
              {/* Chat Header */}
              <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/60 rounded-t-2xl">
                <div className="flex items-center space-x-3">
                  <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-bold text-slate-900 text-sm">AarogyaConnect AI Patient Assistant</h2>
                    <p className="text-[11px] text-slate-500">
                      Aarogya Multispeciality Hospital • "From patient conversations to completed hospital workflows."
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-mono">
                    Session: {sessionId}
                  </span>
                </div>
              </div>

              {/* Chat Messages Log */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed shadow-xs ${
                        m.role === 'user'
                          ? 'bg-teal-700 text-white rounded-br-xs'
                          : 'bg-slate-50 text-slate-900 rounded-bl-xs border border-slate-200/80'
                      }`}
                    >
                      {/* Clean Markdown Formatted Message */}
                      <FormattedMessage content={m.content} isUser={m.role === 'user'} />

                      {/* 1. Selectable Available Slots Card */}
                      {m.role === 'assistant' && m.structured_data?.type === 'slots_list' && (
                        <AvailableSlotsCard
                          data={m.structured_data}
                          onSelectSlot={(slotText) => handleSendMessage(slotText)}
                          disabled={isSending}
                        />
                      )}

                      {/* 2. Proposed Appointment Card (Confirmation Required) */}
                      {m.role === 'assistant' && m.pending_booking && (
                        <ProposedBookingCard
                          booking={m.pending_booking}
                          onConfirm={() => handleSendMessage('Yes, confirm it.')}
                          onCancel={() => handleSendMessage('No, cancel.')}
                          disabled={isSending}
                        />
                      )}

                      {/* 3. Confirmed Appointment Card (Created in SQLite) */}
                      {m.role === 'assistant' && (m.action_performed === 'appointment_booked' || m.structured_data?.type === 'appointment') && m.structured_data && (
                        <ConfirmedAppointmentCard data={m.structured_data} />
                      )}

                      {/* 4. Simulated Ambulance Request Card */}
                      {m.role === 'assistant' && (m.action_performed === 'ambulance_recorded' || m.structured_data?.type === 'ambulance_request') && m.structured_data && (
                        <SimulatedAmbulanceCard data={m.structured_data} />
                      )}

                      {/* 5. Support Ticket Registered Card */}
                      {m.role === 'assistant' && (m.action_performed === 'ticket_created' || m.structured_data?.type === 'support_ticket') && m.structured_data && (
                        <SupportTicketCard
                          data={m.structured_data}
                          onRequestHumanHelp={() => handleSendMessage('Please connect me with a human representative.')}
                          disabled={isSending}
                        />
                      )}

                      {/* 6. Human Escalation Card */}
                      {m.role === 'assistant' && (m.action_performed === 'escalation_recorded' || m.action_performed === 'emergency_escalated' || m.structured_data?.type === 'human_escalation') && m.structured_data && (
                        <EscalationCard data={m.structured_data} />
                      )}

                      {/* Suggested Quick Reply Chips */}
                      {m.suggested_prompts && m.suggested_prompts.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-200/60 flex flex-wrap gap-1.5">
                          {m.suggested_prompts.map((p, pIdx) => (
                            <button
                              key={pIdx}
                              disabled={isSending}
                              onClick={() => handleSendMessage(p)}
                              className="text-xs bg-white text-teal-800 hover:bg-teal-50 hover:border-teal-300 px-3 py-1 rounded-full border border-teal-200 transition font-medium shadow-2xs disabled:opacity-50"
                            >
                              {p}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Live Tool/Action Progress Indicator */}
                {isSending && (
                  <div className="flex justify-start">
                    <div className="bg-teal-50/80 rounded-2xl p-3.5 text-xs text-teal-900 border border-teal-200 flex items-center space-x-2.5 shadow-2xs">
                      <span className="w-2.5 h-2.5 rounded-full bg-teal-600 animate-ping" />
                      <span className="font-medium">AarogyaConnect AI is checking hospital operations & verifying constraints...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Bar */}
              <div className="p-4 border-t border-slate-200 bg-white rounded-b-2xl">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage();
                  }}
                  className="flex items-center space-x-2"
                >
                  <input
                    id="chat-input"
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Type your request (e.g. Book an appointment with Dr. Sharma tomorrow at 2 PM)..."
                    className="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent placeholder-slate-400 disabled:opacity-50"
                    disabled={isSending}
                  />
                  <button
                    id="chat-submit-button"
                    type="submit"
                    disabled={isSending || !inputMessage.trim()}
                    className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition flex items-center space-x-1.5 shadow-xs"
                  >
                    <span>Send</span>
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </div>
          </div>
        ) : !operatorSession ? (
          /* ============================================================ */
          /* OPERATOR ACCESS GATE (FOR UNAUTHENTICATED DIRECT NAVIGATION) */
          /* ============================================================ */
          <div className="max-w-xl mx-auto my-12 bg-white p-8 rounded-2xl border border-slate-200 shadow-xs text-center">
            <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto mb-4 text-amber-600 shadow-2xs">
              <Lock className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">Hospital Operator Access Required</h2>
            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              The hospital-wide Operations Dashboard displays confidential patient appointment rosters, simulated emergency requests, and internal escalations. This data is protected and restricted to authorized hospital operators.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                id="btn-gate-operator-login"
                onClick={() => setShowLoginModal(true)}
                className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-teal-600/20 flex items-center justify-center space-x-2"
              >
                <Lock className="w-4 h-4" />
                <span>Log In as Operator</span>
              </button>
              <button
                onClick={() => {
                  setActiveTab('patient');
                  window.location.hash = '#patient';
                }}
                className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-300 transition"
              >
                Return to Patient Assistant
              </button>
            </div>
          </div>
        ) : (
          /* ============================================================ */
          /* PHASE 5: HOSPITAL OPERATIONS DASHBOARD (AUTHORIZED OPERATORS) */
          /* ============================================================ */
          <div className="space-y-6">
            {/* Dashboard Header & Controls */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-xl font-bold text-slate-900">AarogyaConnect AI Operations</h1>
                  <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-teal-100 text-teal-800 border border-teal-200">
                    Operator Desk
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Aarogya Multispeciality Hospital • Live persistent records from SQLite
                </p>
              </div>

              <div className="flex items-center space-x-2.5 flex-wrap">
                {/* Link back to Patient Assistant */}
                <button
                  id="btn-back-to-patient"
                  onClick={() => {
                    setActiveTab('patient');
                    window.location.hash = '#patient';
                  }}
                  className="flex items-center space-x-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl border border-slate-300 transition shadow-2xs"
                  title="Return to Patient Assistant"
                >
                  <ArrowLeft className="w-3.5 h-3.5 text-slate-500" />
                  <span>Patient Assistant</span>
                </button>

                {/* Backend Connection Indicator */}
                <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Live SQLite (Port 8000)</span>
                </div>

                {/* Refresh Control */}
                <button
                  id="btn-refresh-dashboard"
                  onClick={loadDashboardData}
                  disabled={isLoadingDashboard}
                  className="flex items-center space-x-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-300 transition shadow-2xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDashboard ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {dashboardError && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{dashboardError}</span>
              </div>
            )}

            {/* Summary Metrics Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-semibold">Appointments Recorded</span>
                  <Calendar className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stats?.total_appointments ?? 0}</div>
                <p className="text-[11px] text-teal-700 mt-1 font-medium">Confirmed in SQLite</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-semibold">Ambulance Requests</span>
                  <Truck className="w-4 h-4 text-rose-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stats?.total_ambulance_requests ?? 0}</div>
                <p className="text-[11px] text-rose-700 mt-1 font-medium">Simulated Demos</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-semibold">Open Support Tickets</span>
                  <Ticket className="w-4 h-4 text-amber-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stats?.total_support_tickets ?? 0}</div>
                <p className="text-[11px] text-amber-700 mt-1 font-medium">Grievances Filed</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-semibold">Pending Escalations</span>
                  <UserCheck className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stats?.total_escalations ?? 0}</div>
                <p className="text-[11px] text-indigo-700 mt-1 font-medium">Human Attention</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between text-slate-500 mb-2">
                  <span className="text-xs font-semibold">Active Doctors</span>
                  <Activity className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">{stats?.total_doctors ?? 4}</div>
                <p className="text-[11px] text-emerald-700 mt-1 font-medium">All Specialties</p>
              </div>
            </div>

            {/* Tables Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 1. Confirmed Appointments Table */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                    <Calendar className="w-4 h-4 text-teal-600" />
                    <span>Confirmed Appointments</span>
                  </h3>
                  <span className="text-xs font-medium text-slate-500">Live SQLite Roster</span>
                </div>
                <div className="overflow-x-auto max-h-72 border border-slate-100 rounded-xl">
                  <table className="w-full min-w-[520px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3 whitespace-nowrap">Booking Ref</th>
                        <th className="py-2.5 px-3">Patient</th>
                        <th className="py-2.5 px-3">Doctor</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Date & Slot</th>
                        <th className="py-2.5 px-3 whitespace-nowrap min-w-[90px]">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {appointments.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-400">
                            <Inbox className="w-6 h-6 mx-auto mb-1 opacity-50" />
                            No appointments booked yet.
                          </td>
                        </tr>
                      ) : (
                        appointments.map((a, idx) => (
                          <tr key={a.id} className="hover:bg-slate-50 transition">
                            <td className="py-2.5 px-3 font-mono font-bold text-teal-700 whitespace-nowrap flex items-center space-x-1.5" title={a.reference_code}>
                              <span>{a.reference_code}</span>
                              {idx === 0 && isRecentRecord(a.created_at) && (
                                <span className="px-1.5 py-0.2 bg-teal-100 text-teal-800 rounded text-[9px] font-bold">
                                  NEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-medium" title={`${a.patient_name} (${a.patient_phone})`}>
                              {a.patient_name} <br/>
                              <span className="text-slate-400 text-[10px] font-mono">{a.patient_phone}</span>
                            </td>
                            <td className="py-2.5 px-3" title={`${a.doctor_name} (${a.doctor_department})`}>
                              {a.doctor_name} <br/>
                              <span className="text-[10px] text-slate-400">{a.doctor_department}</span>
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              {a.appointment_date} <br/>
                              <span className="text-teal-700 font-semibold">{a.appointment_time}</span>
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap min-w-[90px]">
                              <span className="inline-block px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold" title={a.status}>
                                {a.status}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 2. Ambulance Requests Table (Simulated Demo View) */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                    <Truck className="w-4 h-4 text-rose-600" />
                    <span>Ambulance Requests (Simulated Demo)</span>
                  </h3>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                    Prototype Only
                  </span>
                </div>
                {/* Persistent Notice Banner */}
                <div className="mb-3 px-3 py-1.5 rounded-lg bg-rose-50/80 border border-rose-200 text-rose-800 text-[11px] flex items-center justify-between">
                  <span><strong>Notice:</strong> Simulated demo records — no real dispatch takes place.</span>
                  <span className="font-mono text-[10px]">Indore Region</span>
                </div>
                <div className="overflow-x-auto max-h-72 border border-slate-100 rounded-xl">
                  <table className="w-full min-w-[540px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3 whitespace-nowrap">Request Ref</th>
                        <th className="py-2.5 px-3">Patient / Phone</th>
                        <th className="py-2.5 px-3">Pickup Location</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Created</th>
                        <th className="py-2.5 px-3 min-w-[130px] whitespace-nowrap">Simulated Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {ambulanceRequests.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-400">
                            <Inbox className="w-6 h-6 mx-auto mb-1 opacity-50" />
                            No ambulance requests recorded.
                          </td>
                        </tr>
                      ) : (
                        ambulanceRequests.map((amb, idx) => (
                          <tr key={amb.id} className="hover:bg-slate-50 transition">
                            <td className="py-2.5 px-3 font-mono font-bold text-rose-700 whitespace-nowrap flex items-center space-x-1.5" title={amb.reference_code}>
                              <span>{amb.reference_code}</span>
                              {idx === 0 && isRecentRecord(amb.created_at) && (
                                <span className="px-1.5 py-0.2 bg-rose-100 text-rose-800 rounded text-[9px] font-bold">
                                  NEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-medium" title={`${amb.patient_name} (${amb.contact_phone})`}>
                              {amb.patient_name} <br/>
                              <span className="text-slate-400 text-[10px] font-mono">{amb.contact_phone}</span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 max-w-xs truncate cursor-help" title={amb.pickup_address}>
                              {amb.pickup_address}
                            </td>
                            <td className="py-2.5 px-3 text-slate-400 text-[10px] font-mono whitespace-nowrap">
                              {new Date(amb.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </td>
                            <td className="py-2.5 px-3 min-w-[130px]">
                              <span className="inline-block px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[10px] font-semibold break-words leading-tight" title={amb.status}>
                                {amb.status}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 3. Support Tickets Table (With Operator Status Toggle) */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                    <Ticket className="w-4 h-4 text-amber-600" />
                    <span>Support Tickets & Grievances</span>
                  </h3>
                  <span className="text-xs font-medium text-slate-500">Customer Operations</span>
                </div>
                <div className="overflow-x-auto max-h-72 border border-slate-100 rounded-xl">
                  <table className="w-full min-w-[580px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3 whitespace-nowrap">Ticket Ref</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Category</th>
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Priority</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Created</th>
                        <th className="py-2.5 px-3 whitespace-nowrap min-w-[120px]">Status / Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {tickets.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-8 text-center text-slate-400">
                            <Inbox className="w-6 h-6 mx-auto mb-1 opacity-50" />
                            No tickets filed.
                          </td>
                        </tr>
                      ) : (
                        tickets.map((t, idx) => (
                          <tr key={t.id} className="hover:bg-slate-50 transition">
                            <td className="py-2.5 px-3 font-mono font-bold text-amber-700 whitespace-nowrap flex items-center space-x-1.5" title={t.reference_code}>
                              <span>{t.reference_code}</span>
                              {idx === 0 && isRecentRecord(t.created_at) && (
                                <span className="px-1.5 py-0.2 bg-amber-100 text-amber-800 rounded text-[9px] font-bold">
                                  NEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-semibold whitespace-nowrap">{t.category}</td>
                            <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate cursor-help" title={t.description}>
                              {t.description}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                t.priority === 'URGENT' || t.priority === 'HIGH' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                              }`} title={`Priority: ${t.priority}`}>
                                {t.priority}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-400 text-[10px] font-mono whitespace-nowrap">
                              {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap min-w-[120px]">
                              {t.status === 'OPEN' ? (
                                <button
                                  onClick={() => handleUpdateTicketStatus(t.id, 'RESOLVED')}
                                  disabled={updatingId === `tkt-${t.id}`}
                                  className="px-2 py-1 rounded bg-amber-100 hover:bg-emerald-100 text-amber-900 hover:text-emerald-900 text-[10px] font-bold border border-amber-300 transition flex items-center space-x-1"
                                  title="Click to resolve this ticket"
                                >
                                  <span>OPEN</span>
                                  <span className="text-[9px] text-amber-700 font-normal underline ml-1">Resolve</span>
                                </button>
                              ) : (
                                <span className="inline-block px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                                  {t.status}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 4. Human Escalations Table (With Operator Status Toggle) */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                    <UserCheck className="w-4 h-4 text-indigo-600" />
                    <span>Human Escalations</span>
                  </h3>
                  <span className="text-xs font-medium text-slate-500">Live Attention</span>
                </div>
                <div className="overflow-x-auto max-h-72 border border-slate-100 rounded-xl">
                  <table className="w-full min-w-[560px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3 whitespace-nowrap">Escalation Ref</th>
                        <th className="py-2.5 px-3">Patient / Contact</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Priority</th>
                        <th className="py-2.5 px-3">Escalation Reason</th>
                        <th className="py-2.5 px-3 whitespace-nowrap min-w-[120px]">Status / Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {escalations.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-400">
                            <Inbox className="w-6 h-6 mx-auto mb-1 opacity-50" />
                            No active escalations.
                          </td>
                        </tr>
                      ) : (
                        escalations.map((esc, idx) => (
                          <tr key={esc.id} className="hover:bg-slate-50 transition">
                            <td className="py-2.5 px-3 font-mono font-bold text-indigo-700 whitespace-nowrap flex items-center space-x-1.5" title={esc.reference_code}>
                              <span>{esc.reference_code}</span>
                              {idx === 0 && isRecentRecord(esc.created_at) && (
                                <span className="px-1.5 py-0.2 bg-indigo-100 text-indigo-800 rounded text-[9px] font-bold">
                                  NEW
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-medium" title={`${esc.patient_name} (${esc.contact_phone})`}>
                              {esc.patient_name} <br/>
                              <span className="text-slate-400 text-[10px] font-mono">{esc.contact_phone}</span>
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                esc.priority === 'URGENT' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                              }`} title={`Priority: ${esc.priority}`}>
                                {esc.priority}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 max-w-xs truncate cursor-help" title={esc.reason}>
                              {esc.reason}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap min-w-[120px]">
                              {esc.status !== 'RESOLVED' ? (
                                <button
                                  onClick={() => handleUpdateEscalationStatus(esc.id, 'RESOLVED')}
                                  disabled={updatingId === `esc-${esc.id}`}
                                  className="px-2 py-1 rounded bg-indigo-100 hover:bg-emerald-100 text-indigo-900 hover:text-emerald-900 text-[10px] font-bold border border-indigo-300 transition flex items-center space-x-1"
                                  title="Click to resolve escalation"
                                >
                                  <span>{esc.status}</span>
                                  <span className="text-[9px] text-indigo-700 font-normal underline ml-1">Resolve</span>
                                </button>
                              ) : (
                                <span className="inline-block px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                                  RESOLVED
                                </span>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 5. Recent Agent Tool Audit Logs */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                    <Activity className="w-4 h-4 text-cyan-600" />
                    <span>Agent Tool Execution & Activity Trail</span>
                  </h3>
                  <span className="text-xs font-medium text-slate-500">Live SQLite Audit Log</span>
                </div>
                <div className="overflow-x-auto max-h-72 border border-slate-100 rounded-xl">
                  <table className="w-full min-w-[680px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3 whitespace-nowrap">Tool Executed</th>
                        <th className="py-2.5 px-3 whitespace-nowrap min-w-[90px]">Result</th>
                        <th className="py-2.5 px-3">Parameters / Context</th>
                        <th className="py-2.5 px-3">Execution Summary</th>
                        <th className="py-2.5 px-3 whitespace-nowrap">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {actionLogs.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-slate-400">
                            <Inbox className="w-6 h-6 mx-auto mb-1 opacity-50" />
                            No agent actions recorded.
                          </td>
                        </tr>
                      ) : (
                        actionLogs.map((log) => (
                          <tr key={log.id} className="hover:bg-slate-50 transition">
                            <td className="py-2.5 px-3 font-mono font-bold text-teal-800 whitespace-nowrap" title={log.tool_name || log.action_type}>
                              {log.tool_name || log.action_type}
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap min-w-[90px]">
                              <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                log.result_status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                              }`} title={log.result_status}>
                                {log.result_status}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500 max-w-xs truncate cursor-help" title={log.parameters || ''}>
                              {log.parameters || '-'}
                            </td>
                            <td className="py-2.5 px-3 text-slate-700 max-w-sm truncate cursor-help" title={log.result_summary}>
                              {log.result_summary}
                            </td>
                            <td className="py-2.5 px-3 text-slate-400 text-[10px] font-mono whitespace-nowrap" title={new Date(log.created_at).toLocaleString()}>
                              {new Date(log.created_at).toLocaleTimeString()}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
