import React from 'react';
import {
  Calendar,
  Clock,
  User,
  Phone,
  CheckCircle2,
  AlertTriangle,
  Truck,
  Ticket,
  UserCheck,
  Stethoscope,
  Building,
  DollarSign,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import type { PendingBooking } from '../types';

interface AvailableSlotsCardProps {
  data: {
    doctor_id?: number;
    doctor_name?: string;
    doctor_department?: string;
    specialization?: string;
    consultation_fee?: number;
    room_no?: string;
    date?: string;
    available_slots?: string[];
  };
  onSelectSlot: (slot: string) => void;
  disabled?: boolean;
}

export const AvailableSlotsCard: React.FC<AvailableSlotsCardProps> = ({
  data,
  onSelectSlot,
  disabled
}) => {
  if (!data.available_slots || data.available_slots.length === 0) return null;

  return (
    <div className="mt-3.5 p-4 bg-white rounded-xl border border-teal-200 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-teal-50 flex items-center justify-center text-teal-700">
            <Stethoscope className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">
              {data.doctor_name || 'Hospital Doctor'}
            </h4>
            <p className="text-[11px] text-slate-500">
              {data.doctor_department} {data.specialization ? `• ${data.specialization}` : ''}
            </p>
          </div>
        </div>
        {data.consultation_fee && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
            ₹{data.consultation_fee}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-slate-600 mb-2.5">
        <span className="flex items-center space-x-1.5 font-medium">
          <Calendar className="w-3.5 h-3.5 text-teal-600" />
          <span>Date: <strong>{data.date || 'Tomorrow'}</strong></span>
        </span>
        {data.room_no && (
          <span className="flex items-center space-x-1 text-slate-500 text-[11px]">
            <Building className="w-3 h-3 text-slate-400" />
            <span>Room {data.room_no}</span>
          </span>
        )}
      </div>

      <p className="text-[11px] text-slate-500 font-medium mb-2">Select an available consultation slot:</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {data.available_slots.map((slot, idx) => (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelectSlot(`I would like to select the ${slot} slot.`)}
            className="flex items-center justify-center space-x-1 py-2 px-2.5 text-xs font-semibold rounded-lg bg-teal-50 hover:bg-teal-600 hover:text-white text-teal-800 border border-teal-200 transition shadow-2xs group disabled:opacity-50"
          >
            <Clock className="w-3 h-3 text-teal-600 group-hover:text-white" />
            <span>{slot}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

interface ProposedBookingCardProps {
  booking: PendingBooking;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
}

export const ProposedBookingCard: React.FC<ProposedBookingCardProps> = ({
  booking,
  onConfirm,
  onCancel,
  disabled
}) => {
  return (
    <div className="mt-3.5 p-4 bg-white rounded-xl border-2 border-teal-500 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-teal-500 animate-ping" />
          <span className="text-xs font-bold text-teal-900 uppercase tracking-wide">
            Proposed Appointment (Pending Confirmation)
          </span>
        </div>
        <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
          Confirmation Required
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs mb-3.5 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
        <div className="flex items-center space-x-2">
          <Stethoscope className="w-3.5 h-3.5 text-teal-600 shrink-0" />
          <span><strong className="text-slate-600">Doctor:</strong> {booking.doctor_name}</span>
        </div>
        <div className="flex items-center space-x-2">
          <Building className="w-3.5 h-3.5 text-teal-600 shrink-0" />
          <span><strong className="text-slate-600">Department:</strong> {booking.doctor_department}</span>
        </div>
        <div className="flex items-center space-x-2">
          <Calendar className="w-3.5 h-3.5 text-teal-600 shrink-0" />
          <span><strong className="text-slate-600">Date:</strong> {booking.appointment_date}</span>
        </div>
        <div className="flex items-center space-x-2">
          <Clock className="w-3.5 h-3.5 text-teal-600 shrink-0" />
          <span><strong className="text-slate-600">Slot:</strong> <span className="font-semibold text-teal-800">{booking.appointment_time}</span></span>
        </div>
        <div className="flex items-center space-x-2">
          <User className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <span><strong className="text-slate-600">Patient:</strong> {booking.patient_name}</span>
        </div>
        <div className="flex items-center space-x-2">
          <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <span><strong className="text-slate-600">Phone:</strong> <span className="font-mono">{booking.patient_phone}</span></span>
        </div>
      </div>

      <p className="text-[11px] text-slate-500 mb-3">
        Please verify the details above. Click <strong>Confirm Booking</strong> to create this appointment in the hospital records, or <strong>Cancel</strong> to abort.
      </p>

      <div className="flex items-center space-x-2.5">
        <button
          id="btn-confirm-appointment"
          disabled={disabled}
          onClick={onConfirm}
          className="flex-1 py-2.5 px-3 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-lg transition shadow-sm flex items-center justify-center space-x-1.5 disabled:opacity-50"
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Confirm Booking</span>
        </button>
        <button
          id="btn-cancel-appointment"
          disabled={disabled}
          onClick={onCancel}
          className="py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg border border-slate-300 transition disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

interface ConfirmedAppointmentCardProps {
  data: {
    reference_code: string;
    doctor_name?: string;
    doctor?: string;
    date: string;
    time: string;
    patient_name?: string;
  };
}

export const ConfirmedAppointmentCard: React.FC<ConfirmedAppointmentCardProps> = ({ data }) => {
  return (
    <div className="mt-3.5 p-4 bg-emerald-50/70 rounded-xl border border-emerald-300 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-emerald-200 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <span className="text-xs font-bold text-emerald-950 uppercase tracking-wide">
            Appointment Confirmed (Live in SQLite)
          </span>
        </div>
        <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-600 text-white">
          {data.reference_code}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-white p-3 rounded-lg border border-emerald-200/80 mb-2.5">
        <div><strong className="text-slate-500">Doctor:</strong> {data.doctor_name || data.doctor}</div>
        <div><strong className="text-slate-500">Date & Slot:</strong> {data.date} at <strong className="text-emerald-800">{data.time}</strong></div>
        {data.patient_name && <div><strong className="text-slate-500">Patient:</strong> {data.patient_name}</div>}
        <div><strong className="text-slate-500">Status:</strong> <span className="font-semibold text-emerald-700">CONFIRMED</span></div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-emerald-800 font-medium">
        <span>📍 Location: OPD Desk, Aarogya Multispeciality Hospital</span>
        <span className="text-emerald-700">✓ SMS Confirmation Simulated</span>
      </div>
    </div>
  );
};

interface SimulatedAmbulanceCardProps {
  data: {
    reference_code: string;
    pickup_address?: string;
    patient_name?: string;
    contact_phone?: string;
    status?: string;
    disclaimer?: string;
  };
}

export const SimulatedAmbulanceCard: React.FC<SimulatedAmbulanceCardProps> = ({ data }) => {
  return (
    <div className="mt-3.5 p-4 bg-rose-50/60 rounded-xl border border-rose-300 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-rose-200 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-rose-600 text-white flex items-center justify-center">
            <Truck className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-rose-950 uppercase tracking-wide">
            Simulated Ambulance Request (Demo Record)
          </span>
        </div>
        <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-rose-600 text-white">
          {data.reference_code}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-1.5 text-xs bg-white p-3 rounded-lg border border-rose-200 mb-3">
        {data.pickup_address && (
          <div><strong className="text-slate-600">Pickup Location:</strong> {data.pickup_address}</div>
        )}
        {data.contact_phone && (
          <div><strong className="text-slate-600">Contact:</strong> {data.patient_name ? `${data.patient_name} • ` : ''}<span className="font-mono">{data.contact_phone}</span></div>
        )}
        <div><strong className="text-slate-600">Simulated Status:</strong> <span className="font-semibold text-rose-700">{data.status || 'DEMO_LOGGED'}</span></div>
      </div>

      {/* Prominent Emergency Warning */}
      <div className="p-2.5 rounded-lg bg-rose-100/80 border border-rose-300 text-rose-900 text-[11px] leading-relaxed flex items-start space-x-2">
        <ShieldAlert className="w-4 h-4 text-rose-700 shrink-0 mt-0.5 animate-pulse" />
        <div>
          <strong>PROTOTYPE DEMONSTRATION ONLY:</strong> No actual ambulance has been dispatched. All operational records are for hackathon demonstration. For real medical emergencies, immediately dial <strong>108 / 112</strong>.
        </div>
      </div>
    </div>
  );
};

interface SupportTicketCardProps {
  data: {
    reference_code: string;
    category?: string;
    priority?: string;
    description?: string;
    status?: string;
    patient_name?: string;
  };
  onRequestHumanHelp: () => void;
  disabled?: boolean;
}

export const SupportTicketCard: React.FC<SupportTicketCardProps> = ({
  data,
  onRequestHumanHelp,
  disabled
}) => {
  return (
    <div className="mt-3.5 p-4 bg-amber-50/70 rounded-xl border border-amber-300 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-amber-200 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-amber-600 text-white flex items-center justify-center">
            <Ticket className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-amber-950 uppercase tracking-wide">
            Support Ticket Registered
          </span>
        </div>
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-amber-600 text-white">
          {data.reference_code}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-white p-3 rounded-lg border border-amber-200 mb-3">
        <div><strong className="text-slate-600">Category:</strong> {data.category || 'GENERAL'}</div>
        <div><strong className="text-slate-600">Priority:</strong> <span className="font-semibold text-amber-800">{data.priority || 'MEDIUM'}</span></div>
        <div><strong className="text-slate-600">Status:</strong> <span className="font-semibold text-amber-700">{data.status || 'OPEN'}</span></div>
        {data.patient_name && <div><strong className="text-slate-600">Patient:</strong> {data.patient_name}</div>}
      </div>

      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-slate-500">Hospital duty desk has logged your issue.</span>
        <button
          onClick={onRequestHumanHelp}
          disabled={disabled}
          className="text-xs font-semibold text-amber-900 bg-amber-200/80 hover:bg-amber-300 px-3 py-1.5 rounded-lg transition flex items-center space-x-1 shadow-2xs"
        >
          <UserCheck className="w-3.5 h-3.5 text-amber-800" />
          <span>Speak to Human Desk</span>
        </button>
      </div>
    </div>
  );
};

interface EscalationCardProps {
  data: {
    reference_code: string;
    priority?: string;
    reason?: string;
    status?: string;
  };
}

export const EscalationCard: React.FC<EscalationCardProps> = ({ data }) => {
  return (
    <div className="mt-3.5 p-4 bg-indigo-50/70 rounded-xl border border-indigo-300 shadow-sm text-slate-900">
      <div className="flex items-center justify-between border-b border-indigo-200 pb-2.5 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
            <UserCheck className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-indigo-950 uppercase tracking-wide">
            Human Operator Escalation
          </span>
        </div>
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-indigo-600 text-white">
          {data.reference_code}
        </span>
      </div>

      <div className="text-xs bg-white p-3 rounded-lg border border-indigo-200 space-y-1">
        <div><strong className="text-slate-600">Priority:</strong> <span className="font-semibold text-indigo-800">{data.priority || 'URGENT'}</span></div>
        {data.reason && <div><strong className="text-slate-600">Reason:</strong> {data.reason}</div>}
        <div><strong className="text-slate-600">Status:</strong> <span className="font-semibold text-indigo-700">{data.status || 'PENDING ATTENTION'}</span></div>
      </div>

      <p className="text-[11px] text-indigo-800 mt-2 font-medium">
        Hospital operations duty manager has received this alert and will initiate contact.
      </p>
    </div>
  );
};

