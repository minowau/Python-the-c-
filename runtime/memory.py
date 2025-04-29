from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
import numpy as np

@dataclass
class MemoryBlock:
    """Represents a block of memory for tensor operations."""
    size: int  # Size in bytes
    device: str  # Device where memory is allocated
    is_free: bool = True
    alignment: int = 64  # Memory alignment in bytes
    tensor_shape: Optional[Tuple[int, ...]] = None
    dtype: Optional[str] = None

class MemoryManager:
    """Memory manager for efficient tensor operations."""
    
    def __init__(self, initial_pool_size: int = 1024*1024):
        self.memory_pools: Dict[str, List[MemoryBlock]] = {
            'cpu': [],
            'cuda': []
        }
        self.active_tensors: Dict[int, MemoryBlock] = {}
        self.fragmentation_threshold = 0.3  # 30% fragmentation triggers defrag
        self.enable_memory_pool = True
        self._initialize_memory_pool('cpu', initial_pool_size)
    
    def _initialize_memory_pool(self, device: str, size: int) -> None:
        """Initialize memory pool for device."""
        self.memory_pools[device].append(
            MemoryBlock(size=size, device=device)
        )
    
    def allocate(self, size: int, device: str = 'cpu',
                 shape: Optional[Tuple[int, ...]] = None,
                 dtype: Optional[str] = None) -> MemoryBlock:
        """Allocate memory block with size and device specification."""
        # Try to find suitable block in pool
        if self.enable_memory_pool:
            block = self._find_suitable_block(size, device)
            if block is not None:
                block.is_free = False
                block.tensor_shape = shape
                block.dtype = dtype
                return block
        
        # Allocate new block if no suitable found
        new_block = MemoryBlock(
            size=size,
            device=device,
            is_free=False,
            tensor_shape=shape,
            dtype=dtype
        )
        self.memory_pools[device].append(new_block)
        
        # Check fragmentation and defrag if needed
        if self._calculate_fragmentation(device) > self.fragmentation_threshold:
            self._defragment_memory(device)
            
        return new_block
    
    def free(self, block: MemoryBlock) -> None:
        """Free memory block and return to pool."""
        block.is_free = True
        block.tensor_shape = None
        block.dtype = None
        
        # Merge adjacent free blocks
        if self.enable_memory_pool:
            self._merge_adjacent_blocks(block.device)
    
    def _find_suitable_block(self, size: int, device: str) -> Optional[MemoryBlock]:
        """Find suitable free memory block in pool."""
        for block in self.memory_pools[device]:
            if block.is_free and block.size >= size:
                # Split block if significantly larger
                if block.size > size * 2:
                    remaining_size = block.size - size
                    block.size = size
                    new_block = MemoryBlock(
                        size=remaining_size,
                        device=device
                    )
                    self.memory_pools[device].append(new_block)
                return block
        return None
    
    def _calculate_fragmentation(self, device: str) -> float:
        """Calculate memory fragmentation ratio."""
        total_size = sum(block.size for block in self.memory_pools[device])
        free_blocks = [b for b in self.memory_pools[device] if b.is_free]
        total_free = sum(block.size for block in free_blocks)
        
        if total_size == 0:
            return 0.0
            
        return len(free_blocks) * total_free / total_size
    
    def _defragment_memory(self, device: str) -> None:
        """Defragment memory pool by consolidating free blocks."""
        # Sort blocks by address (simplified version)
        self.memory_pools[device].sort(key=lambda x: id(x))
        
        # Merge adjacent free blocks
        self._merge_adjacent_blocks(device)
    
    def _merge_adjacent_blocks(self, device: str) -> None:
        """Merge adjacent free memory blocks."""
        i = 0
        while i < len(self.memory_pools[device]) - 1:
            current = self.memory_pools[device][i]
            next_block = self.memory_pools[device][i + 1]
            
            if current.is_free and next_block.is_free:
                # Merge blocks
                current.size += next_block.size
                self.memory_pools[device].pop(i + 1)
            else:
                i += 1
    
    def get_memory_stats(self, device: str) -> Dict[str, Any]:
        """Get memory usage statistics."""
        total_size = sum(block.size for block in self.memory_pools[device])
        used_size = sum(block.size for block in self.memory_pools[device] 
                       if not block.is_free)
        free_size = total_size - used_size
        num_blocks = len(self.memory_pools[device])
        fragmentation = self._calculate_fragmentation(device)
        
        return {
            'total_size': total_size,
            'used_size': used_size,
            'free_size': free_size,
            'num_blocks': num_blocks,
            'fragmentation': fragmentation
        }
    
    def optimize_allocation(self, shapes: List[Tuple[int, ...]],
                          dtypes: List[str]) -> List[MemoryBlock]:
        """Optimize memory allocation for a sequence of tensor operations."""
        blocks = []
        current_offset = 0
        
        # Calculate sizes and alignments
        for shape, dtype in zip(shapes, dtypes):
            size = np.prod(shape) * np.dtype(dtype).itemsize
            # Align size to avoid false sharing
            aligned_size = (size + 63) & ~63  # 64-byte alignment
            
            block = self.allocate(aligned_size, 'cpu', shape, dtype)
            blocks.append(block)
            current_offset += aligned_size
            
        return blocks
    
    def release_tensors(self, tensor_ids: Set[int]) -> None:
        """Release memory for multiple tensors."""
        for tensor_id in tensor_ids:
            if tensor_id in self.active_tensors:
                self.free(self.active_tensors[tensor_id])
                del self.active_tensors[tensor_id]