export type RecordValue = string | number | boolean | null | undefined | Record<string, unknown> | unknown[];
export type DataRecord = Record<string, RecordValue>;

export type Paginated<T> = {
  items: T[];
  pagination: { page: number; page_size: number; total: number; pages: number };
};

export type OverviewResponse = {
  kpis: Record<string, number | string>;
  series: Record<string, DataRecord[]>;
  filters?: Record<string, string | null>;
};

export type Alert = DataRecord & {
  alert_id: string;
  transaction_id: string;
  customer_id: string;
  risk_score: number;
  risk_level: string;
  alert_status: string;
};

export type Transaction = DataRecord & {
  transaction_id: string;
  sender_customer_id: string;
  amount: number;
  timestamp: string;
};

export type ModelReport = {
  metrics: Record<string, DataRecord>;
  class_distribution: DataRecord;
  time_split?: DataRecord;
  threshold_analysis?: DataRecord[];
  precision_recall_curve?: DataRecord;
  feature_importance?: DataRecord[];
  model_limitations?: string[];
};
