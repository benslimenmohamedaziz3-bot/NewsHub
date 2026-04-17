import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, forkJoin, map, of } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NewsCategory } from '../models/category.model';
import { NewsFilters } from '../models/filter.model';
import { NewsArticle } from '../models/news.model';

type RealCategory = Exclude<NewsCategory, 'all'>;

interface NewsApiResponse {
  status: string;
  totalResults: number;
  results: NewsApiArticle[];
  nextPage?: string;
}

interface NewsApiArticle {
  article_id?: string;
  title?: string;
  link?: string;
  description?: string;
  content?: string;
  pubDate?: string;
  image_url?: string;
  source_id?: string;
  source_name?: string;
  category?: string[];
  country?: string[];
  language?: string;
}

@Injectable({
  providedIn: 'root'
})
export class NewsService {
  private readonly http = inject(HttpClient);
  private readonly categories: RealCategory[] = [
    'technology',
    'business',
    'politics',
    'science',
    'entertainment',
    'sports',
    'health'
  ];
  private readonly articleCache = new Map<string, NewsArticle>();

  getCategories(): RealCategory[] {
    return [...this.categories];
  }

  getArticleById(articleId: string, category?: RealCategory): Observable<NewsArticle | null> {
    const cachedArticle = this.articleCache.get(articleId);
    if (cachedArticle) {
      return of(cachedArticle);
    }

    if (!category) {
      return of(null);
    }

    return this.searchNews({
      category,
      country: '',
      source: '',
      date: '',
      dataType: ''
    }).pipe(map((articles) => articles.find((article) => article.id === articleId) || null));
  }

