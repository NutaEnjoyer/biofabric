export type OpType =
  | 'opening_balance'
  | 'intake'
  | 'withdrawal'
  | 'issue_for_control'
  | 'movement'
  | 'adjustment';

export type DirectionCode = 'subsidiary' | 'vivarium';

export type SexCode = 'M' | 'F' | 'U';

// Значения из qa_record_statuses: in_process / current / archived
export type RecordStatus = 'in_process' | 'current' | 'archived';

export interface Species {
  species_id: number;
  name: string;
  code: string;
  has_age_categories: boolean;
  has_mass_bins: boolean;
}

export interface Direction {
  direction_id: number;
  name: string;
  code: DirectionCode;
}

export interface AgeCat {
  age_cat_id: number;
  name: string;
}

export interface MassBin {
  mass_bin_id: number;
  name: string;
}

export interface Group {
  group_id: number;
  name: string;
  direction_code: DirectionCode;
  species_code: string | null;
}

export interface Cohort {
  cohort_id: number;
  label: string;
  status_tag: string | null;
  is_active: boolean;
  direction_code: DirectionCode;
  species_code: string | null;
}

export interface OperationCreate {
  date: string;
  period_month: string;
  op_type: OpType;
  species_code: string;
  direction_code: DirectionCode;
  quantity: number;
  sex?: SexCode;
  age_bin_code?: string;   // передаётся как name в qa_age_categories
  mass_bin_code?: string;  // передаётся как name в qa_mass_bins
  group_code?: string;     // передаётся как name в qa_groups
  cohort_code?: string;    // передаётся как label в qa_cohorts
  src_group_code?: string;
  src_cohort_code?: string;
  dst_group_code?: string;
  dst_cohort_code?: string;
  transfer_key?: string;
  purpose_text?: string;
  reason?: string;
  adjusts_period?: string;
}

export interface IdResponse {
  ok: boolean;
  id: number;
  message?: string;
}

export interface ApiResponse {
  ok: boolean;
  message?: string;
}

export interface MonthlySummaryRow {
  species_code: string;
  direction_code: DirectionCode;
  intake: number;
  withdrawal: number;
  issue_for_control: number;
  movement_in: number;
  movement_out: number;
  adjustment: number;
  closing_balance: number;
}

export interface DirectionBalance {
  direction_code: DirectionCode;
  current: number;
  prev: number;
  delta: number;
  trend: 'up' | 'down' | 'same';
}

export interface DashboardData {
  period_month: string;
  prev_month: string;
  total: {
    current: number;
    prev: number;
    delta: number;
    trend: 'up' | 'down' | 'same';
  };
  by_direction: DirectionBalance[];
}

export interface DynamicsRow {
  period_month: string;
  group_key: string;
  balance: number;
}

export interface HistoryEntry {
  entry_id: number;
  entry_date: string;
  entry_type: string;
  status_code: RecordStatus;
  quantity: number;
  sex: string | null;
  purpose_text: string | null;
  note: string | null;
  transfer_key: string | null;
  group_name: string | null;
  cohort_label: string | null;
  created_at: string;
  created_by: number | null;
}

export interface VivariumGroup {
  group_id: number;
  group_name: string;
  species: {
    species_code: string;
    species_name: string;
    balance: number;
  }[];
}
