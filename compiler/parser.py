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
        self.decorators = [] # Store decorators for function/class
        
        # Initialize FSM components
        self.base_fsm = BaseFSM()
        self.expr_fsm = ExpressionFSM()
        self.stmt_fsm = StatementFSM()
        self.func_fsm = FunctionFSM()
    
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code into an AST using FSM-based approach."""
        self.tokens = tokenize(source_code)
        self.current_pos = 0
        self.decorators = [] # Reset decorators for each parse
        
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
        
        # Handle decorators
        if token['type'] == 'OPERATOR' and token['value'] == '@':
            return self._parse_decorator()

        # Handle async functions
        if token['type'] == 'ASYNC':
            return self._parse_async_function()

        # Delegate to appropriate FSM based on token type
        if token['type'] in ['DEF', 'CLASS']:
            node = self.func_fsm.parse(self)
            if node and self.decorators:
                node['decorators'] = self.decorators
                self.decorators = [] # Clear decorators after use
            return node
        # Updated to include TRY, WITH, MATCH
        elif token['type'] in ['IF', 'WHILE', 'FOR', 'TRY', 'WITH', 'MATCH']:
            # Pass the parser instance to the FSM's parse method
            return self.stmt_fsm.parse(self)
        else:
            # Handle potential expression statements or assignments
            expr = self.expr_fsm.parse(self)
            # Check for assignment
            if self._check('ASSIGN'):
                self._advance() # Consume '='
                value = self._parse_expression() # Assuming _parse_expression exists
                if expr['type'] == 'Literal' and expr['token_type'] == 'IDENTIFIER':
                     return {'type': 'Assignment', 'target': {'type': 'Identifier', 'name': expr['value']}, 'value': value}
                else:
                     raise Exception(f"Invalid assignment target at line {token['line']}, col {token['col']}")
            elif expr: # If it's just an expression statement
                return expr
            else:
                return None # Or handle error

    def _parse_decorator(self) -> Optional[Dict[str, Any]]:
        """Parse a decorator."""
        self._consume('OPERATOR', "Expected '@' for decorator")
        decorator_expr = self._parse_expression() # Need _parse_expression
        if not decorator_expr:
            raise Exception(f"Invalid decorator expression at line {self._peek()['line']}, col {self._peek()['col']}")
        self.decorators.append(decorator_expr)
        # Decorators are followed by function or class def, so parse the next statement
        return self._parse_statement()

    def _parse_async_function(self) -> Optional[Dict[str, Any]]:
        """Parse an async function definition."""
        self._consume('ASYNC', "Expected 'async'")
        if not self._check('DEF'):
             raise Exception(f"Expected 'def' after 'async' at line {self._peek()['line']}, col {self._peek()['col']}")
        func_def = self.func_fsm.parse(self) # Use FunctionFSM to parse the rest
        if func_def:
            func_def['async'] = True # Mark the function as async
            if self.decorators:
                func_def['decorators'] = self.decorators
                self.decorators = []
        return func_def

    def _parse_expression(self, min_precedence=0) -> Optional[Dict[str, Any]]:
        """Parse an expression using Pratt parsing (operator-precedence parsing)."""
        # Start with parsing the left-hand side (prefix operators, literals, parenthesized expressions)
        left = self._parse_prefix()
        if not left:
            return None # Or raise error if expression expected

        # While the next token is an operator with precedence >= min_precedence
        while not self._is_at_end():
            op_token = self._peek()
            if op_token['type'] != 'OPERATOR' or self._get_infix_precedence(op_token['value']) < min_precedence:
                break

            # Consume the operator
            self._advance()
            operator = op_token['value']
            precedence = self._get_infix_precedence(operator)

            # Parse the right-hand side recursively, passing the current operator's precedence
            # For right-associative operators (like exponentiation '**'), pass precedence - 1
            # For now, assume left-associativity for simplicity
            right = self._parse_expression(precedence + 1) # +1 for left-associativity
            if not right:
                 peek_token = self._peek()
                 raise Exception(f"Expected expression after operator '{operator}' at line {peek_token['line']}, col {peek_token['col']}")

            # Combine left, operator, and right into a binary expression node
            left = {
                'type': 'BinaryOp',
                'operator': operator,
                'left': left,
                'right': right
            }

        return left

    def _parse_prefix(self) -> Optional[Dict[str, Any]]:
        """Parse prefix operators, literals, identifiers, grouped expressions, lists."""
        token = self._peek()

        if token['type'] in ['NUMBER', 'STRING', 'IDENTIFIER', 'TRUE', 'FALSE', 'NONE']:
            self._advance()
            # Map boolean/none keywords to their AST representation
            if token['type'] == 'TRUE': value = True
            elif token['type'] == 'FALSE': value = False
            elif token['type'] == 'NONE': value = None
            else: value = token['value']
            return {'type': 'Literal', 'value': value, 'token_type': token['type']}
        elif token['type'] == 'OPERATOR' and token['value'] in ['+', '-', '!', 'not']: # Handle unary operators
            self._advance()
            operator = token['value']
            # Parse the operand recursively (use a high precedence for unary)
            operand = self._parse_expression(self._get_unary_precedence(operator))
            if not operand:
                peek_token = self._peek()
                raise Exception(f"Expected expression after unary operator '{operator}' at line {peek_token['line']}, col {peek_token['col']}")
            return {'type': 'UnaryOp', 'operator': operator, 'operand': operand}
        elif token['type'] == 'LPAREN': # Grouped expression
            self._advance() # Consume '('
            expr = self._parse_expression() # Parse expression inside parentheses
            self._consume('RPAREN', "Expected ')' after expression")
            return expr
        elif token['type'] == 'LBRACKET': # List literal or comprehension
            return self._parse_list_or_comprehension()
        # TODO: Add parsing for other prefix constructs (e.g., function calls if identifier is followed by '(')
        else:
            # If no prefix matches, it might be the start of an invalid expression or end of input
            # Let the caller handle this (e.g., _parse_statement might expect an expression)
            return None

    def _get_infix_precedence(self, operator: str) -> int:
        """Get precedence for infix binary operators."""
        # Based on Python's operator precedence
        if operator in ['or']: return 1
        if operator in ['and']: return 2
        if operator in ['not']: return 3 # Although 'not' is unary, handled in prefix
        if operator in ['==', '!=', '<', '>', '<=', '>=', 'is', 'is not', 'in', 'not in']: return 4
        if operator in ['|']: return 5
        if operator in ['^']: return 6
        if operator in ['&']: return 7
        if operator in ['<<', '>>']: return 8
        if operator in ['+', '-']: return 9
        if operator in ['*', '/', '//', '%', '@']: return 10
        if operator == '**': return 11 # Right-associative, needs special handling in loop if implemented
        return 0 # Default for non-operators or lowest precedence

    def _get_unary_precedence(self, operator: str) -> int:
        """Get precedence for unary prefix operators."""
        if operator in ['+', '-', '~', 'not']: return 10 # High precedence, below power
        return 0

    # Placeholder for parsing list literals or list comprehensions
    def _parse_list_or_comprehension(self) -> Optional[Dict[str, Any]]:
        """Parses a list literal or potentially a list comprehension."""
        self._consume('LBRACKET', "Expected '['")
        elements = []
        # Simple list literal parsing for now
        while not self._check('RBRACKET') and not self._is_at_end():
            expr = self._parse_expression()
            if expr:
                elements.append(expr)
            else:
                raise Exception(f"Invalid expression in list at line {self._peek()['line']}, col {self._peek()['col']}")
            if not self._check('RBRACKET'):
                self._consume('COMMA', "Expected ',' or ']' in list")
        
        self._consume('RBRACKET', "Expected ']' to close list")
        # TODO: Add logic to detect and parse list comprehensions (e.g., 'for' keyword)
        return {'type': 'ListLiteral', 'elements': elements}

    def _peek(self, offset: int = 0) -> Dict[str, Any]:
        """Look ahead in token stream without consuming."""
        if self.current_pos + offset >= len(self.tokens):
            # Return a dummy EOF token if out of bounds
            return {'type': 'EOF', 'value': None, 'line': -1, 'col': -1}
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
        
        peek_token = self._peek()
        raise Exception(f"{message} at line {peek_token['line']}, col {peek_token['col']}")