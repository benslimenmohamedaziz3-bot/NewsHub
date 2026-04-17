export interface ChatbotMessage {
  role: 'user' | 'assistant';
  text: string;
  mode?: 'article_grounded' | 'general_assistant';
  engine?: string;
}

export interface ChatbotArticleContext {
  articleUrl: string;
  articleTitle: string;
  articleDescription?: string;
  articleContent?: string;
}

export interface ChatbotAskRequest extends ChatbotArticleContext {
  question: string;
  conversation?: ChatbotMessage[];
}

export interface ChatbotAskResponse {
  answer: string;
  extractedTitle: string;
  sourceUrl: string;
  sourceExcerpt: string[];
  warning?: string;
  sourceStatus: 'original_page' | 'fallback_article_data' | 'not_used';
  answerMode: 'article_grounded' | 'general_assistant';
  answerEngine: string;
  cached?: boolean;
}
