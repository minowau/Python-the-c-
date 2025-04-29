from typing import Dict, Any, Optional, Set
from weakref import WeakSet
import gc

class MemoryManager:
    """Hybrid memory management system combining reference counting and generational GC."""
    
    def __init__(self):
        self.ref_counts: Dict[int, int] = {}
        self.gen0: Set[int] = set()  # Young generation
        self.gen1: Set[int] = set()  # Old generation
        self.weak_refs = WeakSet()
        self.memory_pool = MemoryPool()
        
        # Configure Python's GC for our hybrid approach
        gc.disable()  # We'll manage collections explicitly
    
    def allocate(self, size: int, type_info: Dict[str, Any]) -> int:
        """Allocate memory from pool.
        
        Args:
            size: Number of bytes to allocate
            type_info: Type information for the allocation
            
        Returns:
            Memory address
        """
        addr = self.memory_pool.allocate(size)
        if addr:
            self.ref_counts[addr] = 1
            self.gen0.add(addr)
        return addr
    
    def increment_ref(self, addr: int) -> None:
        """Increment reference count for object."""
        if addr in self.ref_counts:
            self.ref_counts[addr] += 1
    
    def decrement_ref(self, addr: int) -> None:
        """Decrement reference count and potentially free memory."""
        if addr in self.ref_counts:
            self.ref_counts[addr] -= 1
            if self.ref_counts[addr] <= 0:
                self._collect_object(addr)
    
    def _collect_object(self, addr: int) -> None:
        """Collect single object and its references."""
        if addr in self.gen0:
            self.gen0.remove(addr)
        if addr in self.gen1:
            self.gen1.remove(addr)
        
        self.memory_pool.free(addr)
        del self.ref_counts[addr]
    
    def collect_young(self) -> None:
        """Collect young generation objects."""
        survivors = set()
        for addr in self.gen0:
            if self.ref_counts[addr] > 0:
                survivors.add(addr)
                if self._should_promote(addr):
                    self.gen1.add(addr)
            else:
                self._collect_object(addr)
        
        self.gen0 = survivors - self.gen1
    
    def collect_full(self) -> None:
        """Perform full garbage collection."""
        # Collect both generations
        self.collect_young()
        
        survivors = set()
        for addr in self.gen1:
            if self.ref_counts[addr] > 0:
                survivors.add(addr)
            else:
                self._collect_object(addr)
        
        self.gen1 = survivors
    
    def _should_promote(self, addr: int) -> bool:
        """Determine if object should be promoted to old generation."""
        # Simple promotion strategy based on survival count
        # Could be enhanced with more sophisticated heuristics
        return True  # For now, always promote surviving objects


class MemoryPool:
    """Memory pool for efficient allocation."""
    
    def __init__(self, initial_size: int = 1024 * 1024):
        self.pool_size = initial_size
        self.free_blocks: Dict[int, int] = {}  # addr -> size
        self.used_blocks: Dict[int, int] = {}  # addr -> size
        
        # Initialize with one large free block
        self.free_blocks[0] = initial_size
    
    def allocate(self, size: int) -> Optional[int]:
        """Allocate memory block of given size.
        
        Args:
            size: Number of bytes to allocate
            
        Returns:
            Memory address or None if allocation fails
        """
        # Find best fit block
        best_addr = None
        best_size = float('inf')
        
        for addr, block_size in self.free_blocks.items():
            if block_size >= size and block_size < best_size:
                best_addr = addr
                best_size = block_size
        
        if best_addr is not None:
            # Remove from free blocks
            del self.free_blocks[best_addr]
            
            # Add to used blocks
            self.used_blocks[best_addr] = size
            
            # Create new free block if there's remaining space
            if best_size > size:
                self.free_blocks[best_addr + size] = best_size - size
            
            return best_addr
        
        # Could implement pool expansion here
        return None
    
    def free(self, addr: int) -> None:
        """Free memory block.
        
        Args:
            addr: Address of block to free
        """
        if addr in self.used_blocks:
            size = self.used_blocks[addr]
            del self.used_blocks[addr]
            
            # Add to free blocks and merge adjacent blocks
            self.free_blocks[addr] = size
            self._merge_adjacent_blocks()
    
    def _merge_adjacent_blocks(self) -> None:
        """Merge adjacent free blocks to reduce fragmentation."""
        merged = True
        while merged:
            merged = False
            blocks = sorted(self.free_blocks.items())
            
            for i in range(len(blocks) - 1):
                curr_addr, curr_size = blocks[i]
                next_addr, next_size = blocks[i + 1]
                
                if curr_addr + curr_size == next_addr:
                    # Merge blocks
                    del self.free_blocks[curr_addr]
                    del self.free_blocks[next_addr]
                    self.free_blocks[curr_addr] = curr_size + next_size
                    merged = True
                    break