import { NgClass, NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import {
  ChatbotArticleContext,
  ChatbotAskResponse,
  ChatbotMessage
} from '../../../core/models/chatbot.model';
import { NewsArticle } from '../../../core/models/news.model';
import { ChatbotService } from '../../../core/services/chatbot';
import { NewsService } from '../../../core/services/news';
import { HeaderComponent } from '../../../shared/components/header/header';

@Component({
  selector: 'app-news-chatbot-page',
  standalone: true,
  imports: [FormsModule, HeaderComponent, NgClass, NgFor, NgIf, RouterLink],
  templateUrl: './news-chatbot-page.html',
  styleUrl: './news-chatbot-page.css'
})
export class NewsChatbotPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly newsService = inject(NewsService);
  private readonly chatbotService = inject(ChatbotService);

  article: NewsArticle | null = null;
  question = '';
  loadingArticle = true;
  sending = false;
  error = '';
  warning = '';
  extractedTitle = '';
  sourceExcerpt: string[] = [];
  answerMode: ChatbotAskResponse['answerMode'] = 'article_grounded';
  answerEngine = '';
  messages: ChatbotMessage[] = [
    {
      role: 'assistant',
      text:
        'Ask me anything. If your question is about this story, I will ground the answer in the article.'
    }
  ];

  ngOnInit(): void {
    const articleId = this.route.snapshot.paramMap.get('id');
    const categoryParam = this.route.snapshot.queryParamMap.get('category');
    const stateArticle = (window.history.state?.article as NewsArticle | undefined) ?? null;

    if (!articleId) {
      this.error = 'Article not found.';
      this.loadingArticle = false;
      return;
    }

    if (stateArticle && stateArticle.id === articleId) {
      this.article = stateArticle;
      this.loadingArticle = false;
      return;
    }

    this.newsService.getArticleById(articleId, categoryParam as NewsArticle['category'] | undefined).subscribe({
      next: (article) => {
        this.article = article;
        this.error = article ? '' : 'Article not found.';
        this.loadingArticle = false;
      },
      error: () => {
        this.error = 'Unable to load the article for the AI assistant.';
        this.loadingArticle = false;
      }
    });
  }

  askQuestion(): void {
    const trimmedQuestion = this.question.trim();

    if (!trimmedQuestion || !this.article || this.sending) {
      return;
    }

    const payload: ChatbotArticleContext & { question: string; conversation: ChatbotMessage[] } = {
      question: trimmedQuestion,
      articleUrl: this.article.url,
      articleTitle: this.article.title,
      articleDescription: this.article.description,
      articleContent: this.article.content,
      conversation: this.messages.slice(-6)
    };

    this.error = '';
    this.warning = '';
    this.messages = [...this.messages, { role: 'user', text: trimmedQuestion }];
    this.question = '';
    this.sending = true;

    this.chatbotService
      .askQuestion(payload)
      .pipe(finalize(() => (this.sending = false)))
      .subscribe({
        next: (response) => {
          this.extractedTitle = response.extractedTitle;
          this.sourceExcerpt = response.answerMode === 'article_grounded' ? response.sourceExcerpt : [];
          this.warning = response.warning ?? '';
          this.answerMode = response.answerMode;
          this.answerEngine = response.answerEngine;
          this.messages = [
            ...this.messages,
            {
              role: 'assistant',
              text: response.answer,
              mode: response.answerMode,
              engine: response.answerEngine
            }
          ];
        },
        error: (errorResponse) => {
          this.error =
            errorResponse?.error?.detail ||
            'The assistant could not answer right now. Please try again in a moment.';
          this.messages = [
            ...this.messages,
            {
              role: 'assistant',
              text:
                'I could not answer this question right now. Please try again in a moment or open the original article.'
            }
          ];
        }
      });
  }

  get composerHint(): string {
    if (this.sending) {
      return 'Thinking...';
    }

    if (this.answerMode === 'general_assistant') {
      return this.answerEngine
        ? `General assistant reply via ${this.answerEngine}. Ask about the story to ground the next answer in the article.`
        : 'General assistant reply. Ask about the story to ground the next answer in the article.';
    }

    if (this.warning) {
      return this.warning;
    }

    return this.answerEngine
      ? `Story questions are grounded in the article with ${this.answerEngine}.`
      : 'Story questions are grounded in the article.';
  }

  goBackToArticle(): void {
    if (!this.article) {
      void this.router.navigateByUrl('/');
      return;
    }

    void this.router.navigate(['/details', this.article.id], {
      queryParams: { category: this.article.category },
      state: { article: this.article }
    });
  }
}
