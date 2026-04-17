import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-register-form',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './register-form.html',
  styleUrls: ['./register-form.css']
})
export class RegisterForm {
  form = {
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  };

  errorMessage = '';
  showPassword = false;

  @Output() nextStep = new EventEmitter<{ full_name: string; email: string; password: string }>();

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (this.form.password !== this.form.confirmPassword) {
      this.errorMessage = 'Passwords do not match.';
      return;
    }

    this.errorMessage = '';
    this.nextStep.emit({
      full_name: this.form.name,
      email: this.form.email,
      password: this.form.password
    });
  }
}
