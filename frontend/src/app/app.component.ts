import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="shell-header">
      <div>
        <strong>GroundTrack</strong>
        <span>Pass Planning & Conflict Simulator</span>
      </div>
      <nav>
        <a routerLink="/timeline" routerLinkActive="active">Timeline</a>
        <a routerLink="/conflicts" routerLinkActive="active">Conflicts</a>
        <a routerLink="/map" routerLinkActive="active">Stations</a>
      </nav>
    </header>
    <main>
      <router-outlet />
    </main>
  `
})
export class AppComponent {}
