from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import CATEGORY_SOURCE_MAP, SUPPORTED_CATEGORIES, SUPPORTED_SOURCES
from .database import Base, engine, get_db
from .models import FavoriteCategory, User
from .news_provider import fetch_admin_cache, fetch_favorite_news, fetch_general_feed, generate_chatbot_answer
from .schemas import (
    AdminNewsCacheResponse,
    AuthResponse,
    CategoryOption,
    ChatbotQuestion,
    ChatbotResponse,
    LoginRequest,
    NewsFeedResponse,
    RegisterRequest,
    UserResponse,
)
from .security import create_access_token, get_current_user, hash_password, verify_password

app = FastAPI(title="NewsHub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def serialize_user(user: User) -> UserResponse:
    favorites = [favorite.category for favorite in user.favorite_categories]
    return UserResponse(id=user.id, full_name=user.full_name, email=user.email, favorite_categories=favorites)


@app.get("/")
def read_root():
    return {"message": "NewsHub backend is running"}


@app.get("/categories", response_model=list[CategoryOption])
def list_categories():
    return [
        CategoryOption(
            label=category.title(),
            value=category,
            supported_sources=CATEGORY_SOURCE_MAP.get(category, []),
        )
        for category in SUPPORTED_CATEGORIES
    ]


@app.post("/auth/register", response_model=AuthResponse)
def register_user(data: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    normalized_categories = list(dict.fromkeys(data.favorite_categories))

    if len(normalized_categories) > 3:
        raise HTTPException(status_code=422, detail="You can choose at most 3 favorite categories.")
    if any(category not in SUPPORTED_CATEGORIES for category in normalized_categories):
        raise HTTPException(status_code=422, detail="One or more selected categories are not supported.")

    existing_user = db.scalar(select(User).where(User.email == data.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="This email is already registered.")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    user.favorite_categories = [FavoriteCategory(category=category) for category in normalized_categories]
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(access_token=create_access_token(user.id), user=serialize_user(user))


@app.post("/auth/login", response_model=AuthResponse)
def login_user(data: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return AuthResponse(access_token=create_access_token(user.id), user=serialize_user(user))


@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return serialize_user(current_user)


@app.get("/news/feed", response_model=NewsFeedResponse)
def get_news_feed(
    category: str = Query(default="all"),
    source: str | None = Query(default=None),
    country: str | None = Query(default=None),
    date: str | None = Query(default=None),
    data_type: str | None = Query(default=None, alias="dataType"),
    limit: int = Query(default=12, ge=1, le=40),
):
    if category != "all" and category not in SUPPORTED_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported category.")
    if source and source not in SUPPORTED_SOURCES:
        source = None

    try:
        articles = fetch_general_feed(category, limit, source, country, date, data_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch news from the provider right now.") from exc

    return NewsFeedResponse(articles=articles, mode="general")


@app.get("/news/personalized", response_model=NewsFeedResponse)
def get_personalized_news(current_user: Annotated[User, Depends(get_current_user)]):
    favorites = [favorite.category for favorite in current_user.favorite_categories]
    if not favorites:
        raise HTTPException(status_code=422, detail="No favorite categories found for this user.")

    try:
        articles = fetch_favorite_news(favorites, limit_per_category=7)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to load personalized news right now.") from exc

    return NewsFeedResponse(
        articles=articles,
        mode="personalized",
        message="Showing 7 stories for each of your favorite categories.",
    )


@app.post("/admin/cache-news", response_model=AdminNewsCacheResponse)
def cache_admin_news():
    try:
        cache = fetch_admin_cache(limit_per_category=5)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch admin category news right now.") from exc

    total_articles = sum(len(items) for items in cache.values())

    if total_articles == 0:
        raise HTTPException(
            status_code=502,
            detail=(
                "The backend could not reach the news provider or the provider returned no supported "
                "results. Check that the backend process has internet access to newsdata.io and that "
                "the API key is valid."
            ),
        )

    return AdminNewsCacheResponse(categories=cache, total_articles=total_articles)


@app.post("/chatbot/ask", response_model=ChatbotResponse)
def ask_chatbot(data: ChatbotQuestion):
    return ChatbotResponse(**generate_chatbot_answer(
        question=data.question,
        article_url=data.articleUrl,
        article_title=data.articleTitle,
        article_description=data.articleDescription,
        article_content=data.articleContent,
        conversation=data.conversation,
    ))
