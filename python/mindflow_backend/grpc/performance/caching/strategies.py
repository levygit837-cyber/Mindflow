"""Advanced caching strategies for different use cases.

Provides specialized caching strategies optimized for
different access patterns, content types, and performance requirements.
"""

from __future__ import annotations

import time
import heapq
from typing import Dict, Any, Optional, List
from collections import defaultdict, OrderedDict
from abc import ABC, abstractmethod

from .cache import CacheStrategy, CacheConfig, CacheEntry
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class LFUCacheStrategy(CacheStrategy):
    """Least Frequently Used cache eviction strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._frequencies: Dict[str, int] = defaultdict(int)
        self._frequency_groups: Dict[int, List[str]] = defaultdict(list)
        self._min_frequency = 0
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0,
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry and update frequency."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                self._remove_entry(key)
                self._stats['expired_removals'] += 1
                return None
            
            # Update frequency
            old_freq = self._frequencies[key]
            new_freq = old_freq + 1
            self._frequencies[key] = new_freq
            
            # Move to new frequency group
            self._frequency_groups[old_freq].remove(key)
            self._frequency_groups[new_freq].append(key)
            
            # Update minimum frequency
            if not self._frequency_groups[self._min_frequency]:
                self._min_frequency = new_freq
            
            entry.touch()
            self._stats['hits'] += 1
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into cache."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Check size limit
            while len(self._cache) >= self.config.max_size:
                self._evict_lfu()
            
            # Add new entry
            self._cache[key] = entry
            self._frequencies[key] = 1
            self._frequency_groups[1].append(key)
            
            if self._min_frequency == 0:
                self._min_frequency = 1
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
            self._frequencies.clear()
            self._frequency_groups.clear()
            self._min_frequency = 0
    
    def size(self) -> int:
        """Get number of entries."""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
                self._stats['expired_removals'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                'entries': len(self._cache),
                'max_entries': self.config.max_size,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': hit_rate,
                'evictions': self._stats['evictions'],
                'expired_removals': self._stats['expired_removals'],
                'min_frequency': self._min_frequency,
            }
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and update frequency data."""
        if key in self._cache:
            freq = self._frequencies[key]
            
            # Remove from cache
            del self._cache[key]
            
            # Remove from frequency tracking
            del self._frequencies[key]
            if key in self._frequency_groups[freq]:
                self._frequency_groups[freq].remove(key)
            
            # Update minimum frequency
            if not self._frequency_groups[self._min_frequency]:
                while self._min_frequency > 0 and not self._frequency_groups[self._min_frequency]:
                    self._min_frequency += 1
    
    def _evict_lfu(self) -> None:
        """Evict least frequently used entry."""
        if not self._frequency_groups[self._min_frequency]:
            return
        
        # Remove first entry from minimum frequency group
        key_to_evict = self._frequency_groups[self._min_frequency].pop(0)
        self._remove_entry(key_to_evict)
        self._stats['evictions'] += 1


