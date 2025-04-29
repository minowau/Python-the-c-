from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass
import llvmlite.binding as llvm
import llvmlite.ir as ir
from .types.type_system import TypeInfo

@dataclass
class JITFunction:
    """Represents a JIT-compiled function."""
    ir_module: ir.Module
    compiled_function: Callable
    arg_types: List[TypeInfo]
    return_type: TypeInfo
    optimization_level: int

class JITCompiler:
    """JIT compiler using LLVM for code generation and optimization."""
    
    def __init__(self):
        # Initialize LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Create execution engine
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        self.engine = llvm.create_execution_engine(target_machine)
        
        # Initialize optimization passes
        self.pass_manager = llvm.create_module_pass_manager()
        
        # Cache for compiled functions
        self.function_cache: Dict[str, JITFunction] = {}
    
    def compile_function(self, ast_node: Dict[str, Any], 
                        arg_types: List[TypeInfo],
                        return_type: TypeInfo,
                        optimization_level: int = 2) -> Callable:
        """Compile AST node to machine code using LLVM."""
        # Generate cache key
        cache_key = self._generate_cache_key(ast_node, arg_types, return_type)
        
        # Check cache
        if cache_key in self.function_cache:
            return self.function_cache[cache_key].compiled_function
        
        # Create new LLVM module
        module = ir.Module()
        
        # Generate LLVM IR
        ir_function = self._generate_ir(module, ast_node, arg_types, return_type)
        
        # Optimize IR
        if optimization_level > 0:
            self._optimize_ir(module, optimization_level)
        
        # Compile to machine code
        compiled_func = self._compile_ir(module, ir_function)
        
        # Cache the result
        self.function_cache[cache_key] = JITFunction(
            ir_module=module,
            compiled_function=compiled_func,
            arg_types=arg_types,
            return_type=return_type,
            optimization_level=optimization_level
        )
        
        return compiled_func
    
    def _generate_ir(self, module: ir.Module, ast_node: Dict[str, Any],
                     arg_types: List[TypeInfo], return_type: TypeInfo) -> ir.Function:
        """Generate LLVM IR from AST node."""
        # Convert Python types to LLVM types
        llvm_arg_types = [self._type_to_llvm(t) for t in arg_types]
        llvm_return_type = self._type_to_llvm(return_type)
        
        # Create function type
        func_type = ir.FunctionType(llvm_return_type, llvm_arg_types)
        
        # Create function
        func = ir.Function(module, func_type, name="jit_func")
        
        # Create entry block
        block = func.append_basic_block(name="entry")
        builder = ir.IRBuilder(block)
        
        # Generate IR for function body
        result = self._generate_node_ir(builder, ast_node, {})
        
        # Add return instruction
        builder.ret(result)
        
        return func
    
    def _generate_node_ir(self, builder: ir.IRBuilder, 
                         node: Dict[str, Any],
                         symbol_table: Dict[str, ir.Value]) -> ir.Value:
        """Generate IR for AST node."""
        # TODO: Add handling for more AST node types (e.g., function calls, assignments)
        if node['type'] == 'BinaryOp':
            return self._generate_binary_op_ir(builder, node, symbol_table)
        elif node['type'] == 'Literal':
            return self._generate_literal_ir(builder, node)
        elif node['type'] == 'Variable':
            return self._generate_variable_ir(builder, node, symbol_table)
        # TODO: Add IR generation for complex types (lists, dicts, objects)
        else:
            raise Exception(f"Unsupported node type for JIT: {node['type']}")
    
    def _generate_binary_op_ir(self, builder: ir.IRBuilder,
                              node: Dict[str, Any],
                              symbol_table: Dict[str, ir.Value]) -> ir.Value:
        """Generate IR for binary operation."""
        left = self._generate_node_ir(builder, node['left'], symbol_table)
        right = self._generate_node_ir(builder, node['right'], symbol_table)
        
        op = node['operator']
        if op == '+':
            return builder.add(left, right)
        elif op == '-':
            return builder.sub(left, right)
        elif op == '*':
            return builder.mul(left, right)
        elif op == '/':
            return builder.sdiv(left, right)
        else:
            raise Exception(f"Unsupported binary operator for JIT: {op}")
    
    def _generate_literal_ir(self, builder: ir.IRBuilder,
                           node: Dict[str, Any]) -> ir.Value:
        """Generate IR for literal value."""
        value = node['value']
        if isinstance(value, int):
            return ir.Constant(ir.IntType(64), value)
        elif isinstance(value, float):
            return ir.Constant(ir.DoubleType(), value)
        else:
            raise Exception(f"Unsupported literal type for JIT: {type(value)}")
    
    def _generate_variable_ir(self, builder: ir.IRBuilder,
                             node: Dict[str, Any],
                             symbol_table: Dict[str, ir.Value]) -> ir.Value:
        """Generate IR for variable reference."""
        var_name = node['name']
        if var_name not in symbol_table:
            raise Exception(f"Undefined variable in JIT: {var_name}")
        return symbol_table[var_name]
    
    def _type_to_llvm(self, type_info: TypeInfo) -> ir.Type:
        """Convert Python++ type to LLVM type."""
        if type_info.name == 'int':
            return ir.IntType(64)
        elif type_info.name == 'float':
            return ir.DoubleType()
        elif type_info.name == 'bool':
            return ir.IntType(1)
        # Placeholder for complex types
        elif type_info.name in ['list', 'dict', 'object', 'str']: # Added str as well
            # TODO: Implement proper handling for complex types (e.g., pointers to structs)
            # For now, raise an error or return a placeholder (like void pointer)
            # return ir.IntType(8).as_pointer() # Example: void*
            raise Exception(f"JIT compilation for complex type '{type_info.name}' not yet implemented.")
        else:
            raise Exception(f"Unsupported type for JIT: {type_info.name}")
    
    def _optimize_ir(self, module: ir.Module, level: int) -> None:
        """Apply LLVM optimization passes."""
        # Add optimization passes based on level
        if level >= 1:
            self.pass_manager.add_instruction_combining_pass()
            self.pass_manager.add_reassociate_pass()
        if level >= 2:
            self.pass_manager.add_gvn_pass()
            self.pass_manager.add_cfg_simplification_pass()
        if level >= 3:
            self.pass_manager.add_loop_vectorize_pass()
            self.pass_manager.add_slp_vectorize_pass()
        
        # Run optimization passes
        self.pass_manager.run(module)
    
    def _compile_ir(self, module: ir.Module, ir_function: ir.Function) -> Callable:
        """Compile LLVM IR to machine code."""
        # Convert IR to machine code
        compiled = self.engine.compile_ir(module)
        
        # Get function pointer
        func_ptr = self.engine.get_function_address(ir_function.name)
        
        # Create Python callable
        return self._create_python_wrapper(func_ptr)
    
    def _create_python_wrapper(self, func_ptr: int) -> Callable:
        """Create Python callable from function pointer."""
        # This is a simplified version - actual implementation would need proper
        # argument marshalling and return type conversion
        def wrapper(*args):
            return func_ptr(*args)
        return wrapper
    
    def _generate_cache_key(self, ast_node: Dict[str, Any],
                           arg_types: List[TypeInfo],
                           return_type: TypeInfo) -> str:
        """Generate cache key for compiled function."""
        # Create unique key based on AST and types
        key_parts = [
            str(ast_node),
            ','.join(t.name for t in arg_types),
            return_type.name
        ]
        return '|'.join(key_parts)