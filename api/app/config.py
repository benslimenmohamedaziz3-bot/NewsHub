from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'newshub.db'}"

JWT_SECRET = "newshub-dev-secret"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24

NEWS_API_URL = "https://newsdata.io/api/1/news"
NEWS_API_KEY = "pub_9975d8337c2543ab88c675d41966143b"

SUPPORTED_CATEGORIES = [
    "technology",
    "business",
    "politics",
    "science",
    "entertainment",
    "sports",
    "health",
]

CATEGORY_SOURCE_MAP = {
    "technology": ["techcrunch.com", "cnbc.com", "reuters.com"],
    "business": ["reuters.com", "cnbc.com", "bbc.com"],
    "politics": ["bbc.com", "reuters.com", "cnn.com"],
    "science": ["bbc.com", "reuters.com"],
    "entertainment": ["theguardian.com", "bbc.com", "cnn.com"],
    "sports": ["bbc.com", "cnn.com", "reuters.com"],
    "health": ["bbc.com", "reuters.com", "cnn.com"],
}

SUPPORTED_SOURCES = sorted(
    {domain for domains in CATEGORY_SOURCE_MAP.values() for domain in domains}
)

OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen3:14b"