  loadHomeNews(favoriteCategories: RealCategory[] = []): Observable<NewsArticle[]> {
    const targetCategories = favoriteCategories.length ? favoriteCategories : this.categories;
    const perCategoryLimit = favoriteCategories.length ? 10 : 5;

    const requests = targetCategories.map((category) =>
      this.getNewsByCategory(category, perCategoryLimit)
    );

    return forkJoin(requests).pipe(
      map((groups) => groups.flat()),
      map((articles) => this.dedupeArticles(articles)),
      map((articles) =>
        [...articles].sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime())
      ),
      map((articles) => this.cacheArticles(articles))
    );
  }

  getNewsByCategory(category: RealCategory, size = 5): Observable<NewsArticle[]> {
    const params = new HttpParams()
      .set('apikey', environment.newsApiKey)
      .set('language', 'en')
      .set('category', category)
      .set('size', String(size));

    return this.http.get<NewsApiResponse>(environment.apiBaseUrl, { params }).pipe(
      map((response) =>
        (response.results ?? []).map((item, index) => this.mapArticle(item, category, index))
      ),
      map((articles) => articles.filter((article) => !!article.title)),
      map((articles) => this.dedupeArticles(articles)),
      catchError((error) => {
        console.error(`Failed to load ${category} news`, error);
        return of([]);
      })
    );
  }

  searchNews(filters: NewsFilters): Observable<NewsArticle[]> {
    let params = new HttpParams()
      .set('apikey', environment.newsApiKey)
      .set('language', 'en')
      .set('size', '12');

    if (filters.category !== 'all') {
      params = params.set('category', filters.category);
    }

    if (filters.country) {
      params = params.set('country', filters.country);
    }

    if (filters.source) {
      params = params.set('domainurl', filters.source);
    }

    if (filters.date) {
      params = params.set('from_date', filters.date).set('to_date', filters.date);
    }

    if (filters.dataType) {
      params = params.set('datatype', filters.dataType);
    }

    return this.http.get<NewsApiResponse>(environment.apiBaseUrl, { params }).pipe(
      map((response) => {
        const fallbackCategory: RealCategory =
          filters.category === 'all' ? 'technology' : filters.category;

        return (response.results ?? []).map((item, index) =>
          this.mapArticle(item, this.resolveCategory(item.category, fallbackCategory), index)
        );
      }),
      map((articles) => articles.filter((article) => !!article.title)),
      map((articles) => this.dedupeArticles(articles)),
      map((articles) => this.cacheArticles(articles)),
      catchError((error) => {
        console.error('Failed to load news feed', error);
        return of([]);
      })
    );
  }

  private mapArticle(item: NewsApiArticle, category: RealCategory, index: number): NewsArticle {
    const title = this.stripHtmlTags(item.title?.trim() || 'Untitled article');
    const rawDescription = this.resolveReadableText(
      item.description?.trim(),
      item.content?.trim(),
      'No description available for this article.'
    );
    const content = this.resolveReadableText(item.content?.trim(), rawDescription, rawDescription);
    const id = item.article_id || `${category}-${index}-${title}`;

    return {
      id,
      title,
      description: this.truncateText(rawDescription, 160),
      content,
      imageUrl: item.image_url || this.getFallbackImage(category),
      sourceName: item.source_name || item.source_id || 'Unknown source',
      publishedAt: item.pubDate || new Date().toISOString(),
      readTime: this.estimateReadTime(content || rawDescription || title),
      url: item.link || '#',
      category
    };
  }

  private resolveCategory(
    apiCategories: string[] | undefined,
    fallbackCategory: RealCategory
  ): RealCategory {
    const firstCategory = apiCategories?.[0]?.toLowerCase();

    if (
      firstCategory === 'technology' ||
      firstCategory === 'business' ||
      firstCategory === 'politics' ||
      firstCategory === 'science' ||
      firstCategory === 'entertainment' ||
      firstCategory === 'sports' ||
      firstCategory === 'health'
    ) {
      return firstCategory;
    }

    return fallbackCategory;
  }

  private resolveReadableText(
    primary: string | undefined,
    fallback: string | undefined,
    defaultValue: string
  ): string {
    const primaryText = this.stripHtmlTags(primary || '');
    const fallbackText = this.stripHtmlTags(fallback || '');

    if (primaryText && !this.isPaidPlaceholder(primaryText)) {
      return primaryText;
    }

    if (fallbackText && !this.isPaidPlaceholder(fallbackText)) {
      return fallbackText;
    }

    return defaultValue;
  }

  private isPaidPlaceholder(text: string): boolean {
    const normalized = text.toLowerCase();
    return (
      normalized.includes('only available in paid plans') ||
      normalized.includes('available in paid plans') ||
      normalized.includes('premium subscribers') ||
      normalized.includes('subscribe to continue reading')
    );
  }

  private truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) {
      return text;
    }

    return `${text.slice(0, maxLength).trimEnd()}...`;
  }

  private stripHtmlTags(text: string): string {
    if (!text) {
      return '';
    }

    return text.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  }

  private dedupeArticles(articles: NewsArticle[]): NewsArticle[] {
    const uniqueMap = new Map<string, NewsArticle>();

    for (const article of articles) {
      const key = this.buildArticleKey(article);

      if (!uniqueMap.has(key)) {
        uniqueMap.set(key, article);
      }
    }

    return Array.from(uniqueMap.values());
  }

  private buildArticleKey(article: NewsArticle): string {
    const safeUrl = article.url && article.url !== '#' ? article.url.trim().toLowerCase() : '';
    const safeTitle = article.title.trim().toLowerCase();
    const safeSource = article.sourceName.trim().toLowerCase();

    return safeUrl || `${safeTitle}__${safeSource}`;
  }

  private estimateReadTime(text: string): number {
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    return Math.max(3, Math.ceil(words / 200));
  }

  private getFallbackImage(category: RealCategory): string {
    return `https://placehold.co/800x500?text=${category}`;
  }

  private cacheArticles(articles: NewsArticle[]): NewsArticle[] {
    articles.forEach((article) => this.articleCache.set(article.id, article));
    return articles;
  }
}
