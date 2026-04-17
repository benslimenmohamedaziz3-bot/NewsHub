import { ChangeDetectorRef, Component, EventEmitter, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-login-form',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './login-form.html',
  styleUrls: ['./login-form.css']
})
export class LoginForm {
  private readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  form = {
    email: '',
    password: ''
  };

  errorMessage = '';
  showPassword = false;
  isLoading = false;

  @Output() loginSuccess = new EventEmitter<{ full_name: string }>();
  @Output() switchToSignup = new EventEmitter<void>();

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.authService.login(this.form).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.loginSuccess.emit(response.user);
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error.error?.detail || 'Invalid email or password.';
        this.cdr.detectChanges();
      }
    });
  }
}
