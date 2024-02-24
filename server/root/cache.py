"""
23.02.2024
Alexander Tyamin.

Storage for processing cache, user sessions, and any key-value data.
"""

from abc import ABC, abstractmethod


class CacheStorage(ABC):
    """Provides a key-value storage."""

    @abstractmethod
    async def get(self, key):
        pass

    @abstractmethod
    async def set(self, key, value):
        pass

    @abstractmethod
    async def delete(self, key):
        pass

    @abstractmethod
    async def expire(self, key, ttl: int):
        pass


class DictCacheStorage(CacheStorage):
    """
    Provides a key-value storage
    based on a standard Python dictionary.
    """

    def __init__(self):
        self.storage = {}

    async def get(self, key):
        return self.storage.get(key)

    async def set(self, key, value):
        self.storage[key] = value

    async def delete(self, key):
        self.storage.pop(key, None)

    async def expire(self, key, ttl: int):
        pass


storage = DictCacheStorage()


async def get_cache_storage() -> CacheStorage:
    """
    Provides a key-value storage.

    return: CacheStorage interface
    """

    return storage
