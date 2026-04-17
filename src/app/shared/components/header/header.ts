import { DOCUMENT } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthUser } from '../../../core/models/auth.model';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './header.html',
  styleUrl: './header.css'
})
export class HeaderComponent implements OnInit {
  private readonly document = inject(DOCUMENT);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly storageKey = 'f-news-theme';

  isDarkMode = false;
  currentUser: AuthUser | null = null;

  ngOnInit(): void {
    const storedTheme = localStorage.getItem(this.storageKey);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const resolvedTheme = storedTheme ?? (prefersDark ? 'dark' : 'light');

    this.isDarkMode = resolvedTheme === 'dark';
    this.applyTheme();
    this.currentUser = this.authService.currentUser;
    this.authService.currentUser$.subscribe((user) => (this.currentUser = user));
  }

  toggleTheme(): void {
    this.isDarkMode = !this.isDarkMode;
    this.applyTheme();
    localStorage.setItem(this.storageKey, this.isDarkMode ? 'dark' : 'light');
  }

  logout(): void {
    this.authService.logout();
    void this.router.navigateByUrl('/');
  }

  private applyTheme(): void {
    this.document.documentElement.setAttribute('data-theme', this.isDarkMode ? 'dark' : 'light');
  }
}
