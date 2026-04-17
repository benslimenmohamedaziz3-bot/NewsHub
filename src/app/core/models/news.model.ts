import { NewsCategory } from './category.model';

export interface NewsArticle {
  id: string;
  title: string;
  description: string;
  content: string;
  imageUrl: string;
  sourceName: string;
  publishedAt: string;
  readTime: number;
  url: string;
  category: Exclude<NewsCategory, 'all'>;
}

export type NewsStore = Record<Exclude<NewsCategory, 'all'>, NewsArticle[]>;

export interface NewsFeedResponse {
  articles: NewsArticle[];
  mode: 'general' | 'personalized' | 'admin_cache';
  message?: string | null;
}

export interface AdminNewsCacheResponse {
  categories: Record<Exclude<NewsCategory, 'all'>, NewsArticle[]>;
  total_articles: number;
}
