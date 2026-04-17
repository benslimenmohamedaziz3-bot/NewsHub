import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AuthResponse,
  AuthUser,
  CategoryApiOption,
  LoginPayload,
  RegisterPayload
} from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenKey = 'newshub-token';
  private readonly userKey = 'newshub-user';
  private readonly apiBaseUrl = environment.backendBaseUrl;

  private readonly currentUserSubject = new BehaviorSubject<AuthUser | null>(this.readStoredUser());
  readonly currentUser$ = this.currentUserSubject.asObservable();

  get currentUser(): AuthUser | null {
    return this.currentUserSubject.value;
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem(this.tokenKey) && !!this.currentUser;
  }

  getCategories(): Observable<CategoryApiOption[]> {
    return this.http.get<CategoryApiOption[]>(`${this.apiBaseUrl}/categories`);
  }

  register(payload: RegisterPayload): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.apiBaseUrl}/auth/register`, payload)
      .pipe(tap((response) => this.persistAuth(response)));
  }

  login(payload: LoginPayload): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.apiBaseUrl}/auth/login`, payload)
      .pipe(tap((response) => this.persistAuth(response)));
  }

  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUserSubject.next(null);
  }

  private persistAuth(response: AuthResponse): void {
    localStorage.setItem(this.tokenKey, response.access_token);
    localStorage.setItem(this.userKey, JSON.stringify(response.user));
    this.currentUserSubject.next(response.user);
  }

  private readStoredUser(): AuthUser | null {
    const rawUser = localStorage.getItem(this.userKey);

    if (!rawUser) {
      return null;
    }

    try {
      return JSON.parse(rawUser) as AuthUser;
    } catch {
      localStorage.removeItem(this.userKey);
      return null;
    }
  }
}
