from collections import Counter
from html import unescape
import json
import math
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

import requests

from .config import CATEGORY_SOURCE_MAP, NEWS_API_KEY, NEWS_API_URL, OLLAMA_API_URL, OLLAMA_MODEL, SUPPORTED_CATEGORIES
from .schemas import NewsArticle

ARTICLE_CONTEXT_TTL_SECONDS = 60 * 20
CHAT_ANSWER_TTL_SECONDS = 60 * 10
CHATBOT_CACHE_VERSION = "v2"
article_context_cache: dict[str, tuple[float, dict]] = {}
chat_answer_cache: dict[str, tuple[float, dict]] = {}
ANSWER_MODE_ARTICLE = "article_grounded"
ANSWER_MODE_GENERAL = "general_assistant"
BLOCKED_CONTENT_PHRASES = [
    "available only in paid plans",
    "available in paid plans",
    "only available in paid plans",
    "premium subscribers",
    "upgrade to premium",
    "subscribe to continue reading",
]
GREETING_INPUTS = {"hi", "hello", "hey", "yo", "good morning", "good evening", "good afternoon"}
BOILERPLATE_TERMS = {
    "subscribe",
    "newsletter",
    "gift subscriptions",
    "customer service",
    "sign in",
    "sign out",
    "my account",
    "search",
    "keyword",
    "e-edition",
    "advertise",
    "corrections",
    "today's paper",
    "manage newsletters",
}
NON_ARTICLE_PATTERNS = [
    r"^\s*print\b",
    r"^\s*\d+\s*[\+\-\*/]\s*\d+",
    r"^\s*write code",
    r"^\s*run code",
    r"^\s*execute\b",
    r"^\s*generate code\b",
    r"^\s*tell me a joke",
]
FOLLOW_UP_PREFIXES = (
    "what about",
    "and ",
    "then ",
    "so ",
    "tell me more",
    "explain more",
    "can you explain more",
    "what does that mean",
    "why is that",
    "how so",
    "who is that",
    "who is he",
    "who is she",
    "when was that",
    "where was that",
)


def clean_text(raw_text: str) -> str:
    return re.sub(r"\s+", " ", unescape(raw_text)).strip()


def strip_html_tags(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]*>", "", text).replace("&nbsp;", " ").strip()


def is_blocked_placeholder(text: str | None) -> bool:
    if not text:
        return False
    normalized = strip_html_tags(text).lower()
    return any(phrase in normalized for phrase in BLOCKED_CONTENT_PHRASES)


def sanitize_article_text(primary_text: str | None, fallback_text: str | None = None) -> str:
    cleaned_primary = strip_html_tags((primary_text or "").strip())
    cleaned_fallback = strip_html_tags((fallback_text or "").strip())

    if cleaned_primary and not is_blocked_placeholder(cleaned_primary):
        return cleaned_primary
    if cleaned_fallback and not is_blocked_placeholder(cleaned_fallback):
        return cleaned_fallback
    return ""


def dedupe_text_chunks(chunks: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for chunk in chunks:
        normalized = chunk.strip().lower()
        if (
            not normalized
            or normalized in seen
            or is_blocked_placeholder(normalized)
            or is_boilerplate_chunk(normalized)
        ):
            continue
        seen.add(normalized)
        deduped.append(chunk.strip())

    return deduped


def truncate_text(text: str, max_length: int = 180) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length].rstrip()}..."


def estimate_read_time(text: str) -> int:
    words = len(text.split())
    return max(3, math.ceil(words / 180))


def build_article_key(item: NewsArticle) -> str:
    return item.url.lower().strip() or f"{item.title.lower().strip()}::{item.sourceName.lower().strip()}"


def dedupe_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    unique: dict[str, NewsArticle] = {}
    for article in articles:
        key = build_article_key(article)
        if key not in unique:
            unique[key] = article
    return list(unique.values())


def resolve_domains(category: str, requested_source: str | None) -> list[str]:
    supported = CATEGORY_SOURCE_MAP.get(category, [])
    if requested_source and requested_source in supported:
        return [requested_source]
    return supported[:2] if supported else []


