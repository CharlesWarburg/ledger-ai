export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;
export type DecimalString = string;

export type UserRole = "user" | "admin";
export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue" | "cancelled";
export type DocumentType = "receipt" | "invoice_attachment" | "other";
export type DocumentProcessingStatus =
  | "pending"
  | "processing"
  | "review_required"
  | "completed"
  | "failed";
export type RecentActivityType = "invoice_created" | "payment_received";

export interface UserRegister {
  email: string;
  password: string;
}

export type UserLogin = UserRegister;

export interface AccessTokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface UserResponse {
  id: UUID;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface CustomerCreate {
  name: string;
  email?: string | null;
  phone?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  postal_code?: string | null;
  country_code?: string | null;
  vat_number?: string | null;
}

export type CustomerUpdate = Partial<CustomerCreate>;

export interface CustomerResponse extends Required<CustomerCreate> {
  id: UUID;
  owner_id: UUID;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface InvoiceLineItemCreate {
  description: string;
  quantity: DecimalString;
  unit_price: DecimalString;
  vat_rate: DecimalString;
}

export interface InvoiceLineItemResponse extends InvoiceLineItemCreate {
  id: UUID;
  invoice_id: UUID;
  subtotal: DecimalString;
  vat_amount: DecimalString;
  total: DecimalString;
  position: number;
}

export interface InvoiceCreate {
  customer_id: UUID;
  invoice_number: string;
  currency?: string;
  issue_date: ISODate;
  due_date: ISODate;
  notes?: string | null;
  line_items: InvoiceLineItemCreate[];
}

export type InvoiceUpdate = Partial<InvoiceCreate>;

export interface InvoiceStatusUpdate {
  status: InvoiceStatus;
}

export interface InvoiceResponse {
  id: UUID;
  owner_id: UUID;
  customer_id: UUID;
  invoice_number: string;
  status: InvoiceStatus;
  currency: string;
  issue_date: ISODate;
  due_date: ISODate;
  subtotal: DecimalString;
  vat_total: DecimalString;
  total: DecimalString;
  notes: string | null;
  line_items: InvoiceLineItemResponse[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface PaymentCreate {
  amount: DecimalString;
  payment_date: ISODate;
  payment_method: string;
  reference?: string | null;
  notes?: string | null;
}

export type PaymentUpdate = Partial<PaymentCreate>;

export interface PaymentResponse extends Required<PaymentCreate> {
  id: UUID;
  owner_id: UUID;
  invoice_id: UUID;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface DocumentResponse {
  id: UUID;
  owner_id: UUID;
  invoice_id: UUID | null;
  document_type: DocumentType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: ISODateTime;
}

export interface DocumentUpdate {
  document_type?: DocumentType | null;
  invoice_id?: UUID | null;
}

export interface ExtractedInvoiceLineItem {
  description?: string | null;
  quantity?: DecimalString | null;
  unit_price?: DecimalString | null;
  vat_rate?: DecimalString | null;
}

export interface InvoiceExtraction {
  supplier_name?: string | null;
  supplier_email?: string | null;
  customer_name?: string | null;
  invoice_number?: string | null;
  currency?: string | null;
  issue_date?: ISODate | null;
  due_date?: ISODate | null;
  line_items?: ExtractedInvoiceLineItem[];
  subtotal?: DecimalString | null;
  vat_total?: DecimalString | null;
  total?: DecimalString | null;
  notes?: string | null;
  confidence?: number | null;
}

export interface DocumentProcessingResponse {
  id: UUID;
  document_id: UUID;
  owner_id: UUID;
  status: DocumentProcessingStatus;
  provider: string | null;
  extracted_data: InvoiceExtraction | null;
  error_message: string | null;
  attempt_count: number;
  started_at: ISODateTime | null;
  completed_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface DocumentProcessingReview {
  extracted_data: InvoiceExtraction;
}

export interface DocumentProcessingInvoiceCreate {
  customer_id: UUID;
}

export interface DashboardKpis {
  total_revenue: DecimalString;
  outstanding_amount: DecimalString;
  overdue_amount: DecimalString;
  paid_invoice_count: number;
}

export interface InvoiceStatusMetric {
  status: InvoiceStatus;
  count: number;
  total_amount: DecimalString;
}

export interface MonthlyCashFlowPoint {
  month: ISODate;
  amount: DecimalString;
}

export interface RecentActivityItem {
  activity_type: RecentActivityType;
  entity_id: UUID;
  invoice_id: UUID;
  description: string;
  amount: DecimalString | null;
  occurred_at: ISODateTime;
}

export interface DashboardResponse {
  currency: string;
  period_start: ISODate;
  period_end: ISODate;
  kpis: DashboardKpis;
  invoice_statuses: InvoiceStatusMetric[];
  monthly_cash_flow: MonthlyCashFlowPoint[];
  recent_activity: RecentActivityItem[];
}

export interface DuplicateInvoiceMatch {
  first_invoice_id: UUID;
  first_invoice_number: string;
  second_invoice_id: UUID;
  second_invoice_number: string;
  customer_id: UUID;
  customer_name: string;
  currency: string;
  total: DecimalString;
  issue_date: ISODate;
}

export interface DuplicateInvoiceInsightsResponse {
  matches: DuplicateInvoiceMatch[];
}

export interface CashFlowForecastPoint {
  month: ISODate;
  expected_receipts: DecimalString;
  overdue_receipts: DecimalString;
  invoice_count: number;
}

export interface CashFlowForecastResponse {
  currency: string;
  as_of_date: ISODate;
  months: CashFlowForecastPoint[];
}

export interface SlowPayerInsight {
  customer_id: UUID;
  customer_name: string;
  overdue_invoice_count: number;
  overdue_balance: DecimalString;
  longest_days_overdue: number;
}

export interface SlowPayerInsightsResponse {
  currency: string;
  as_of_date: ISODate;
  customers: SlowPayerInsight[];
}

export interface ExecutiveSummaryResponse {
  summary: string;
  key_findings: string[];
  risks: string[];
  recommended_actions: string[];
}

export interface FinancialAssistantQuestion {
  question: string;
  currency?: string;
}

export interface FinancialAssistantAnswer {
  answer: string;
  data_scope: string;
  caveat: string | null;
}
