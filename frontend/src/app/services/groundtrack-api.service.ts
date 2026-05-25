import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ConflictReport, GroundStation, PassWindow, SatellitePosition, Stats } from '../models/groundtrack.models';

@Injectable({ providedIn: 'root' })
export class GroundtrackApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  passes(filters: { groundStationId?: number; satelliteId?: number; minElevation?: number } = {}): Observable<PassWindow[]> {
    let params = new HttpParams();
    if (filters.groundStationId) params = params.set('ground_station_id', filters.groundStationId);
    if (filters.satelliteId) params = params.set('satellite_id', filters.satelliteId);
    if (filters.minElevation) params = params.set('min_elevation', filters.minElevation);
    return this.http.get<PassWindow[]>(`${this.baseUrl}/passes`, { params });
  }

  conflicts(): Observable<ConflictReport[]> {
    return this.http.get<ConflictReport[]>(`${this.baseUrl}/conflicts`);
  }

  stats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.baseUrl}/stats`);
  }

  groundStations(): Observable<GroundStation[]> {
    return this.http.get<GroundStation[]>(`${this.baseUrl}/groundstations`);
  }

  positions(): Observable<SatellitePosition[]> {
    return this.http.get<SatellitePosition[]>(`${this.baseUrl}/positions`);
  }

  rerunConflict(conflictId: number): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/conflicts/${conflictId}/resolve`, {});
  }

  replay(date: string, groundStationId?: number): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/replay`, { date, ground_station_id: groundStationId });
  }
}
