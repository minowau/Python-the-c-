from typing import Dict, Any, Optional
from .base_fsm import BaseFSM

class StatementFSM(BaseFSM):
    """FSM for parsing control flow statements."""
    
    def __init__(self):
        super().__init__()
        self.statement_type = None
        self.condition = None
        self.body = []
        self.else_body = None
    
    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect statement keyword."""
        if token['type'] in ['IF', 'WHILE', 'FOR']:
            self.statement_type = token['type'].lower()
            self.state = 'expect_condition'
        else:
            self._set_error(f"Expected statement keyword, got {token['type']}")
    
    def _handle_expect_condition(self, token: Dict[str, Any]) -> None:
        """Handle state expecting condition expression."""
        if self.statement_type == 'for' and token['type'] == 'IDENTIFIER':
            self.condition = {
                'type': 'Identifier',
                'name': token['value']
            }
            self.state = 'expect_in'
        else:
            # Delegate to expression FSM for condition parsing
            from .expression_fsm import ExpressionFSM
            expr_fsm = ExpressionFSM()
            self.condition = expr_fsm.parse(self._parser)
            if self.condition:
                self.state = 'expect_colon'
    
    def _handle_expect_in(self, token: Dict[str, Any]) -> None:
        """Handle state expecting 'in' keyword in for loop."""
        if token['type'] == 'IN':
            self.state = 'expect_iterable'
        else:
            self._set_error(f"Expected 'in' keyword, got {token['type']}")
    
    def _handle_expect_iterable(self, token: Dict[str, Any]) -> None:
        """Handle state expecting iterable expression in for loop."""
        from .expression_fsm import ExpressionFSM
        expr_fsm = ExpressionFSM()
        self.condition = {
            'type': 'ForCondition',
            'variable': self.condition,
            'iterable': expr_fsm.parse(self._parser)
        }
        if self.condition['iterable']:
            self.state = 'expect_colon'
    
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
        """Handle state parsing statement body."""
        if token['type'] == 'DEDENT':
            self.state = 'expect_else'
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.body.append(statement)
    
    def _handle_expect_else(self, token: Dict[str, Any]) -> None:
        """Handle state expecting possible else clause."""
        if token['type'] == 'ELSE':
            self.state = 'expect_else_colon'
        else:
            self._finalize_statement()
    
    def _handle_expect_else_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon after else."""
        if token['type'] == 'COLON':
            self.state = 'expect_else_indent'
        else:
            self._set_error(f"Expected ':' after else, got {token['type']}")
    
    def _handle_expect_else_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting indentation for else body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_else_body'
        else:
            self._set_error(f"Expected indented block, got {token['type']}")
    
    def _handle_parse_else_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing else body."""
        if token['type'] == 'DEDENT':
            self._finalize_statement()
        else:
            if not self.else_body:
                self.else_body = []
            statement = self._parser._parse_statement()
            if statement:
                self.else_body.append(statement)
    
    def _finalize_statement(self) -> None:
        """Finalize statement parsing."""
        result = {
            'type': f'{self.statement_type.capitalize()}Statement',
            'condition': self.condition,
            'body': self.body
        }
        
        if self.else_body:
            result['else_body'] = self.else_body
        
        self._set_result(result)