export interface AgentReport {
  id?: string;
  file: string;
  engine: string;
  manufacturing_assumptions?: {
    mode: string;
    audience_summary: string;
    alloy: string;
    annual_volume: number;
    sliders: number;
    port_cost: number;
    confidence: number;
    location: string;
    signals: Record<string, number>;
    decisions: {
      label: string;
      value: string;
      reason: string;
    }[];
    open_data_sources: string[];
  };
  technical_matrix: {
    volume: number;
    surface_area: number;
    projected_area: number;
    preview_mesh: string;
    dimensions?: {
      x?: number;
      y?: number;
      z?: number;
    };
    validation?: {
      is_manifold?: boolean;
      integrity_score?: number;
    };
    topology?: {
      solids?: number;
      faces?: number;
      edges?: number;
      vertices?: number;
    };
  };
  cost_estimation: {
    material_cost: number;
    machine_cost: number;
    amortization: number;
    port_cost: number;
    total_unit_cost: number;
    per_part_cost?: number;
    unit_cost_inr: number;
    weight_g: number;
    tooling_estimate: number;
    material_price_basis?: string;
    fluctuation_range: {
      min: number;
      max: number;
      percent: number;
    };
    machine_details: {
      selected_machine: number;
      required_tonnage: number;
      cycle_time_s: number;
      shots_per_hour: number;
    };
  };
  market_snapshot: {
    metal?: string;
    spot_price_usd: number;
    live_spot_price_usd?: number | null;
    reference_price_usd?: number | null;
    location_adjusted_price_usd?: number;
    live_location_adjusted_price_usd?: number | null;
    reference_location_adjusted_price_usd?: number | null;
    regional_premium_percent?: number;
    estimated_freight_usd_per_kg?: number;
    price_model?: string;
    is_live_metal_price?: boolean;
    exchange_rate: number;
    price_source?: string;
    price_status?: string;
    price_as_of?: string;
    pricing_note?: string;
    provider_error?: string;
    location?: string;
    location_geodata?: {
      city?: string;
      country?: string;
      lat?: number | null;
      lon?: number | null;
      currency?: string;
    };
    location_price_table?: {
      name: string;
      city: string;
      country: string;
      lat: number | null;
      lon: number | null;
      location_adjusted_usd_per_kg: number;
      regional_premium_percent?: number;
      estimated_freight_usd_per_kg?: number;
      is_live_price: boolean;
      method?: string;
    }[];
  };
  ai_insight?: {
    status: string;
    provider: string;
    model?: string;
    summary: string;
    key_drivers: string[];
    risk_notes: string[];
    recommendation: string;
    note?: string;
    sources: {
      provider: string;
      title: string;
      url: string;
      snippet: string;
    }[];
  };
}
