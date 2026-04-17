import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { AuthService } from '../../../core/services/auth';
import { CATEGORY_OPTIONS } from '../../../core/models/category.model';
import {
  COUNTRY_OPTIONS,
  DATA_TYPE_OPTIONS,
  DEFAULT_NEWS_FILTERS,
  NewsFilters,
  SOURCE_OPTIONS
} from '../../../core/models/filter.model';
import { NewsArticle } from '../../../core/models/news.model';
import { NewsService } from '../../../core/services/news';
import { CategoryFilterComponent } from '../../../shared/components/category-filter/category-filter';
import { FooterComponent } from '../../../shared/components/footer/footer';
import { HeaderComponent } from '../../../shared/components/header/header';
import { HeroBannerComponent } from '../../../shared/components/hero-banner/hero-banner';
import { NewsCardComponent } from '../../../shared/components/news-card/news-card';

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [
    CommonModule,
    HeaderComponent,
    HeroBannerComponent,
    CategoryFilterComponent,
    NewsCardComponent,
    FooterComponent
  ],
  templateUrl: './home-page.html',
  styleUrl: './home-page.css'
})
export class HomePageComponent implements OnInit {
  private readonly newsService = inject(NewsService);
  private readonly authService = inject(AuthService);

  readonly categories = CATEGORY_OPTIONS;
  readonly countryOptions = COUNTRY_OPTIONS;
  readonly sourceOptions = SOURCE_OPTIONS;
  readonly dataTypeOptions = DATA_TYPE_OPTIONS;

  filters: NewsFilters = { ...DEFAULT_NEWS_FILTERS };
  visibleArticles: NewsArticle[] = [];
  loading = true;
  error = '';

  ngOnInit(): void {
    this.loadNews();
  }

  onFiltersChange(filters: NewsFilters): void {
    this.filters = { ...filters };
    this.loadNews();
  }

  trackByArticle(_: number, article: NewsArticle): string {
    return article.id;
  }

  private loadNews(): void {
    this.loading = true;
    this.error = '';

    const shouldUseHomepagePreset =
      this.filters.category === 'all' &&
      !this.filters.country &&
      !this.filters.source &&
      !this.filters.date &&
      !this.filters.dataType;

    const favoriteCategories = (this.authService.currentUser?.favorite_categories ?? []).filter(
      (category): category is Exclude<typeof this.filters.category, 'all'> => category !== 'all'
    );

    const request$ = shouldUseHomepagePreset
      ? this.newsService.loadHomeNews(favoriteCategories)
      : this.newsService.searchNews(this.filters);

    request$.subscribe({
      next: (articles) => {
        this.visibleArticles = [...articles].sort(
          (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime()
        );
        this.loading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.error = error.error?.detail || 'Unable to load news at the moment.';
        this.loading = false;
      }
    });
  }
}