class AdaptiveCacheStrategy(CacheStrategy):
    """Adaptive cache that changes strategy based on access patterns."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._current_strategy = LRUCacheStrategy(config)
        self._strategies = {
            'lru': LRUCacheStrategy(config),
            'ttl': TTLCacheStrategy(config),
            'size_based': SizeBasedCacheStrategy(config),
            'lfu': LFUCacheStrategy(config),
        }
        self._strategy_stats = {name: {'hits': 0, 'misses': 0} for name in self._strategies}
        self._adaptation_interval = 100  # Adapt every 100 requests
        self._request_count = 0
        self._stats = {
            'strategy_changes': 0,
            'current_strategy': 'lru',
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry using current strategy."""
        self._request_count += 1
        
        entry = self._current_strategy.get(key)
        
        # Update strategy stats
        strategy_name = type(self._current_strategy).__name__.replace('CacheStrategy', '').lower()
        if entry:
            self._strategy_stats[strategy_name]['hits'] += 1
        else:
            self._strategy_stats[strategy_name]['misses'] += 1
        
        # Check if we should adapt
        if self._request_count % self._adaptation_interval == 0:
            self._adapt_strategy()
        
        return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry using current strategy."""
        return self._current_strategy.put(key, entry)
    
    def remove(self, key: str) -> bool:
        """Remove entry using current strategy."""
        return self._current_strategy.remove(key)
    
    def clear(self) -> None:
        """Clear all entries."""
        for strategy in self._strategies.values():
            strategy.clear()
    
    def size(self) -> int:
        """Get number of entries."""
        return self._current_strategy.size()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        return self._current_strategy.cleanup_expired()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._current_strategy.get_stats()
        stats.update(self._stats)
        stats['strategy_performance'] = self._strategy_stats
        return stats
    
    def _adapt_strategy(self) -> None:
        """Adapt strategy based on performance."""
        # Calculate hit rates for each strategy
        hit_rates = {}
        for name, stats in self._strategy_stats.items():
            total = stats['hits'] + stats['misses']
            hit_rates[name] = (stats['hits'] / total * 100) if total > 0 else 0
        
        # Find best performing strategy
        best_strategy = max(hit_rates.keys(), key=lambda k: hit_rates[k])
        current_strategy = type(self._current_strategy).__name__.replace('CacheStrategy', '').lower()
        
        # Switch if significantly better
        if (best_strategy != current_strategy and 
            hit_rates[best_strategy] > hit_rates[current_strategy] + 10):
            
            old_strategy = self._current_strategy
            self._current_strategy = self._strategies[best_strategy]
            
            # Transfer data if possible (simplified)
            _logger.info(
                "cache_strategy_adapted",
                old=current_strategy,
                new=best_strategy,
                old_hit_rate=hit_rates[current_strategy],
                new_hit_rate=hit_rates[best_strategy]
            )
            
            self._stats['strategy_changes'] += 1
            self._stats['current_strategy'] = best_strategy


class HierarchicalCacheStrategy(CacheStrategy):
    """Hierarchical cache with multiple levels."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        # L1: Fast, small cache (LRU)
        self._l1_cache = LRUCacheStrategy(CacheConfig(
            max_size=config.max_size // 4,
            max_memory_mb=config.max_memory_mb // 4
        ))
        
        # L2: Medium cache (TTL)
        self._l2_cache = TTLCacheStrategy(CacheConfig(
            max_size=config.max_size // 2,
            max_memory_mb=config.max_memory_mb // 2,
            default_ttl_seconds=config.default_ttl_seconds // 2
        ))
        
        # L3: Large, slow cache (Size-based)
        self._l3_cache = SizeBasedCacheStrategy(CacheConfig(
            max_size=config.max_size,
            max_memory_mb=config.max_memory_mb,
            default_ttl_seconds=config.default_ttl_seconds
        ))
        
        self._stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0,
            'promotions': 0,
            'demotions': 0,
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from hierarchical cache."""
        # Try L1 first
        entry = self._l1_cache.get(key)
        if entry:
            self._stats['l1_hits'] += 1
            return entry
        
        # Try L2
        entry = self._l2_cache.get(key)
        if entry:
            self._stats['l2_hits'] += 1
            # Promote to L1
            self._l1_cache.put(key, entry)
            self._stats['promotions'] += 1
            return entry
        
        # Try L3
        entry = self._l3_cache.get(key)
        if entry:
            self._stats['l3_hits'] += 1
            # Promote to L2
            self._l2_cache.put(key, entry)
            self._stats['promotions'] += 1
            return entry
        
        self._stats['misses'] += 1
        return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into hierarchical cache."""
        # Always put in L1 first
        success = self._l1_cache.put(key, entry)
        
        # If L1 is full, demote to L2
        if not success:
            success = self._l2_cache.put(key, entry)
            if success:
                self._stats['demotions'] += 1
        
        # If L2 is full, demote to L3
        if not success:
            success = self._l3_cache.put(key, entry)
            if success:
                self._stats['demotions'] += 1
        
        return success
    
    def remove(self, key: str) -> bool:
        """Remove entry from all levels."""
        removed = False
        if self._l1_cache.remove(key):
            removed = True
        if self._l2_cache.remove(key):
            removed = True
        if self._l3_cache.remove(key):
            removed = True
        return removed
    
    def clear(self) -> None:
        """Clear all levels."""
        self._l1_cache.clear()
        self._l2_cache.clear()
        self._l3_cache.clear()
    
    def size(self) -> int:
        """Get total number of entries."""
        return self._l1_cache.size() + self._l2_cache.size() + self._l3_cache.size()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from all levels."""
        total_removed = 0
        total_removed += self._l1_cache.cleanup_expired()
        total_removed += self._l2_cache.cleanup_expired()
        total_removed += self._l3_cache.cleanup_expired()
        return total_removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hierarchical cache statistics."""
        l1_stats = self._l1_cache.get_stats()
        l2_stats = self._l2_cache.get_stats()
        l3_stats = self._l3_cache.get_stats()
        
        total_requests = sum(self._stats.values())
        hit_rate = ((total_requests - self._stats['misses']) / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': self.size(),
            'total_size_mb': (l1_stats['total_size_mb'] + l2_stats['total_size_mb'] + l3_stats['total_size_mb']),
            'hit_rate_percent': hit_rate,
            'level_stats': {
                'l1': {**l1_stats, 'hits': self._stats['l1_hits']},
                'l2': {**l2_stats, 'hits': self._stats['l2_hits']},
                'l3': {**l3_stats, 'hits': self._stats['l3_hits']},
            },
            'promotions': self._stats['promotions'],
            'demotions': self._stats['demotions'],
            'misses': self._stats['misses'],
        }


