import { NewsCategory } from './category.model';

export interface NewsApiResponse {
  status: string;
  totalResults: number;
  results: NewsApiArticle[];
  nextPage?: string;
}

export interface NewsApiArticle {
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