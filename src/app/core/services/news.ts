import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, forkJoin, map, of, shareReplay, catchError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NewsCategory } from '../models/category.model';
import { NewsFilters } from '../models/filter.model';
import { NewsApiArticle, NewsApiResponse, NewsArticle, NewsStore } from '../models/news.model';

type RealCategory = Exclude<NewsCategory, 'all'>;

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

  private newsStore$?: Observable<NewsStore>;

  getCategories(): RealCategory[] {
    return [...this.categories];
  }

  getAllNews(): Observable<NewsStore> {
    if (!this.newsStore$) {
      const requests = this.categories.reduce((acc, category) => {
        acc[category] = this.getNewsByCategory(category);
        return acc;
      }, {} as Record<RealCategory, Observable<NewsArticle[]>>);

      this.newsStore$ = forkJoin(requests).pipe(shareReplay(1));
    }

    return this.newsStore$;
  }

  getArticleById(articleId: string, category?: RealCategory): Observable<NewsArticle | null> {
    if (category) {
      return this.getNewsByCategory(category).pipe(
        map((articles) => articles.find((article) => article.id === articleId) || null)
      );
    }

    return this.getAllNews().pipe(
      map((store) => {
        const allArticles = [
          ...store.technology,
          ...store.business,
          ...store.politics,
          ...store.science,
          ...store.entertainment,
          ...store.sports,
          ...store.health
        ];

        return allArticles.find((article) => article.id === articleId) || null;
      })
    );
  }

  getNewsByCategory(category: RealCategory): Observable<NewsArticle[]> {
    const params = new HttpParams()
      .set('apikey', environment.newsApiKey)
      .set('category', category)
      .set('language', 'en')
      .set('size', '5');

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
      .set('size', '10');

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
      map((articles) => this.dedupeArticles(articles))
    );
  }

  private mapArticle(item: NewsApiArticle, category: RealCategory, index: number): NewsArticle {
    const title = item.title?.trim() || 'Untitled article';
    const rawDescription =
      item.description?.trim() || 'No description available for this article.';
    const content = this.resolveReadableContent(item.content, rawDescription);
    const id = item.article_id || `${category}-${index}-${title}`;

    return {
      id,
      title,
      description: this.truncateText(rawDescription, 120),
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

  private resolveReadableContent(content: string | undefined, fallbackDescription: string): string {
    const safeContent = content?.trim();

    if (!safeContent) {
      return fallbackDescription;
    }

    const blockedPhrases = [
      'available only in paid plans',
      'available in paid plans',
      'only available in paid plans',
      'disponible uniquement dans les forfaits payants',
      'premium subscribers',
      'upgrade to premium',
      'subscribe to continue reading'
    ];

    const normalized = safeContent.toLowerCase();
    const hasBlockedPhrase = blockedPhrases.some((phrase) => normalized.includes(phrase));

    return hasBlockedPhrase ? fallbackDescription : safeContent;
  }

  private truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) {
      return text;
    }

    return `${text.slice(0, maxLength).trimEnd()}...`;
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
}