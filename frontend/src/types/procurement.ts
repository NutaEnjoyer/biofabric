export type ProcurementStatus =
  | 'draft'
  | 'on_approval'
  | 'in_progress'
  | 'awaiting_delivery'
  | 'done'
  | 'overdue';

export type ApprovalDecision = 'approve' | 'reject' | 'return_for_rework';

export interface RequestItemIn {
  nomenclature: string;
  tech_spec?: string;
  due_days?: number;
  quantity: number;
  justification?: string;
}

export interface ProcurementCreate {
  subject: string;
  justification?: string;
  items: RequestItemIn[];
}

export interface RequestItem {
  id: number;
  nomenclature: string;
  tech_spec?: string;
  due_days?: number;
  quantity: number;
  justification?: string;
}

export interface Approval {
  id: number;
  user_id: number;
  decision: ApprovalDecision;
  comment?: string;
  decided_at: string;
}

export interface SupplierQuote {
  id: number;
  supplier_name: string;
  price: number;
  delivery_days?: number;
  payment_terms?: string;
  comment?: string;
  file_ref?: string;
}

export interface ProcurementDocument {
  id: number;
  doc_type: string;
  filename: string;
  storage_url?: string;
  signed: boolean;
}

export interface ProcurementEvent {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ProcurementRequest {
  id: number;
  subject: string;
  justification?: string;
  status: ProcurementStatus;
  created_at: string;
  items?: RequestItem[];
  approvals?: Approval[];
  quotes?: SupplierQuote[];
  documents?: ProcurementDocument[];
  events?: ProcurementEvent[];
}

export interface ApprovalIn {
  request_id: number;
  user_id: number;
  decision: ApprovalDecision;
  comment?: string;
}

export interface SupplierQuoteIn {
  request_id: number;
  supplier_name: string;
  price: number;
  delivery_days?: number;
  payment_terms?: string;
  comment?: string;
  file_ref?: string;
}

export interface DocumentIn {
  request_id: number;
  doc_type: string;
  filename: string;
  storage_url?: string;
  signed: boolean;
}
