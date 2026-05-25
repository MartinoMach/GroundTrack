import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Subscription, interval, startWith, switchMap } from 'rxjs';
import { PassWindow } from '../models/groundtrack.models';
import { GroundtrackApiService } from '../services/groundtrack-api.service';

@Component({
  selector: 'app-pass-timeline',
  standalone: true,
  imports: [CommonModule, DatePipe, DecimalPipe],
  templateUrl: './pass-timeline.component.html',
  styleUrl: './pass-timeline.component.css'
})
export class PassTimelineComponent implements OnInit, OnDestroy {
  passes: PassWindow[] = [];
  selected: PassWindow | null = null;
  selectedStationId?: number;
  private sub?: Subscription;
  readonly windowStart = new Date();

  constructor(private readonly api: GroundtrackApiService, private readonly route: ActivatedRoute) {}

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      const station = params.get('station');
      this.selectedStationId = station ? Number(station) : undefined;
      this.startRefresh();
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  stations(): string[] {
    return [...new Set(this.passes.map((p) => p.ground_station_name))];
  }

  passesForStation(station: string): PassWindow[] {
    return this.passes.filter((p) => p.ground_station_name === station);
  }

  left(passWindow: PassWindow): number {
    const start = this.windowStart.getTime();
    const aos = new Date(passWindow.aos_time).getTime();
    return Math.max(0, ((aos - start) / 86_400_000) * 100);
  }

  width(passWindow: PassWindow): number {
    return Math.max(0.6, (passWindow.duration_seconds / 86_400) * 100);
  }

  private startRefresh(): void {
    this.sub?.unsubscribe();
    this.sub = interval(60_000)
      .pipe(
        startWith(0),
        switchMap(() => this.api.passes({ groundStationId: this.selectedStationId }))
      )
      .subscribe((passes) => {
        this.passes = passes;
        if (this.selected) {
          this.selected = passes.find((p) => p.id === this.selected?.id) ?? null;
        }
      });
  }
}
