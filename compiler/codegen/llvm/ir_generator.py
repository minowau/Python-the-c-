from typing import Dict, Any, Optional
from llvmlite import ir
from llvmlite import binding as llvm

class LLVMIRGenerator:
    """LLVM IR Generator for Python++ AST nodes."""
    
    def __init__(self):
        # Initialize LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Create module and engine
        self.module = ir.Module(name="python++_module")
        self.builder = None
        self.func = None
        self.target_machine = self._create_target_machine()
        
        # Type mappings
        self.type_map = {
            'int': ir.IntType(64),
            'float': ir.DoubleType(),
            'bool': ir.IntType(1),
            'str': ir.ArrayType(ir.IntType(8), 1),  # Simple string representation
        }
    
    def _create_target_machine(self):
        """Create native target machine."""
        target = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine()
        return target_machine
    
    def generate(self, ast: Dict[str, Any]) -> Optional[llvm.ModuleRef]:
        """Generate LLVM IR from AST.
        
        Args:
            ast: Abstract Syntax Tree
            
        Returns:
            Compiled LLVM module
        """
        try:
            # Create main function
            func_type = ir.FunctionType(ir.VoidType(), [])
            self.func = ir.Function(self.module, func_type, name="main")
            block = self.func.append_basic_block(name="entry")
            self.builder = ir.IRBuilder(block)
            
            # Generate IR for each statement
            for node in ast['body']:
                self._generate_node(node)
            
            # Add return void
            self.builder.ret_void()
            
            # Verify and optimize module
            llvm_ir = str(self.module)
            mod = llvm.parse_assembly(llvm_ir)
            mod.verify()
            
            # Optimize
            pmb = llvm.create_pass_manager_builder()
            pmb.opt_level = 2
            pm = llvm.create_module_pass_manager()
            pmb.populate(pm)
            pm.run(mod)
            
            return mod
            
        except Exception as e:
            print(f"IR Generation error: {str(e)}")
            return None
    
    def _generate_node(self, node: Dict[str, Any]) -> Optional[ir.Value]:
        """Generate IR for a single AST node.
        
        Args:
            node: AST node to generate IR for
            
        Returns:
            LLVM IR Value or None
        """
        generator = getattr(self, f'_generate_{node["type"].lower()}', None)
        if generator:
            return generator(node)
        else:
            raise Exception(f"Unsupported node type: {node['type']}")
    
    def _generate_binop(self, node: Dict[str, Any]) -> ir.Value:
        """Generate IR for binary operation."""
        left = self._generate_node(node['left'])
        right = self._generate_node(node['right'])
        
        op = node['operator']
        if op == '+':
            return self.builder.add(left, right)
        elif op == '-':
            return self.builder.sub(left, right)
        elif op == '*':
            return self.builder.mul(left, right)
        elif op == '/':
            return self.builder.sdiv(left, right)
        else:
            raise Exception(f"Unsupported binary operator: {op}")
    
    def _generate_number(self, node: Dict[str, Any]) -> ir.Constant:
        """Generate IR for numeric literal."""
        if isinstance(node['value'], int):
            return ir.Constant(ir.IntType(64), node['value'])
        else:
            return ir.Constant(ir.DoubleType(), node['value'])
    
    def _generate_variable(self, node: Dict[str, Any]) -> Optional[ir.Value]:
        """Generate IR for variable reference."""
        # Implementation depends on symbol table and scope management
        pass
    
    def _generate_function(self, node: Dict[str, Any]) -> Optional[ir.Function]:
        """Generate IR for function definition."""
        # Save current context
        old_builder = self.builder
        old_func = self.func
        
        # Create function
        func_name = node['name']
        return_type = self.type_map.get(node['return_type'], ir.VoidType())
        param_types = [self.type_map.get(p['type'], ir.VoidType()) for p in node['params']]
        func_type = ir.FunctionType(return_type, param_types)
        func = ir.Function(self.module, func_type, name=func_name)
        
        # Create entry block
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.func = func
        
        # Generate body
        for stmt in node['body']:
            self._generate_node(stmt)
        
        # Restore context
        self.builder = old_builder
        self.func = old_func
        
        return func