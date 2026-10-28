export interface Doctor {
  id: number;
  name: string;
  department: string;
  specialization: string;
  qualification: string;
  experience_years: number;
  consultation_fee: number;
  room_no: string;
  opd_timings: string;
  is_active: boolean;
}

export interface DoctorSlot {
  id: number;
  doctor_id: number;
  slot_date: string;
  slot_time: string;
  is_booked: boolean;
}

export interface Appointment {
  id: number;
  reference_code: string;
  doctor_id: number;
  doctor_name: string;
  doctor_department: string;
  patient_name: string;
  patient_phone: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  notes?: string;
  created_at: string;
}

export interface AmbulanceRequest {
  id: number;
  reference_code: string;
  patient_name: string;
  contact_phone: string;
  pickup_address: string;
  emergency_nature?: string;
  status: string;
  is_emergency_redirect: boolean;
  disclaimer: string;
  created_at: string;
}

export interface SupportTicket {
  id: number;
  reference_code: string;
  patient_name: string;
  contact_phone: string;
  category: string;
  priority: string;
  description: string;
  status: string;
  created_at: string;
}

export interface HumanEscalation {
  id: number;
  reference_code: string;
  patient_name: string;
  contact_phone: string;
  reason: string;
  priority: string;
  status: string;
  notes?: string;
  created_at: string;
}

export interface AgentActionLog {
  id: number;
  action_type: string;
  tool_name?: string;
  parameters?: string;
  result_status: string;
  result_summary: string;
  created_at: string;
}

export interface DashboardStats {
  total_appointments: number;
  total_ambulance_requests: number;
  total_support_tickets: number;
  total_escalations: number;
  total_doctors: number;
  system_mode: string;
}

export interface PendingBooking {
  doctor_id: number;
  doctor_name: string;
  doctor_department: string;
  consultation_fee: number;
  appointment_date: string;
  appointment_time: string;
  patient_name: string;
  patient_phone: string;
  notes?: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  action_performed?: string;
  action_reference?: string;
  pending_booking?: PendingBooking;
  structured_data?: any;
  suggested_prompts?: string[];
  created_at?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  history?: Array<{ role: string; content: string }>;
  pending_booking?: PendingBooking | null;
}

export interface ChatResponse {
  reply: string;
  mode: 'ai' | 'deterministic_demo';
  session_id: string;
  action_performed?: string;
  action_reference?: string;
  pending_booking?: PendingBooking | null;
  structured_data?: any;
  suggested_prompts?: string[];
}

export interface OperatorSession {
  access_token: string;
  token_type: string;
  expires_at: number;
  username: string;
  role: string;
  hospital: string;
}
