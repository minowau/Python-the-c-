from typing import List, Optional, Dict, Any
from .lexer import token, tokenize
from .fsm.base_fsm import BaseFSM
from .fsm.expression_fsm import ExpressionFSM
from .fsm.statement_fsm import StatementFSM
from .fsm.function_fsm import FunctionFSM

class Parser:
    def __init__(self):
        self.tokens: List[Dict[str, Any]] = []
        self.current_pos = 0
        self.symbol_table: Dict[str, Any] = {}
        
        # Initialize FSM components
        self.base_fsm = BaseFSM()
        self.expr_fsm = ExpressionFSM()
        self.stmt_fsm = StatementFSM()
        self.func_fsm = FunctionFSM()
    
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code into an AST using FSM-based approach."""
        self.tokens = tokenize(source_code)
        self.current_pos = 0
        
        # Initialize AST root node
        ast = {
            'type': 'Program',
            'body': []
        }
        
        while not self._is_at_end():
            statement = self._parse_statement()
            if statement:
                ast['body'].append(statement)
        
        return ast
    
    def _parse_statement(self) -> Optional[Dict[str, Any]]:
        """Parse a single statement using appropriate FSM."""
        token = self._peek()
        
        # Delegate to appropriate FSM based on token type
        if token['type'] in ['DEF', 'CLASS']:
            return self.func_fsm.parse(self)
        elif token['type'] in ['IF', 'WHILE', 'FOR']:
            return self.stmt_fsm.parse(self)
        else:
            return self.expr_fsm.parse(self)
    
    def _peek(self, offset: int = 0) -> Dict[str, Any]:
        """Look ahead in token stream without consuming."""
        if self.current_pos + offset >= len(self.tokens):
            return self.tokens[-1]  # Return EOF token
        return self.tokens[self.current_pos + offset]
    
    def _advance(self) -> Dict[str, Any]:
        """Consume and return current token."""
        if not self._is_at_end():
            self.current_pos += 1
        return self.tokens[self.current_pos - 1]
    
    def _is_at_end(self) -> bool:
        """Check if we've reached end of token stream."""
        return self._peek()['type'] == 'EOF'
    
    def _match(self, *types: str) -> bool:
        """Check if current token matches any of given types."""
        for type_ in types:
            if self._check(type_):
                self._advance()
                return True
        return False
    
    def _check(self, type_: str) -> bool:
        """Check if current token is of given type."""
        if self._is_at_end():
            return False
        return self._peek()['type'] == type_
    
    def _consume(self, type_: str, message: str) -> Dict[str, Any]:
        """Consume token of expected type or raise error."""
        if self._check(type_):
            return self._advance()
        
        raise Exception(f"{message} at line {self._peek()['line']}, col {self._peek()['col']}")