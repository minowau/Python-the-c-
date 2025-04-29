from typing import Dict, Any, List, Union, Optional
import numpy as np

class ASTOptimizer:
    """AST optimization passes for Python++."""
    
    def __init__(self):
        self.optimizations = [
            self._constant_folding,
            self._dead_code_elimination,
            self._expression_simplification,
            self._matrix_operation_optimization,
            self._numerical_stability_optimization
        ]
    
    def optimize(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all optimization passes to AST.
        
        Args:
            ast: Abstract Syntax Tree
            
        Returns:
            Optimized AST
        """
        for optimization in self.optimizations:
            ast = optimization(ast)
        return ast
    
    def _constant_folding(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Fold constant expressions at compile time."""
        if isinstance(ast, dict):
            if ast.get('type') == 'BinaryOp':
                left = self._constant_folding(ast['left'])
                right = self._constant_folding(ast['right'])
                
                if (left.get('type') == 'Literal' and 
                    right.get('type') == 'Literal'):
                    try:
                        result = self._evaluate_constant_expression(
                            left['value'],
                            right['value'],
                            ast['operator']
                        )
                        return {
                            'type': 'Literal',
                            'value': result
                        }
                    except:
                        # If evaluation fails, return original node
                        ast['left'] = left
                        ast['right'] = right
                        return ast
                else:
                    ast['left'] = left
                    ast['right'] = right
            
            # Recursively process all node fields
            for key, value in ast.items():
                if isinstance(value, (dict, list)):
                    ast[key] = self._constant_folding(value)
        
        elif isinstance(ast, list):
            return [self._constant_folding(node) for node in ast]
        
        return ast
    
    def _dead_code_elimination(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Eliminate unreachable and redundant code."""
        if isinstance(ast, dict):
            if ast.get('type') == 'If':
                condition = ast['condition']
                if condition.get('type') == 'Literal':
                    # If condition is constant, eliminate dead branch
                    if condition['value']:
                        return self._dead_code_elimination(ast['consequent'])
                    elif 'alternate' in ast:
                        return self._dead_code_elimination(ast['alternate'])
                    else:
                        return {'type': 'EmptyStatement'}
            
            # Recursively process all node fields
            for key, value in ast.items():
                if isinstance(value, (dict, list)):
                    ast[key] = self._dead_code_elimination(value)
        
        elif isinstance(ast, list):
            # Filter out empty statements
            return [self._dead_code_elimination(node) for node in ast 
                    if node.get('type') != 'EmptyStatement']
        
        return ast
    
    def _expression_simplification(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify complex expressions."""
        if isinstance(ast, dict):
            if ast.get('type') == 'BinaryOp':
                # Simplify x + 0, x * 1, etc.
                ast['left'] = self._expression_simplification(ast['left'])
                ast['right'] = self._expression_simplification(ast['right'])
                
                left = ast['left']
                right = ast['right']
                op = ast['operator']
                
                if right.get('type') == 'Literal':
                    if op == '+' and right['value'] == 0:
                        return left
                    elif op == '*' and right['value'] == 1:
                        return left
                    elif op == '*' and right['value'] == 0:
                        return {'type': 'Literal', 'value': 0}
                    elif op == '@' and right['value'] == 1:
                        return left  # Identity matrix multiplication
                
                if left.get('type') == 'Literal':
                    if op == '+' and left['value'] == 0:
                        return right
                    elif op == '*' and left['value'] == 1:
                        return right
                    elif op == '*' and left['value'] == 0:
                        return {'type': 'Literal', 'value': 0}
                    elif op == '@' and left['value'] == 1:
                        return right  # Identity matrix multiplication
            
            # Recursively process all node fields
            for key, value in ast.items():
                if isinstance(value, (dict, list)):
                    ast[key] = self._expression_simplification(value)
        
        elif isinstance(ast, list):
            return [self._expression_simplification(node) for node in ast]
        
        return ast
    
    def _matrix_operation_optimization(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize matrix operations for better performance."""
        if isinstance(ast, dict):
            if ast.get('type') == 'BinaryOp' and ast['operator'] == '@':
                # Check for matrix multiplication chain
                if ast['left'].get('type') == 'BinaryOp' and ast['left']['operator'] == '@':
                    # Reorder matrix multiplications for optimal performance
                    # (AB)C -> A(BC) if dimensions are compatible
                    try:
                        dims = self._get_matrix_dimensions(ast)
                        if dims and self._should_reorder_matmul(dims):
                            return self._reorder_matrix_multiplication(ast)
                    except:
                        pass
            
            # Recursively process all node fields
            for key, value in ast.items():
                if isinstance(value, (dict, list)):
                    ast[key] = self._matrix_operation_optimization(value)
        
        elif isinstance(ast, list):
            return [self._matrix_operation_optimization(node) for node in ast]
        
        return ast
    
    def _numerical_stability_optimization(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize numerical operations for better stability."""
        if isinstance(ast, dict):
            if ast.get('type') == 'BinaryOp':
                op = ast['operator']
                if op in ['/', '**']:
                    # Add checks for numerical stability
                    ast = self._add_numerical_stability_checks(ast)
                elif op == '-':
                    # Avoid catastrophic cancellation in subtraction
                    ast = self._optimize_subtraction(ast)
            
            # Recursively process all node fields
            for key, value in ast.items():
                if isinstance(value, (dict, list)):
                    ast[key] = self._numerical_stability_optimization(value)
        
        elif isinstance(ast, list):
            return [self._numerical_stability_optimization(node) for node in ast]
        
        return ast
    
    def _get_matrix_dimensions(self, ast: Dict[str, Any]) -> Optional[List[tuple]]:
        """Get dimensions of matrices in multiplication chain."""
        try:
            if ast.get('type') == 'Literal' and isinstance(ast['value'], np.ndarray):
                return ast['value'].shape
            return None
        except:
            return None
    
    def _should_reorder_matmul(self, dims: List[tuple]) -> bool:
        """Determine if matrix multiplication should be reordered."""
        if len(dims) < 3:
            return False
        # Add logic to determine optimal multiplication order
        return True
    
    def _reorder_matrix_multiplication(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Reorder matrix multiplication for optimal performance."""
        # Implementation of matrix multiplication reordering
        return ast
    
    def _add_numerical_stability_checks(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Add checks for numerical stability."""
        # Add implementation for numerical stability checks
        return ast
    
    def _optimize_subtraction(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize subtraction to avoid catastrophic cancellation."""
        # Add implementation for subtraction optimization
        return ast

    def _evaluate_constant_expression(self, left: Any, right: Any, operator: str) -> Any:
        """Evaluate constant expression at compile time."""
        if operator == '+':
            return left + right
        elif operator == '-':
            return left - right
        elif operator == '*':
            return left * right
        elif operator == '/':
            # Add numerical stability for division
            if isinstance(right, (int, float)) and abs(right) < 1e-10:
                raise Exception("Division by near-zero value")
            return left / right
        elif operator == '%':
            return left % right
        elif operator == '**':
            # Add numerical stability for exponentiation
            if isinstance(right, (int, float)) and right < 0 and left == 0:
                raise Exception("Invalid exponentiation: zero base with negative exponent")
            return left ** right
        elif operator == '@':
            # Matrix multiplication
            if hasattr(left, '__matmul__'):
                return left @ right
            raise Exception("Matrix multiplication not supported for these types")
        else:
            raise Exception(f"Unsupported operator for constant folding: {operator}")