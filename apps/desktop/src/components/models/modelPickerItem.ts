export interface ModelPickerItem {
  id: string;
  display_name: string;
  price_hint: string;
  price_updated_at?: string | null;
  estimate_credits?: number | null;
  supports_vision?: boolean;
  supports_tools?: boolean;
}
