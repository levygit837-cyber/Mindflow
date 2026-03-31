"""Memory Observers — Passive agents that monitor missions and annotate memory.

Fase 3B — SPADE Memory Observer Protocol

Components:
    - MemoryObserver: Background async task that listens to mission events
      and writes important observations to universal memory.
"""

from .memory_observer import MemoryObserver

__all__ = ["MemoryObserver"]