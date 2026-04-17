import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ChatbotAskRequest, ChatbotAskResponse } from '../models/chatbot.model';

@Injectable({
  providedIn: 'root'
})
export class ChatbotService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.backendBaseUrl}/chatbot/ask`;

  askQuestion(payload: ChatbotAskRequest): Observable<ChatbotAskResponse> {
    return this.http.post<ChatbotAskResponse>(this.apiUrl, payload);
  }
}
