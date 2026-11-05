# Fixture multi-fichiers — bug de cache/invalidation

Petit dépôt (store versionné + cache TTL + API) avec deux bugs répartis sur deux fichiers :

- `src/store.py` : `version` n'est jamais incrémentée dans `put()` → cache périmé ;
- `src/cache.py` : `invalidate_prefix()` compare `key == prefix` au lieu de `startswith`.

Résultat attendu : 2 tests rouges / 4. La correction exige de modifier **au moins deux
fichiers**, ce qui en fait le support des tests multi-fichiers et de la démo v2.

```bash
cd examples/fixture-multi
python -m unittest discover -s tests -v
```
