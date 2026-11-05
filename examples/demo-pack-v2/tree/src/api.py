"""API applicative au-dessus du store et du cache."""

from src.cache import TTLCache
from src.store import Store, seeded_store


def bootstrap() -> tuple[Store, TTLCache]:
    store = seeded_store()
    return store, TTLCache(store)


def read_user_name(store: Store, cache: TTLCache) -> str | None:
    cached = cache.get("user:1:name")
    if cached is not None:
        return cached
    value = store.get("user:1:name")
    if value is not None:
        cache.set("user:1:name", value)
    return value


def rename_user(store: Store, cache: TTLCache, new_name: str) -> str:
    store.put("user:1:name", new_name)
    return read_user_name(store, cache) or ""
