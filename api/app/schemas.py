from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class CategoryOption(BaseModel):
    label: str
    value: str
    supported_sources: list[str]


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr


class RegisterRequest(UserBase):
    password: str = Field(min_length=6, max_length=128)
    favorite_categories: list[str] = Field(min_length=1, max_length=3)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    favorite_categories: list[str]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class NewsArticle(BaseModel):
    id: str
    title: str
    description: str
    content: str
    imageUrl: str
    sourceName: str
    publishedAt: str
    readTime: int
    url: str
    category: str


class NewsFeedResponse(BaseModel):
    articles: list[NewsArticle]
    mode: Literal["general", "personalized", "admin_cache"]
    message: str | None = None


class AdminNewsCacheResponse(BaseModel):
    categories: dict[str, list[NewsArticle]]
    total_articles: int


class ChatbotQuestion(BaseModel):
    question: str
    articleUrl: str
    articleTitle: str
    articleDescription: str | None = None
    articleContent: str | None = None
    conversation: list[dict[str, str]] = Field(default_factory=list)


class ChatbotResponse(BaseModel):
    answer: str
    extractedTitle: str
    sourceUrl: str
    sourceExcerpt: list[str]
    warning: str | None = None
    sourceStatus: Literal["original_page", "fallback_article_data", "not_used"]
    answerMode: Literal["article_grounded", "general_assistant"]
    answerEngine: str
    cached: bool = False
