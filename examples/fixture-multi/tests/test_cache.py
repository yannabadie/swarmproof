"""Tests du cache TTL et de son invalidation (stdlib unittest)."""

import unittest

from src.api import bootstrap, read_user_name, rename_user
from src.cache import TTLCache


class CacheInvalidationTests(unittest.TestCase):
    def test_basic_set_get(self) -> None:
        store, cache = bootstrap()
        cache.set("k", "v")
        self.assertEqual(cache.get("k"), "v")

    def test_missing_key_returns_none(self) -> None:
        _, cache = bootstrap()
        self.assertIsNone(cache.get("absent"))

    def test_cached_value_is_refreshed_after_store_update(self) -> None:
        store, cache = bootstrap()
        self.assertEqual(read_user_name(store, cache), "Ada")
        renamed = rename_user(store, cache, "Grace")
        self.assertEqual(renamed, "Grace")

    def test_invalidate_prefix_clears_all_matching_entries(self) -> None:
        _, cache = bootstrap()
        cache.set("user:1:name", "Ada")
        cache.set("user:1:email", "ada@example.org")
        removed = cache.invalidate_prefix("user:1")
        self.assertEqual(removed, 2)
        self.assertIsNone(cache.get("user:1:name"))
        self.assertIsNone(cache.get("user:1:email"))


if __name__ == "__main__":
    unittest.main()
