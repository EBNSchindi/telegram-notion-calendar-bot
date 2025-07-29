"""Base repository interface for data access layer."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from dataclasses import dataclass


T = TypeVar('T')  # Generic type for entities


@dataclass
class PaginationParams:
    """Parameters for pagination."""
    page_size: int = 10
    start_cursor: Optional[str] = None
    
    
@dataclass
class PaginatedResult(Generic[T]):
    """Result container for paginated queries."""
    items: List[T]
    has_more: bool
    next_cursor: Optional[str] = None
    total_count: Optional[int] = None


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository interface.
    
    Provides common CRUD operations with type safety and pagination support.
    """
    
    @abstractmethod
    async def create(self, entity: T) -> str:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            str: ID of the created entity
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Optional[T]: Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(self, pagination: Optional[PaginationParams] = None) -> PaginatedResult[T]:
        """
        Get all entities with optional pagination.
        
        Args:
            pagination: Pagination parameters
            
        Returns:
            PaginatedResult[T]: Paginated list of entities
        """
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, entity: T) -> bool:
        """
        Update an existing entity.
        
        Args:
            entity_id: ID of the entity to update
            entity: Updated entity data
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: ID of the entity to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any], 
                             pagination: Optional[PaginationParams] = None) -> PaginatedResult[T]:
        """
        Find entities by criteria.
        
        Args:
            criteria: Search criteria as key-value pairs
            pagination: Pagination parameters
            
        Returns:
            PaginatedResult[T]: Paginated list of matching entities
        """
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """
        Check if entity exists.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            bool: True if exists, False otherwise
        """
        pass
    
    async def create_many(self, entities: List[T]) -> List[str]:
        """
        Create multiple entities.
        
        Default implementation creates one by one.
        Subclasses can override for batch operations.
        
        Args:
            entities: List of entities to create
            
        Returns:
            List[str]: List of created entity IDs
        """
        ids = []
        for entity in entities:
            entity_id = await self.create(entity)
            ids.append(entity_id)
        return ids
    
    async def delete_many(self, entity_ids: List[str]) -> int:
        """
        Delete multiple entities.
        
        Default implementation deletes one by one.
        Subclasses can override for batch operations.
        
        Args:
            entity_ids: List of entity IDs to delete
            
        Returns:
            int: Number of deleted entities
        """
        deleted_count = 0
        for entity_id in entity_ids:
            if await self.delete(entity_id):
                deleted_count += 1
        return deleted_count