import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ConflictReport, Stats } from '../models/groundtrack.models';
import { GroundtrackApiService } from '../services/groundtrack-api.service';

@Component({
  selector: 'app-conflict-dashboard',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './conflict-dashboard.component.html',
  styleUrl: './conflict-dashboard.component.css'
})
export class ConflictDashboardComponent implements OnInit {
  conflicts: ConflictReport[] = [];
  stats?: Stats;
  resolvingId?: number;

  constructor(private readonly api: GroundtrackApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.api.conflicts().subscribe((conflicts) => (this.conflicts = conflicts));
    this.api.stats().subscribe((stats) => (this.stats = stats));
  }

  rerun(conflict: ConflictReport): void {
    this.resolvingId = conflict.id;
    this.api.rerunConflict(conflict.id).subscribe(() => {
      this.resolvingId = undefined;
      this.load();
    });
  }
}
