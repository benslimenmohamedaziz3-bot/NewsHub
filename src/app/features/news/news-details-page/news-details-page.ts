import { DatePipe, NgIf, TitleCasePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NewsCategory } from '../../../core/models/category.model';
import { NewsArticle } from '../../../core/models/news.model';
import { NewsService } from '../../../core/services/news';
import { HeaderComponent } from '../../../shared/components/header/header';

@Component({
  selector: 'app-news-details-page',
  standalone: true,
  imports: [DatePipe, HeaderComponent, NgIf, RouterLink, TitleCasePipe],
  templateUrl: './news-details-page.html',
  styleUrl: './news-details-page.css'
})
export class NewsDetailsPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly newsService = inject(NewsService);

  article: NewsArticle | null = null;
  loading = true;
  error = '';

  ngOnInit(): void {
    const articleId = this.route.snapshot.paramMap.get('id');
    const categoryParam = this.route.snapshot.queryParamMap.get('category') as
      | Exclude<NewsCategory, 'all'>
      | null;
    const stateArticle = (window.history.state?.article as NewsArticle | undefined) ?? null;

    if (!articleId) {
      this.error = 'Article not found.';
      this.loading = false;
      return;
    }

    if (stateArticle && stateArticle.id === articleId) {
      this.article = stateArticle;
      this.loading = false;
      return;
    }

    this.newsService.getArticleById(articleId, categoryParam ?? undefined).subscribe({
      next: (article) => {
        this.article = article;
        this.error = article ? '' : 'Article not found.';
        this.loading = false;
      },
      error: () => {
        this.error = 'Unable to load article details right now.';
        this.loading = false;
      }
    });
  }

  openAskAi(): void {
    if (!this.article) {
      return;
    }

    void this.router.navigate(['/details', this.article.id, 'ask-ai'], {
      queryParams: { category: this.article.category },
      state: { article: this.article }
    });
  }
}
