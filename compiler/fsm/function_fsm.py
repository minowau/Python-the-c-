from typing import Dict, Any, Optional, List
from .base_fsm import BaseFSM

class FunctionFSM(BaseFSM):
    """FSM for parsing function and class definitions."""
    
    def __init__(self):
        super().__init__()
        self.def_type = None  # 'function' or 'class'
        self.name = None
        self.params: List[Dict[str, Any]] = []
        self.body = []
        self.decorators = []
        self.current_param = None
    
    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect def or class keyword."""
        if token['type'] == 'DEF':
            self.def_type = 'function'
            self.state = 'expect_name'
        elif token['type'] == 'CLASS':
            self.def_type = 'class'
            self.state = 'expect_name'
        else:
            self._set_error(f"Expected 'def' or 'class', got {token['type']}")
    
    def _handle_expect_name(self, token: Dict[str, Any]) -> None:
        """Handle state expecting function/class name."""
        if token['type'] == 'IDENTIFIER':
            self.name = token['value']
            self.state = 'expect_params' if self.def_type == 'function' else 'expect_colon'
        else:
            self._set_error(f"Expected identifier, got {token['type']}")
    
    def _handle_expect_params(self, token: Dict[str, Any]) -> None:
        """Handle state expecting parameter list."""
        if token['type'] == 'LPAREN':
            self.state = 'parse_params'
        else:
            self._set_error(f"Expected '(', got {token['type']}")
    
    def _handle_parse_params(self, token: Dict[str, Any]) -> None:
        """Handle state parsing parameter list."""
        if token['type'] == 'RPAREN':
            self.state = 'expect_colon'
        elif token['type'] == 'IDENTIFIER':
            self.current_param = {
                'type': 'Parameter',
                'name': token['value'],
                'default_value': None
            }
            self.state = 'expect_param_separator'
        elif token['type'] == 'COMMA':
            if not self.current_param:
                self._set_error("Unexpected comma in parameter list")
        else:
            self._set_error(f"Unexpected token in parameter list: {token['type']}")
    
    def _handle_expect_param_separator(self, token: Dict[str, Any]) -> None:
        """Handle state expecting parameter separator or default value."""
        if token['type'] == 'COMMA':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'parse_params'
        elif token['type'] == 'OPERATOR' and token['value'] == '=':
            self.state = 'parse_default_value'
        elif token['type'] == 'RPAREN':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'expect_colon'
        else:
            self._set_error(f"Expected ',' or '=', got {token['type']}")
    
    def _handle_parse_default_value(self, token: Dict[str, Any]) -> None:
        """Handle state parsing parameter default value."""
        from .expression_fsm import ExpressionFSM
        expr_fsm = ExpressionFSM()
        default_value = expr_fsm.parse(self._parser)
        if default_value:
            self.current_param['default_value'] = default_value
            self.params.append(self.current_param)
            self.current_param = None
            self.state = 'parse_params'
    
    def _handle_expect_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon before body."""
        if token['type'] == 'COLON':
            self.state = 'expect_indent'
        else:
            self._set_error(f"Expected ':', got {token['type']}")
    
    def _handle_expect_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting indentation for body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_body'
        else:
            self._set_error(f"Expected indented block, got {token['type']}")
    
    def _handle_parse_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing function/class body."""
        if token['type'] == 'DEDENT':
            self._finalize_definition()
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.body.append(statement)
    
    def _finalize_definition(self) -> None:
        """Finalize function/class definition parsing."""
        result = {
            'type': 'FunctionDefinition' if self.def_type == 'function' else 'ClassDefinition',
            'name': self.name,
            'body': self.body
        }
        
        if self.def_type == 'function':
            result['params'] = self.params
        
        if self.decorators:
            result['decorators'] = self.decorators
        
        self._set_result(result)