def map_article(item: dict, category: str, index: int) -> NewsArticle:
    title = strip_html_tags((item.get("title") or "Untitled article").strip())
    description = sanitize_article_text(
        item.get("description"),
        item.get("content") or "No description available for this article.",
    ) or "No description available for this article."
    content = sanitize_article_text(item.get("content"), description) or description
    article_id = item.get("article_id") or f"{category}-{index}-{title[:40]}"

    return NewsArticle(
        id=article_id,
        title=title,
        description=truncate_text(description),
        content=content,
        imageUrl=item.get("image_url") or f"https://placehold.co/800x500?text={category}",
        sourceName=item.get("source_name") or item.get("source_id") or "Unknown source",
        publishedAt=item.get("pubDate") or "",
        readTime=estimate_read_time(content or description or title),
        url=item.get("link") or "#",
        category=category,
    )


def fetch_news_by_category(
    category: str,
    limit: int,
    source: str | None = None,
    country: str | None = None,
    date: str | None = None,
    data_type: str | None = None,
) -> list[NewsArticle]:
    params = {
        "apikey": NEWS_API_KEY,
        "category": category,
        "language": "en",
        "size": str(limit),
    }

    domains = resolve_domains(category, source)
    if domains:
        params["domainurl"] = ",".join(domains)
    if country:
        params["country"] = country
    if date:
        params["from_date"] = date
        params["to_date"] = date
    if data_type:
        params["datatype"] = data_type

    response = requests.get(NEWS_API_URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])

    return dedupe_articles([map_article(item, category, index) for index, item in enumerate(results)])


def fetch_general_feed(
    category: str,
    limit: int,
    source: str | None = None,
    country: str | None = None,
    date: str | None = None,
    data_type: str | None = None,
) -> list[NewsArticle]:
    if category != "all":
        return fetch_news_by_category(category, limit, source, country, date, data_type)[:limit]

    all_articles: list[NewsArticle] = []
    per_category_limit = max(2, math.ceil(limit / len(SUPPORTED_CATEGORIES)))

    for item_category in SUPPORTED_CATEGORIES:
        try:
            all_articles.extend(
                fetch_news_by_category(item_category, per_category_limit, source, country, date, data_type)
            )
        except requests.RequestException:
            continue

    all_articles.sort(key=lambda article: article.publishedAt, reverse=True)
    return dedupe_articles(all_articles)[:limit]


def fetch_favorite_news(categories: list[str], limit_per_category: int = 7) -> list[NewsArticle]:
    articles: list[NewsArticle] = []
    for category in categories:
        try:
            articles.extend(fetch_news_by_category(category, limit_per_category))
        except requests.RequestException:
            continue

    articles.sort(key=lambda article: article.publishedAt, reverse=True)
    return dedupe_articles(articles)


def fetch_admin_cache(limit_per_category: int = 5) -> dict[str, list[NewsArticle]]:
    cache: dict[str, list[NewsArticle]] = {}
    for category in SUPPORTED_CATEGORIES:
        try:
            cache[category] = fetch_news_by_category(category, limit_per_category)
        except requests.RequestException:
            cache[category] = []
    return cache