class ShardedCacheStrategy(CacheStrategy):
    """Sharded cache for better concurrency."""
    
    def __init__(self, config: CacheConfig, num_shards: int = 16):
        super().__init__(config)
        self._num_shards = num_shards
        shard_size = config.max_size // num_shards
        shard_memory = config.max_memory_mb // num_shards
        
        self._shards = [
            LRUCacheStrategy(CacheConfig(
                max_size=shard_size,
                max_memory_mb=shard_memory
            ))
            for _ in range(num_shards)
        ]
        
        self._stats = {
            'hits': 0,
            'misses': 0,
            'shard_distribution': [0] * num_shards,
        }
    
    def _get_shard(self, key: str) -> CacheStrategy:
        """Get shard for key."""
        shard_index = hash(key) % self._num_shards
        self._stats['shard_distribution'][shard_index] += 1
        return self._shards[shard_index]
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from appropriate shard."""
        shard = self._get_shard(key)
        entry = shard.get(key)
        
        if entry:
            self._stats['hits'] += 1
        else:
            self._stats['misses'] += 1
        
        return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put entry into appropriate shard."""
        shard = self._get_shard(key)
        return shard.put(key, entry)
    
    def remove(self, key: str) -> bool:
        """Remove entry from appropriate shard."""
        shard = self._get_shard(key)
        return shard.remove(key)
    
    def clear(self) -> None:
        """Clear all shards."""
        for shard in self._shards:
            shard.clear()
    
    def size(self) -> int:
        """Get total number of entries."""
        return sum(shard.size() for shard in self._shards)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from all shards."""
        return sum(shard.cleanup_expired() for shard in self._shards)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sharded cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        shard_stats = []
        for i, shard in enumerate(self._shards):
            stats = shard.get_stats()
            stats['shard_index'] = i
            stats['requests'] = self._stats['shard_distribution'][i]
            shard_stats.append(stats)
        
        return {
            'total_entries': self.size(),
            'hit_rate_percent': hit_rate,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'num_shards': self._num_shards,
            'shard_stats': shard_stats,
        }


# Strategy factory
def create_cache_strategy(strategy_name: str, config: CacheConfig, **kwargs) -> CacheStrategy:
    """Create a cache strategy by name."""
    strategies = {
        'lru': LRUCacheStrategy,
        'ttl': TTLCacheStrategy,
        'size_based': SizeBasedCacheStrategy,
        'lfu': LFUCacheStrategy,
        'adaptive': AdaptiveCacheStrategy,
        'hierarchical': HierarchicalCacheStrategy,
        'sharded': lambda cfg: ShardedCacheStrategy(cfg, kwargs.get('num_shards', 16)),
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown cache strategy: {strategy_name}")
    
    return strategies[strategy_name](config)
