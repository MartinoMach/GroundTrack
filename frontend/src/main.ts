import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, Routes } from '@angular/router';
import { AppComponent } from './app/app.component';
import { PassTimelineComponent } from './app/pass-timeline/pass-timeline.component';
import { ConflictDashboardComponent } from './app/conflict-dashboard/conflict-dashboard.component';
import { StationMapComponent } from './app/station-map/station-map.component';

const routes: Routes = [
  { path: '', redirectTo: 'timeline', pathMatch: 'full' },
  { path: 'timeline', component: PassTimelineComponent },
  { path: 'conflicts', component: ConflictDashboardComponent },
  { path: 'map', component: StationMapComponent }
];

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(), provideRouter(routes)]
}).catch((err) => console.error(err));
