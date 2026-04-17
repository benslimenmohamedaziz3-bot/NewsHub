export interface CategoryApiOption {
  label: string;
  value: string;
  supported_sources: string[];
}

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  favorite_categories: string[];
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  favorite_categories: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
