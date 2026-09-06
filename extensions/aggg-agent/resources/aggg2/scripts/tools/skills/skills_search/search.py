"""Поиск скиллов в skills.sh и каталогах."""
import hashlib
import json
import urllib.parse
import urllib.request

from .cache import (
    cache_get,
    cache_init,
    cache_set,
    circuit_breaker_check,
    circuit_breaker_record_failure,
    circuit_breaker_record_success,
)
from .events import log_event
from .paths import API, skills_catalog


class SkillsSearchUnavailable(RuntimeError):
    """skills.sh API недоступен."""
    pass


def _normalize_name(name):
    """Нормализация имени для релевантности."""
    return name.lower().replace("-", " ").replace("_", " ")


def _calculate_relevance(query, item):
    """Расчёт релевантности (простой: вхождение подстроки)."""
    q = query.lower()
    name = item.get("name", "").lower()
    desc = item.get("description", "").lower()

    score = 0
    if q in name:
        score += 10
    if q in desc:
        score += 5

    # Бонус за installs
    installs = item.get("installs", 0)
    if installs > 1000:
        score += 3
    elif installs > 100:
        score += 2
    elif installs > 10:
        score += 1

    return score


def _github_search(query, limit=30):
    """Поиск через GitHub API (фоллбэк)."""
    if not circuit_breaker_check("github"):
        return []

    try:
        # Поиск репозиториев с темой "agent-skills" или "ai-skills"
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}+topic:agent-skills&per_page={limit}"
        if not url.startswith("https://api.github.com/"):
            raise ValueError("недопустимый GitHub URL")

        req = urllib.request.Request(url)
        from .paths import GITHUB_TOKEN
        if GITHUB_TOKEN:
            req.add_header("Authorization", f"token {GITHUB_TOKEN}")

        with urllib.request.urlopen(req, timeout=15) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected — fixed api.github.com origin
            data = json.loads(resp.read().decode("utf-8"))

        circuit_breaker_record_success("github")

        results = []
        for item in data.get("items", []):
            results.append({
                "name": item.get("name", ""),
                "owner": item.get("owner", {}).get("login", ""),
                "repo": item.get("name", ""),
                "description": item.get("description", ""),
                "installs": item.get("stargazers_count", 0),
                "source": "github",
                "url": item.get("html_url", "")
            })

        return results
    except Exception:
        circuit_breaker_record_failure("github")
        return []


def search_multi(query, limit=10):
    """Мульти-поиск: skills.sh + каталоги (sitemap)."""
    cache_init()

    # Проверяем кэш
    q_hash = hashlib.sha256(query.encode()).hexdigest()
    cached = cache_get(q_hash)
    if cached:
        log_event("search_cache_hit", {"query": query, "limit": limit})
        return cached[:limit]

    results = []

    # 1. skills.sh API (основной источник)
    if circuit_breaker_check("skills.sh"):
        try:
            url = f"{API}?q={urllib.parse.quote(query)}&limit=50"
            if not url.startswith("https://skills.sh/"):
                raise ValueError("недопустимый skills.sh URL")
            req = urllib.request.Request(url)

            with urllib.request.urlopen(req, timeout=15) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected — fixed skills.sh origin
                data = json.loads(resp.read().decode("utf-8"))

            circuit_breaker_record_success("skills.sh")

            for item in data.get("results", []):
                results.append({
                    "name": item.get("name", ""),
                    "owner": item.get("owner", ""),
                    "repo": item.get("repo", ""),
                    "description": item.get("description", ""),
                    "installs": item.get("installs", 0),
                    "source": "skills.sh",
                    "url": item.get("url", "")
                })
        except Exception:
            circuit_breaker_record_failure("skills.sh")

    # 2. Sitemap-каталоги (если доступны)
    if skills_catalog and circuit_breaker_check("sitemap"):
        try:
            catalog_results = skills_catalog.search(query, limit=20)
            for item in catalog_results:
                results.append({
                    "name": item.get("name", ""),
                    "owner": item.get("owner", ""),
                    "repo": item.get("repo", ""),
                    "description": item.get("description", ""),
                    "installs": item.get("installs", 0),
                    "source": "sitemap",
                    "url": item.get("url", "")
                })
            circuit_breaker_record_success("sitemap")
        except Exception:
            circuit_breaker_record_failure("sitemap")

    # 3. GitHub API (фоллбэк)
    if len(results) < 5 and circuit_breaker_check("github"):
        github_results = _github_search(query, limit=20)
        results.extend(github_results)

    # Сортировка по релевантности
    results.sort(key=lambda x: _calculate_relevance(query, x), reverse=True)

    # Кэшируем
    cache_set(q_hash, query, results, source="multi")

    log_event("search", {"query": query, "limit": limit, "results": len(results)})

    return results[:limit]


def search(query, limit=10):
    """Поиск скиллов (основная функция)."""
    return search_multi(query, limit)
