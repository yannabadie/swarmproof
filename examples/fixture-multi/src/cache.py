"""Cache TTL adossé au Store versionné."""

from src.store import Store


class TTLCache:
    """Cache mémoire invalidé par version du store et par préfixe de clé."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self._entries: dict[str, tuple[str, int]] = {}

    def get(self, key: str) -> str | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        value, version = entry
        if version != self.store.version:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: str) -> None:
        self._entries[key] = (value, self.store.version)

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalide toutes les clés commençant par `prefix` ; renvoie le nombre supprimé."""
        removed = 0
        for key in list(self._entries):
            # BUG: comparaison d'égalité au lieu de startswith -> les clés préfixées
            # restent en cache.
            if key == prefix:
                del self._entries[key]
                removed += 1
        return removed
