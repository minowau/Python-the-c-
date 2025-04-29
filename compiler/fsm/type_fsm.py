from typing import Dict, Any, Optional
from .base_fsm import BaseFSM

class TypeFSM(BaseFSM):
    """FSM for parsing Python++ type annotations and definitions."""
    
    def __init__(self):
        super().__init__()
        self.type_stack = []
    
    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect type name or opening bracket."""
        if token['type'] == 'IDENTIFIER':
            self.type_stack.append({'type': 'SimpleType', 'name': token['value']})
            self.state = 'after_type'
        elif token['type'] == 'LBRACKET':
            self.type_stack.append({'type': 'GenericType', 'base': None, 'params': []})
            self.state = 'expect_base'
        else:
            self._set_error(f"Expected type name or '[', got {token['type']}")
    
    def _handle_expect_base(self, token: Dict[str, Any]) -> None:
        """Handle state after opening bracket - expect base type name."""
        if token['type'] == 'IDENTIFIER':
            current = self.type_stack[-1]
            current['base'] = token['value']
            self.state = 'expect_type_param'
        else:
            self._set_error(f"Expected type name, got {token['type']}")
    
    def _handle_expect_type_param(self, token: Dict[str, Any]) -> None:
        """Handle state expecting type parameter."""
        if token['type'] == 'IDENTIFIER':
            current = self.type_stack[-1]
            current['params'].append({'type': 'SimpleType', 'name': token['value']})
            self.state = 'after_type_param'
        elif token['type'] == 'RBRACKET':
            self._finalize_type()
        else:
            self._set_error(f"Expected type parameter or ']', got {token['type']}")
    
    def _handle_after_type_param(self, token: Dict[str, Any]) -> None:
        """Handle state after type parameter."""
        if token['type'] == 'COMMA':
            self.state = 'expect_type_param'
        elif token['type'] == 'RBRACKET':
            self._finalize_type()
        else:
            self._set_error(f"Expected ',' or ']', got {token['type']}")
    
    def _handle_after_type(self, token: Dict[str, Any]) -> None:
        """Handle state after type name."""
        if token['type'] == 'OPERATOR' and token['value'] == '->':
            self.state = 'expect_return_type'
        else:
            self._finalize_type()
            # Don't consume this token
            self.transition(token)
    
    def _handle_expect_return_type(self, token: Dict[str, Any]) -> None:
        """Handle state expecting return type after '->'."""
        if token['type'] == 'IDENTIFIER':
            return_type = {'type': 'SimpleType', 'name': token['value']}
            current = self.type_stack.pop()
            self._set_result({
                'type': 'FunctionType',
                'param_type': current,
                'return_type': return_type
            })
        else:
            self._set_error(f"Expected return type, got {token['type']}")
    
    def _finalize_type(self) -> None:
        """Finalize type parsing and set result."""
        if self.type_stack:
            self._set_result(self.type_stack.pop())
        else:
            self._set_error("No type information available")