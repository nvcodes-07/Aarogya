import type {
  Doctor,
  DoctorSlot,
  Appointment,
  AmbulanceRequest,
  SupportTicket,
  HumanEscalation,
  AgentActionLog,
  DashboardStats,
  ChatRequest,
  ChatResponse,
  OperatorSession
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? '/api' : 'http://localhost:8000/api');

let operatorToken: string | null = typeof window !== 'undefined' ? sessionStorage.getItem('aarogya_operator_token') : null;

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string> || {})
    };

    if (operatorToken) {
      headers['Authorization'] = `Bearer ${operatorToken}`;
    }

    const res = await fetch(url, {
      ...options,
      headers
    });

    if (!res.ok) {
      if (res.status === 401) {
        // Clear stale operator token on any 401 response
        operatorToken = null;
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem('aarogya_operator_token');
          localStorage.removeItem('aarogya_operator_token');
        }
      }

      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMessage);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Operator Authentication Gate
  loginOperator: async (username: string, password: string): Promise<OperatorSession> => {
    const data = await request<OperatorSession>('/auth/operator/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    operatorToken = data.access_token;
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('aarogya_operator_token', data.access_token);
      localStorage.removeItem('aarogya_operator_token');
    }
    return data;
  },

  getOperatorProfile: (): Promise<{ username: string; role: string; hospital: string }> => {
    return request<{ username: string; role: string; hospital: string }>('/auth/operator/me');
  },

  getDemoCredentials: (): Promise<{ username: string; password: string; note: string }> => {
    return request<{ username: string; password: string; note: string }>('/auth/operator/demo-credentials');
  },

  logoutOperator: async (): Promise<void> => {
    try {
      if (operatorToken) {
        await request<{ status: string }>('/auth/operator/logout', { method: 'POST' });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      operatorToken = null;
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('aarogya_operator_token');
        localStorage.removeItem('aarogya_operator_token');
      }
    }
  },

  getStoredOperatorToken: (): string | null => {
    return operatorToken;
  },

  setOperatorToken: (token: string | null) => {
    operatorToken = token;
    if (typeof window !== 'undefined') {
      if (token) {
        sessionStorage.setItem('aarogya_operator_token', token);
      } else {
        sessionStorage.removeItem('aarogya_operator_token');
      }
      localStorage.removeItem('aarogya_operator_token');
    }
  },

  // Health
  checkHealth: () => request<{ status: string; app: string; hospital: string; ai_enabled: boolean; model: string }>('/health'),

  // Chat (Public Patient Portal)
  sendMessage: (payload: ChatRequest) => request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Doctors & Slots (Public Patient Portal)
  getDoctors: () => request<Doctor[]>('/doctors'),
  searchDoctors: (query?: string, department?: string) => {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (department) params.append('department', department);
    return request<Doctor[]>(`/doctors/search?${params.toString()}`);
  },
  getSlots: (doctorId: number, date: string) => request<DoctorSlot[]>(`/appointments/slots?doctor_id=${doctorId}&date=${date}`),

  // Appointments (Creation: Public Patient; Listing: Protected Operator)
  createAppointment: (payload: {
    doctor_id: number;
    patient_name: string;
    patient_phone: string;
    appointment_date: string;
    appointment_time: string;
    notes?: string;
  }) => request<Appointment>('/appointments', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getAppointments: (limit: number = 50) => request<Appointment[]>(`/appointments?limit=${limit}`),

  // Ambulance (Creation: Public Patient; Listing: Protected Operator)
  createAmbulanceRequest: (payload: {
    patient_name: string;
    contact_phone: string;
    pickup_address: string;
    emergency_nature?: string;
    is_emergency?: boolean;
  }) => request<AmbulanceRequest>('/ambulance-requests', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getAmbulanceRequests: (limit: number = 50) => request<AmbulanceRequest[]>(`/ambulance-requests?limit=${limit}`),

  // Tickets (Creation: Public Patient; Listing: Protected Operator)
  createTicket: (payload: {
    patient_name: string;
    contact_phone: string;
    category: string;
    priority: string;
    description: string;
  }) => request<SupportTicket>('/tickets', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getTickets: (limit: number = 50) => request<SupportTicket[]>(`/tickets?limit=${limit}`),

  // Escalations (Creation: Public Patient; Listing: Protected Operator)
  createEscalation: (payload: {
    patient_name: string;
    contact_phone: string;
    reason: string;
    priority?: string;
    notes?: string;
  }) => request<HumanEscalation>('/escalations', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getEscalations: (limit: number = 50) => request<HumanEscalation[]>(`/escalations?limit=${limit}`),

  // Action Logs & Dashboard Stats (PROTECTED OPERATOR)
  getActionLogs: (limit: number = 50) => request<AgentActionLog[]>(`/actions?limit=${limit}`),
  getDashboardStats: () => request<DashboardStats>('/dashboard/stats'),

  // Status updates by authorized operator
  updateTicketStatus: (ticketId: number, status: string) => request<SupportTicket>(`/tickets/${ticketId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status })
  }),
  updateEscalationStatus: (escalationId: number, status: string) => request<HumanEscalation>(`/escalations/${escalationId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status })
  })
};