def fetch_article_html(article_url: str) -> str:
    parsed_url = urlparse(article_url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Article URL must use http or https.")

    request = UrlRequest(
        article_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=12) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def get_cached_value(cache: dict[str, tuple[float, dict]], key: str, ttl_seconds: int) -> dict | None:
    cached_entry = cache.get(key)
    if not cached_entry:
        return None

    cached_at, payload = cached_entry
    if (time.time() - cached_at) > ttl_seconds:
        cache.pop(key, None)
        return None

    return payload


def set_cached_value(cache: dict[str, tuple[float, dict]], key: str, payload: dict) -> None:
    cache[key] = (time.time(), payload)


def extract_meta_content(html: str, attribute_name: str, attribute_value: str) -> str:
    pattern = re.compile(
        rf'<meta[^>]+{attribute_name}=["\']{re.escape(attribute_value)}["\'][^>]+content=["\'](.*?)["\']',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    return clean_text(match.group(1)) if match else ""


def extract_article_content(html: str) -> tuple[str, str, list[str]]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    extracted_title = clean_text(title_match.group(1)) if title_match else ""

    meta_description = extract_meta_content(html, "name", "description")
    if not meta_description:
        meta_description = extract_meta_content(html, "property", "og:description")

    stripped_html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    stripped_html = re.sub(r"<style.*?>.*?</style>", " ", stripped_html, flags=re.IGNORECASE | re.DOTALL)
    paragraph_matches = re.findall(r"<p[^>]*>(.*?)</p>", stripped_html, re.IGNORECASE | re.DOTALL)
    paragraphs = [clean_text(re.sub(r"<[^>]+>", " ", paragraph)) for paragraph in paragraph_matches]
    filtered_paragraphs = dedupe_text_chunks([
        paragraph for paragraph in paragraphs if len(paragraph) >= 60 and not is_boilerplate_chunk(paragraph)
    ])
    return extracted_title, meta_description, filtered_paragraphs[:20]


def tokenize(text: str) -> list[str]:
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it",
        "of", "on", "or", "that", "the", "this", "to", "was", "what", "when", "where", "which", "who",
        "why", "with",
    }
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9']+", text.lower())
        if len(token) > 2 and token not in stop_words
    ]


def split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned_sentences = [clean_text(sentence) for sentence in sentences]
    return [
        sentence
        for sentence in cleaned_sentences
        if len(sentence) >= 40 and not is_blocked_placeholder(sentence) and not is_boilerplate_chunk(sentence)
    ]


def build_context_candidates(context_chunks: list[str]) -> list[str]:
    candidates: list[str] = []
    for chunk in context_chunks:
        cleaned_chunk = sanitize_article_text(chunk)
        if not cleaned_chunk:
            continue
        candidates.append(cleaned_chunk)
        candidates.extend(split_into_sentences(cleaned_chunk))
    return dedupe_text_chunks(candidates)


def score_sentence(sentence: str, question_tokens: list[str]) -> float:
    sentence_tokens = tokenize(sentence)
    if not sentence_tokens:
        return 0.0
    overlap = Counter(sentence_tokens)
    score = sum(overlap[token] for token in question_tokens)
    return score / max(1, len(sentence_tokens) ** 0.35)


def select_relevant_excerpts(question: str, context_chunks: list[str], limit: int = 3) -> list[str]:
    question_tokens = tokenize(question)
    candidates = build_context_candidates(context_chunks)

    if not candidates:
        return []

    ranked_chunks = sorted(
        ((score_sentence(chunk, question_tokens), chunk) for chunk in candidates if chunk.strip()),
        key=lambda item: item[0],
        reverse=True,
    )
    best_chunks = [chunk for score, chunk in ranked_chunks if score > 0][:limit]
    return best_chunks or candidates[:limit]


def build_answer(question: str, context_chunks: list[str], article_title: str) -> tuple[str, list[str]]:
    best_chunks = select_relevant_excerpts(question, context_chunks, limit=3)
    if not best_chunks:
        return f"I could not find enough article content to answer a question about '{article_title}'.", []
    answer = " ".join(best_chunks[:2])
    return (answer[:697].rsplit(" ", 1)[0] + "...") if len(answer) > 700 else answer, best_chunks


def is_greeting(question: str) -> bool:
    normalized = question.strip().lower()
    return normalized in GREETING_INPUTS


def is_non_article_request(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.match(pattern, normalized) for pattern in NON_ARTICLE_PATTERNS)


def question_relevance_score(question: str, context_chunks: list[str]) -> float:
    question_tokens = tokenize(question)
    if not question_tokens or not context_chunks:
        return 0.0

    scores = [score_sentence(chunk, question_tokens) for chunk in build_context_candidates(context_chunks)]
    return max(scores, default=0.0)


def is_article_follow_up(question: str, conversation: list[dict[str, str]] | None = None) -> bool:
    if not conversation:
        return False

    normalized = question.strip().lower()
    raw_tokens = re.findall(r"[a-zA-Z']+", normalized)
    pronouns = {"it", "this", "that", "he", "she", "they", "them", "those", "these", "him", "her"}

    if normalized in {"more", "continue", "go on", "and?", "so?"}:
        return True

    if any(normalized.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES):
        return True

    return len(raw_tokens) <= 7 and any(token in pronouns for token in raw_tokens)


