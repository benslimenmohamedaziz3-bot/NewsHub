import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { CategoryApiOption } from '../../../core/models/auth.model';
import { AuthService } from '../../../core/services/auth';
import { InterestsForm } from '../interests-form/interests-form';
import { LoginForm } from '../login-form/login-form';
import { RegisterForm } from '../register-form/register-form';

@Component({
  selector: 'app-auth-card',
  standalone: true,
  imports: [CommonModule, RegisterForm, InterestsForm, LoginForm],
  templateUrl: './auth-card.html',
  styleUrls: ['./auth-card.css']
})
export class AuthCard implements OnInit {
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);

  step = 1;
  mode: 'login' | 'signup' = 'login';
  registrationData: { full_name: string; email: string; password: string } | null = null;
  isLoading = false;
  errorMessage = '';
  successUser: { full_name: string } | null = null;
  categories: CategoryApiOption[] = [];

  ngOnInit(): void {
    this.mode = this.router.url.includes('register') ? 'signup' : 'login';

    this.authService.getCategories().subscribe({
      next: (categories) => {
        this.categories = categories;
        this.cdr.detectChanges();
      }
    });
  }

  goToNextStep(data: { full_name: string; email: string; password: string }): void {
    this.registrationData = data;
    this.step = 2;
    this.cdr.detectChanges();
  }

  finishSignup(selectedCategories: string[]): void {
    if (!this.registrationData) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.authService
      .register({
        ...this.registrationData,
        favorite_categories: selectedCategories
      })
      .subscribe({
        next: (response) => {
          this.isLoading = false;
          this.successUser = response.user;
          this.step = 3;
          this.cdr.detectChanges();
          setTimeout(() => void this.router.navigateByUrl('/'), 1000);
        },
        error: (error) => {
          this.isLoading = false;
          this.errorMessage = error.error?.detail || 'An error occurred during signup.';
          this.cdr.detectChanges();
        }
      });
  }

  onLoginSuccess(user: { full_name: string }): void {
    this.successUser = user;
    this.step = 3;
    this.cdr.detectChanges();
    setTimeout(() => void this.router.navigateByUrl('/'), 1000);
  }

  switchToSignup(): void {
    void this.router.navigate(['/register']);
    this.mode = 'signup';
    this.step = 1;
    this.errorMessage = '';
  }

  switchToLogin(): void {
    void this.router.navigate(['/login']);
    this.mode = 'login';
    this.step = 1;
    this.errorMessage = '';
  }
}
