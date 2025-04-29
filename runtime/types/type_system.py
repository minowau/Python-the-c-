from typing import Dict, Any, Optional, List, Set, Tuple, Union
from dataclasses import dataclass
import numpy as np

@dataclass
class TypeInfo:
    """Type information for Python++ variables and expressions."""
    name: str
    cpp_type: str
    python_type: type
    is_primitive: bool
    methods: Dict[str, 'FunctionType']
    fields: Dict[str, 'TypeInfo']
    shape: Optional[Tuple[int, ...]] = None  # For tensor types
    dtype: Optional[str] = None  # For numeric/tensor types
    device: Optional[str] = None  # CPU/GPU specification

@dataclass
class FunctionType:
    """Type information for functions."""
    param_types: List[TypeInfo]
    return_type: TypeInfo
    is_method: bool

class TypeSystem:
    """Type system for Python++ with static inference and C++ bridging."""
    
    def __init__(self):
        self.types: Dict[str, TypeInfo] = {}
        self.type_cache: Dict[str, TypeInfo] = {}
        self._initialize_primitive_types()
    
    def _initialize_primitive_types(self) -> None:
        """Initialize built-in primitive types including ML-specific types."""
        self.types.update({
            'int': TypeInfo(
                name='int',
                cpp_type='int64_t',
                python_type=int,
                is_primitive=True,
                methods={},
                fields={}
            ),
            'float': TypeInfo(
                name='float',
                cpp_type='double',
                python_type=float,
                is_primitive=True,
                methods={},
                fields={}
            ),
            'bool': TypeInfo(
                name='bool',
                cpp_type='bool',
                python_type=bool,
                is_primitive=True,
                methods={},
                fields={}
            ),
            'str': TypeInfo(
                name='str',
                cpp_type='std::string',
                python_type=str,
                is_primitive=True,
                methods={},
                fields={}
            ),
            'None': TypeInfo( # Add NoneType
                name='None',
                cpp_type='std::nullptr_t', # Or appropriate C++ representation
                python_type=type(None),
                is_primitive=True,
                methods={},
                fields={}
            ),
            'tensor': TypeInfo(
                name='tensor',
                cpp_type='torch::Tensor',
                python_type=np.ndarray,
                is_primitive=False,
                methods={
                    'reshape': FunctionType(
                        param_types=[self.types['int']],
                        return_type=None,  # Will be set to self-reference after creation
                        is_method=True
                    ),
                    'transpose': FunctionType(
                        param_types=[],
                        return_type=None,  # Will be set to self-reference after creation
                        is_method=True
                    )
                },
                fields={},
                shape=None,
                dtype='float32',
                device='cpu'
            ),
            # Add a generic 'Any' type for flexibility
            'Any': TypeInfo(
                name='Any',
                cpp_type='std::any', # Example C++ equivalent
                python_type=Any,
                is_primitive=False,
                methods={},
                fields={}
            ),
            'half': TypeInfo(
                name='half',
                cpp_type='half',
                python_type=float,
                is_primitive=True,
                methods={},
                fields={},
                dtype='float16'
            )
        })
        
        # Set self-referential return types for tensor methods
        self.types['tensor'].methods['reshape'].return_type = self.types['tensor']
        self.types['tensor'].methods['transpose'].return_type = self.types['tensor']
    
    def infer_type(self, node: Dict[str, Any], context: Dict[str, TypeInfo]) -> TypeInfo:
        """Infer type of AST node.
        
        Args:
            node: AST node
            context: Type context including variable types
            
        Returns:
            Inferred type information
        """
        if node['type'] == 'Literal':
            return self._infer_literal_type(node)
        elif node['type'] == 'BinaryOp':
            return self._infer_binary_op_type(node, context)
        elif node['type'] == 'Identifier': # Match parser AST type
            return self._infer_variable_type(node, context)
        elif node['type'] == 'UnaryOp':
            return self._infer_unary_op_type(node, context)
        elif node['type'] == 'FunctionCall':
            return self._infer_call_type(node, context)
        elif node['type'] == 'FunctionDefinition': # Added for completeness
            # Type inference for function definition itself might return a FunctionType
            # This needs more context about how functions are stored/represented
            pass # Placeholder
        else:
            # Return 'Any' or raise error for unhandled types
            # raise Exception(f"Cannot infer type for node: {node['type']}")
            print(f"[Warning] Cannot infer type for node: {node['type']}, returning Any")
            return self.types.get('Any', TypeInfo(name='Any', cpp_type='std::any', python_type=Any, is_primitive=False, methods={}, fields={})) # Fallback
    
    def _infer_literal_type(self, node: Dict[str, Any]) -> TypeInfo:
        """Infer type of literal value."""
        value = node['value']
        if isinstance(value, int):
            return self.types['int']
        elif isinstance(value, float):
            return self.types['float']
        elif isinstance(value, bool):
            return self.types['bool']
        elif isinstance(value, str):
            return self.types['str']
        elif value is None:
             return self.types['None']
        else:
            raise Exception(f"Unsupported literal type: {type(value)}")
    
    def _infer_binary_op_type(self, node: Dict[str, Any], context: Dict[str, TypeInfo]) -> TypeInfo:
        """Infer result type of binary operation including tensor operations."""
        left_type = self.infer_type(node['left'], context)
        right_type = self.infer_type(node['right'], context)
        
        # Handle tensor operations
        if left_type.name == 'tensor' or right_type.name == 'tensor':
            if node['operator'] in ['+', '-', '*', '/']:
                # Broadcasting rules - return tensor with appropriate shape
                result_type = self.types['tensor']
                result_type.shape = self._infer_broadcast_shape(left_type, right_type)
                return result_type
            elif node['operator'] in ['@']:  # Matrix multiplication
                return self._infer_matmul_type(left_type, right_type)
            elif node['operator'] in ['==', '!=', '<', '>', '<=', '>=']:
                return self.types['tensor']  # Element-wise comparison returns boolean tensor
        
        # Standard numeric type promotion
        if left_type.name == 'float' or right_type.name == 'float':
            return self.types['float']
        elif left_type.name == 'int' and right_type.name == 'int':
            return self.types['int']
        elif node['operator'] in ['==', '!=', '<', '>', '<=', '>=']:
            return self.types['bool']
        elif node['operator'] in ['and', 'or']:
             # Assume boolean logic returns bool
             return self.types['bool']
        else:
            raise Exception(f"Invalid operation '{node['operator']}' between types: {left_type.name} and {right_type.name}")

    def _infer_unary_op_type(self, node: Dict[str, Any], context: Dict[str, TypeInfo]) -> TypeInfo:
        """Infer result type of unary operation."""
        operand_type = self.infer_type(node['operand'], context)
        op = node['operator']

        if op == 'not':
            return self.types['bool']
        elif op in ['+', '-']:
            # Assume numeric unary ops preserve type (int->int, float->float)
            if operand_type.name in ['int', 'float', 'tensor', 'half']:
                return operand_type
            else:
                raise Exception(f"Unary '{op}' not supported for type {operand_type.name}")
        # TODO: Add other unary ops like '~'
        else:
            raise Exception(f"Unsupported unary operator: {op}")
    
    def _infer_variable_type(self, node: Dict[str, Any], context: Dict[str, TypeInfo]) -> TypeInfo:
        """Infer type of variable reference."""
        var_name = node['name']
        if var_name in context:
            return context[var_name]
        else:
            # Check for built-in functions/types if not in local context
            if var_name in self.types:
                 # This might need refinement - is it a type name or a function?
                 # For now, assume it refers to the type itself if used as a variable
                 return self.types[var_name]
            raise Exception(f"Undefined variable: {var_name}")
    
    def _infer_call_type(self, node: Dict[str, Any], context: Dict[str, TypeInfo]) -> TypeInfo:
        """Infer return type of function call."""
        func_name = node['callee']['name']
        if func_name in context and isinstance(context[func_name], FunctionType):
            return context[func_name].return_type
        else:
            raise Exception(f"Undefined function: {func_name}")
    
    def register_class(self, name: str, fields: Dict[str, TypeInfo], methods: Dict[str, FunctionType]) -> None:
        """Register new class type."""
        self.types[name] = TypeInfo(
            name=name,
            cpp_type=f"class_{name}",  # Could be customized
            python_type=type(name, (), {}),  # Dynamic type creation
            is_primitive=False,
            methods=methods,
            fields=fields
        )
    
    def get_cpp_type(self, type_info: TypeInfo) -> str:
        """Get C++ type representation."""
        return type_info.cpp_type
    
    def validate_assignment(self, target_type: TypeInfo, value_type: TypeInfo) -> bool:
        """Validate type compatibility for assignment including tensor operations."""
        # Direct type match
        if target_type.name == value_type.name:
            if target_type.name == 'tensor':
                # Validate tensor shape compatibility
                return self._validate_tensor_shapes(target_type, value_type)
            return True
            
        # Numeric type promotions
        if target_type.name == 'float' and value_type.name == 'int':
            return True
        elif target_type.name == 'tensor':
            # Allow scalar to tensor broadcast
            return value_type.name in ['int', 'float', 'half']
            
        return False
        
    def _validate_tensor_shapes(self, target: TypeInfo, value: TypeInfo) -> bool:
        """Validate tensor shape compatibility for assignment."""
        if target.shape is None or value.shape is None:
            return True  # Dynamic shapes are always compatible
            
        if len(target.shape) != len(value.shape):
            return False
            
        for t, v in zip(target.shape, value.shape):
            if t != v and t != -1:  # -1 indicates dynamic dimension
                return False
        return True
        
    def _infer_broadcast_shape(self, left: TypeInfo, right: TypeInfo) -> Optional[Tuple[int, ...]]:
        """Infer resulting shape after broadcasting."""
        if left.shape is None or right.shape is None:
            return None
            
        # Implement numpy-style broadcasting rules
        left_shape = left.shape[::-1]  # Reverse for broadcasting
        right_shape = right.shape[::-1]
        result_shape = []
        
        for l, r in zip(left_shape, right_shape):
            result_shape.append(max(l, r))
            
        return tuple(result_shape[::-1])  # Reverse back
        
    def _infer_matmul_type(self, left: TypeInfo, right: TypeInfo) -> TypeInfo:
        """Infer resulting type and shape for matrix multiplication."""
        result = self.types['tensor']
        
        if left.shape is None or right.shape is None:
            result.shape = None
            return result
            
        # Basic matrix multiplication shape inference
        if len(left.shape) == 2 and len(right.shape) == 2:
            if left.shape[1] != right.shape[0]:
                raise Exception(f"Invalid shapes for matrix multiplication: {left.shape} and {right.shape}")
            result.shape = (left.shape[0], right.shape[1])
            
        return result
    def add(self, other: 'Tensor') -> 'Tensor':
            # Basic implementation, replace with optimized version
            if self.shape != other.shape:
                raise ValueError("Shapes must match for element-wise addition")
            # Placeholder for actual optimized operation
            result_data = np.add(self.data, other.data) # Example using numpy
            return Tensor(result_data)

    def multiply(self, other: 'Tensor') -> 'Tensor':
            # Basic implementation, replace with optimized version
            if self.shape != other.shape:
                raise ValueError("Shapes must match for element-wise multiplication")
            # Placeholder for actual optimized operation
            result_data = np.multiply(self.data, other.data) # Example using numpy
            return Tensor(result_data)

        # TODO: Add more optimized tensor operations (matmul, transpose, etc.)