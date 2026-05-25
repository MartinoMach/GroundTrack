import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import * as L from 'leaflet';
import { Subscription, interval, startWith, switchMap } from 'rxjs';
import { GroundStation, SatellitePosition } from '../models/groundtrack.models';
import { GroundtrackApiService } from '../services/groundtrack-api.service';

@Component({
  selector: 'app-station-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './station-map.component.html',
  styleUrl: './station-map.component.css'
})
export class StationMapComponent implements AfterViewInit, OnDestroy {
  stations: GroundStation[] = [];
  private map?: L.Map;
  private positionLayer = L.layerGroup();
  private sub?: Subscription;

  constructor(private readonly api: GroundtrackApiService, private readonly router: Router) {}

  ngAfterViewInit(): void {
    this.map = L.map('station-map', { worldCopyJump: true }).setView([18, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(this.map);
    this.positionLayer.addTo(this.map);

    this.api.groundStations().subscribe((stations) => {
      this.stations = stations;
      stations.forEach((station) => this.addStationMarker(station));
    });

    this.sub = interval(30_000)
      .pipe(startWith(0), switchMap(() => this.api.positions()))
      .subscribe((positions) => this.renderPositions(positions));
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.map?.remove();
  }

  private addStationMarker(station: GroundStation): void {
    if (!this.map) return;
    L.circleMarker([station.lat, station.lon], {
      radius: 7,
      color: '#37d67a',
      fillColor: '#37d67a',
      fillOpacity: 0.95,
      weight: 2
    })
      .addTo(this.map)
      .bindPopup(`<strong>${station.name}</strong><br>${station.lat.toFixed(2)}, ${station.lon.toFixed(2)}`)
      .on('click', () => this.router.navigate(['/timeline'], { queryParams: { station: station.id } }));
  }

  private renderPositions(positions: SatellitePosition[]): void {
    this.positionLayer.clearLayers();
    positions.slice(0, 80).forEach((position) => {
      L.circleMarker([position.lat, position.lon], {
        radius: 4,
        color: '#5aa7ff',
        fillColor: '#5aa7ff',
        fillOpacity: 0.85,
        weight: 1
      })
        .bindTooltip(position.name)
        .addTo(this.positionLayer);
    });
  }
}