def should_treat_as_article_question(
    question: str,
    context_chunks: list[str],
    conversation: list[dict[str, str]] | None = None,
) -> bool:
    normalized = question.strip().lower()
    if is_greeting(normalized) or is_non_article_request(normalized):
        return False

    if len(normalized) <= 3:
        return False

    if is_article_follow_up(question, conversation):
        return True

    relevance = question_relevance_score(question, context_chunks)
    explicit_article_terms = {
        "summary",
        "summarize",
        "what happened",
        "why it matters",
        "why does it matter",
        "important in this story",
        "what does this mean",
        "what does that mean",
        "fact",
        "facts",
        "key facts",
        "article",
        "story",
        "news",
        "explain",
        "headline",
        "source",
    }
    has_article_intent = any(term in normalized for term in explicit_article_terms)

    if has_article_intent:
        return True

    starts_like_question = normalized.startswith(("who ", "what ", "when ", "where ", "why ", "how "))
    if starts_like_question and relevance >= 0.05:
        return True

    return relevance >= 0.12


def is_boilerplate_chunk(text: str) -> bool:
    normalized = text.lower()
    matched_terms = sum(1 for term in BOILERPLATE_TERMS if term in normalized)
    word_count = len(normalized.split())

    if matched_terms >= 2:
        return True

    if word_count > 18 and matched_terms >= 1 and normalized.count(" ") > 12:
        return True

    if normalized.count("subscribe") >= 2 or normalized.count("sign in") >= 2:
        return True

    return False


def handle_simple_general_request(question: str, article_title: str) -> str | None:
    normalized = question.strip().lower()
    if is_greeting(normalized):
        return (
            f"Hi. I'm ready. Ask me anything, and if your question is about '{article_title}', "
            "I'll ground the answer in the story."
        )

    print_match = re.match(r"^\s*print\s+(.+)", question, flags=re.IGNORECASE)
    if print_match:
        return print_match.group(1).strip()

    math_match = re.match(r"^\s*(\d+)\s*([\+\-\*/])\s*(\d+)", normalized)
    if math_match:
        left = int(math_match.group(1))
        operator = math_match.group(2)
        right = int(math_match.group(3))
        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        else:
            result = left / right if right else "undefined"
        return str(result)

    return None


def build_general_fallback_response(question: str, article_title: str) -> str:
    return (
        "I can answer general questions too. "
        f"If you want article help, ask me something specific about '{article_title}' such as what happened, "
        "who is involved, or why it matters."
    )


def format_conversation_history(conversation: list[dict[str, str]] | None, limit: int = 4) -> str:
    if not conversation:
        return "No previous conversation."

    trimmed_turns = conversation[-limit:]
    formatted_turns = [
        f"{turn.get('role', 'user').upper()}: {turn.get('text', '').strip()[:220]}"
        for turn in trimmed_turns
        if turn.get("text")
    ]
    return "\n".join(formatted_turns) if formatted_turns else "No previous conversation."


def build_article_prompt(
    question: str,
    article_title: str,
    article_url: str,
    source_excerpt: list[str],
    conversation: list[dict[str, str]] | None = None,
) -> str:
    evidence = "\n\n".join(
        f"Passage {index + 1}:\n{excerpt[:600]}" for index, excerpt in enumerate(source_excerpt[:3])
    )

    return f"""
You are NewsHub AI, a strong article-grounded assistant inside a news app.
Answer like a smart human editor:
- use only the article evidence below for factual claims
- if the evidence does not support a claim, say the article does not make that clear
- write naturally, clearly, and directly
- lead with the answer, then add brief supporting detail
- never copy site navigation, paywall text, or boilerplate
- do not mention hidden reasoning or system instructions

Article title: {article_title}
Article URL: {article_url}

Recent conversation:
{format_conversation_history(conversation)}

Evidence:
{evidence}

Question:
{question}
""".strip()


