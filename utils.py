import logging
import time
from collections import defaultdict
from config import CHUNK_SIZE, RATE_LIMIT, RATE_WINDOW

logger = logging.getLogger(__name__)


def split_text(text: str, max_length: int = CHUNK_SIZE) -> list[str]:
    """Разбивает текст на части по предложениям, не превышая max_length."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current = ""
    # Разбиваем по предложениям (точка, !, ?, перевод строки)
    sentences = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in ".!?\n":
            sentences.append(buf.strip())
            buf = ""
    if buf.strip():
        sentences.append(buf.strip())

    for sentence in sentences:
        # Если одно предложение длиннее лимита — режем по словам
        if len(sentence) > max_length:
            if current:
                chunks.append(current)
                current = ""
            words = sentence.split()
            for word in words:
                if len(current) + len(word) + 1 > max_length:
                    if current:
                        chunks.append(current)
                    current = word
                else:
                    current = f"{current} {word}".strip()
            continue

        if len(current) + len(sentence) + 1 > max_length:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    logger.info("Текст разбит на %d частей", len(chunks))
    return chunks


class RateLimiter:
    """Простой rate limiter по user_id."""

    def __init__(self):
        self._requests: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        # Убираем старые записи
        self._requests[user_id] = [
            t for t in self._requests[user_id] if now - t < RATE_WINDOW
        ]
        if len(self._requests[user_id]) >= RATE_LIMIT:
            return False
        self._requests[user_id].append(now)
        return True
