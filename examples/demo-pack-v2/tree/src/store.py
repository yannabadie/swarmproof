"""Stockage en mémoire versionné, utilisé par le cache TTL."""


class Store:
    """Key-value store avec compteur de version pour l'invalidation des caches."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.version = 0

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        self.version += 1

    def get(self, key: str) -> str | None:
        return self._data.get(key)


def seeded_store() -> Store:
    store = Store()
    store.put("user:1:name", "Ada")
    return store