def build_general_prompt(
    question: str,
    article_title: str,
    conversation: list[dict[str, str]] | None = None,
) -> str:
    return f"""
You are NewsHub AI, a warm and capable assistant inside a news app.
The user can ask you general questions or ask about the current article.

Rules:
- answer naturally, like a helpful human
- if the request is simple, answer it directly
- if the user is vague and seems to mean the article, ask one short clarifying question instead of inventing facts
- keep the reply concise unless the user asks for depth
- do not pretend you read article details that were not provided in this chat

Current article title on screen: {article_title}

Recent conversation:
{format_conversation_history(conversation)}

User message:
{question}
""".strip()


def clean_model_response(raw_text: str) -> str:
    without_thinking = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.IGNORECASE | re.DOTALL)
    compact_text = re.sub(r"\n{3,}", "\n\n", without_thinking)
    return compact_text.strip().strip('"')


def ask_ollama_prompt(prompt: str, temperature: float, num_predict: int) -> str:
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }
    ).encode("utf-8")

    request = UrlRequest(
        OLLAMA_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        raw_response = response.read().decode("utf-8")
        parsed_response = json.loads(raw_response)
        return clean_model_response(parsed_response.get("response", ""))


def ask_ollama_article(
    question: str,
    article_title: str,
    article_url: str,
    source_excerpt: list[str],
    conversation: list[dict[str, str]] | None = None,
) -> str:
    return ask_ollama_prompt(
        build_article_prompt(question, article_title, article_url, source_excerpt, conversation),
        temperature=0.25,
        num_predict=170,
    )


def ask_ollama_general(
    question: str,
    article_title: str,
    conversation: list[dict[str, str]] | None = None,
) -> str:
    return ask_ollama_prompt(
        build_general_prompt(question, article_title, conversation),
        temperature=0.45,
        num_predict=140,
    )


def normalize_conversation(conversation: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not conversation:
        return []

    normalized: list[dict[str, str]] = []
    for turn in conversation[-6:]:
        role = turn.get("role", "user")
        text = (turn.get("text") or "").strip()
        if role in {"user", "assistant"} and text:
            normalized.append({"role": role, "text": text})
    return normalized


def build_chat_cache_key(article_url: str, question: str, conversation: list[dict[str, str]]) -> str:
    history_key = "||".join(f"{turn['role']}:{turn['text'][:120]}" for turn in conversation[-4:])
    return f"{CHATBOT_CACHE_VERSION}::{article_url.strip().lower()}::{question.strip().lower()}::{history_key}"


def build_chatbot_response(
    answer: str,
    article_title: str,
    article_url: str,
    source_excerpt: list[str],
    answer_mode: str,
    answer_engine: str,
    warning: str | None = None,
    source_status: str = "not_used",
    cached: bool = False,
) -> dict:
    return {
        "answer": answer,
        "extractedTitle": article_title,
        "sourceUrl": article_url,
        "sourceExcerpt": source_excerpt,
        "warning": warning,
        "sourceStatus": source_status,
        "answerMode": answer_mode,
        "answerEngine": answer_engine,
        "cached": cached,
    }


def get_article_context(
    article_url: str,
    article_title: str,
    article_description: str | None,
    article_content: str | None,
) -> dict:
    cached_context = get_cached_value(article_context_cache, article_url, ARTICLE_CONTEXT_TTL_SECONDS)
    if cached_context:
        return {**cached_context, "cached": True}

    extracted_title = article_title
    meta_description = ""
    paragraphs: list[str] = []
    warning = None
    source_status = "original_page"

    try:
        html = fetch_article_html(article_url)
        extracted_title, meta_description, paragraphs = extract_article_content(html)
    except (ValueError, HTTPError, URLError):
        source_status = "fallback_article_data"
        warning = "The original page was blocked, so NewsHub answered from the article data already stored in the app."

    context_payload = {
        "extracted_title": extracted_title or article_title,
        "meta_description": meta_description,
        "paragraphs": paragraphs,
        "warning": warning,
        "source_status": source_status,
        "context_chunks": dedupe_text_chunks([
            sanitize_article_text(extracted_title or article_title),
            sanitize_article_text(meta_description),
            sanitize_article_text(article_description),
            sanitize_article_text(article_content, article_description),
            *[sanitize_article_text(paragraph) for paragraph in paragraphs],
        ]),
    }
    set_cached_value(article_context_cache, article_url, context_payload)
    return {**context_payload, "cached": False}


def answer_general_request(
    question: str,
    article_title: str,
    conversation: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    simple_response = handle_simple_general_request(question, article_title)
    if simple_response:
        return simple_response, "local_rules"

    llm_answer = ask_ollama_general(question, article_title, conversation)
    if llm_answer:
        return llm_answer, OLLAMA_MODEL

    return build_general_fallback_response(question, article_title), "general_fallback"


def generate_chatbot_answer(
    question: str,
    article_url: str,
    article_title: str,
    article_description: str | None,
    article_content: str | None,
    conversation: list[dict[str, str]] | None = None,
) -> dict:
    normalized_conversation = normalize_conversation(conversation)
    cache_key = build_chat_cache_key(article_url, question, normalized_conversation)
    cached_answer = get_cached_value(chat_answer_cache, cache_key, CHAT_ANSWER_TTL_SECONDS)
    if cached_answer:
        return {**cached_answer, "cached": True}

    if is_greeting(question) or is_non_article_request(question):
        try:
            answer, engine = answer_general_request(question, article_title, normalized_conversation)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            answer = build_general_fallback_response(question, article_title)
            engine = "general_fallback"

        response_payload = build_chatbot_response(
            answer=answer,
            article_title=article_title,
            article_url=article_url,
            source_excerpt=[],
            answer_mode=ANSWER_MODE_GENERAL,
            answer_engine=engine,
            source_status="not_used",
        )
        set_cached_value(chat_answer_cache, cache_key, response_payload)
        return response_payload

    article_context = get_article_context(article_url, article_title, article_description, article_content)
    extracted_title = article_context["extracted_title"]
    warning = article_context["warning"]
    source_status = article_context["source_status"]
    context_chunks = article_context["context_chunks"]

    if not should_treat_as_article_question(question, context_chunks, normalized_conversation):
        try:
            answer, engine = answer_general_request(question, extracted_title or article_title, normalized_conversation)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            answer = build_general_fallback_response(question, extracted_title or article_title)
            engine = "general_fallback"

        response_payload = build_chatbot_response(
            answer=answer,
            article_title=extracted_title or article_title,
            article_url=article_url,
            source_excerpt=[],
            answer_mode=ANSWER_MODE_GENERAL,
            answer_engine=engine,
            source_status="not_used",
            cached=article_context["cached"],
        )
        set_cached_value(chat_answer_cache, cache_key, response_payload)
        return response_payload

    if not context_chunks:
        response_payload = build_chatbot_response(
            answer=(
                "I do not have enough readable article content yet to answer reliably. "
                "Please open the original article or ask about another story."
            ),
            article_title=extracted_title or article_title,
            article_url=article_url,
            source_excerpt=[],
            answer_mode=ANSWER_MODE_ARTICLE,
            answer_engine="article_fallback",
            warning=warning or "The available article data was too limited to generate a trustworthy answer.",
            source_status=source_status,
            cached=article_context["cached"],
        )
        set_cached_value(chat_answer_cache, cache_key, response_payload)
        return response_payload

    answer, source_excerpt = build_answer(question, context_chunks, extracted_title or article_title)
    answer_engine = "article_fallback"

    try:
        llm_answer = ask_ollama_article(
            question,
            extracted_title or article_title,
            article_url,
            source_excerpt or select_relevant_excerpts(question, context_chunks, limit=3),
            normalized_conversation,
        )
        if llm_answer:
            answer = llm_answer
            answer_engine = OLLAMA_MODEL
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        if warning is None:
            warning = "Qwen was unavailable for this request, so NewsHub used the fast article fallback answer."

    response_payload = build_chatbot_response(
        answer=answer,
        article_title=extracted_title or article_title,
        article_url=article_url,
        source_excerpt=source_excerpt,
        answer_mode=ANSWER_MODE_ARTICLE,
        answer_engine=answer_engine,
        warning=warning,
        source_status=source_status,
        cached=article_context["cached"],
    )
    set_cached_value(chat_answer_cache, cache_key, response_payload)
    return response_payload
