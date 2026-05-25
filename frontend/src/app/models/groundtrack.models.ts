export interface PassWindow {
  id: number;
  satellite_id: number;
  satellite_name: string;
  ground_station_id: number;
  ground_station_name: string;
  aos_time: string;
  los_time: string;
  max_elevation_deg: number;
  duration_seconds: number;
  status: 'scheduled' | 'conflict' | 'deprioritized';
  mission_priority: number;
  satellite_type: string;
}

export interface ConflictReport {
  id: number;
  pass_id_winner: number;
  pass_id_loser: number;
  winner_satellite: string;
  loser_satellite: string;
  ground_station: string;
  conflict_reason: string;
  resolution_reason: string;
  alternative_window: string | null;
  resolved_at: string;
}

export interface GroundStation {
  id: number;
  name: string;
  lat: number;
  lon: number;
  elevation_m: number;
  created_at: string;
}

export interface SatellitePosition {
  satellite_id: number;
  name: string;
  lat: number;
  lon: number;
}

export interface Stats {
  total_passes_today: number;
  conflicts_detected: number;
  conflicts_resolved: number;
  resolution_rate_percent: number;
  last_pipeline_seconds: number | null;
}
