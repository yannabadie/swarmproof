"""SwarmProof — le swarm propose, l'oracle externe décide, l'Evidence Pack le prouve.

Le produit orchestre le moteur NEXUS (HybridSwarmEngine, extrait de swarm-os) avec des
drivers CLI hétérogènes, mais **ne croit jamais** le statut auto-déclaré du moteur :
seul un oracle externe (tests) rend le verdict, et un pack de preuves vérifiable le documente.

Bibliothèque standard uniquement (Python >= 3.11), zéro dépendance runtime.
"""

from __future__ import annotations

__version__ = "0.2.1"
__all__ = ["__version__"]
