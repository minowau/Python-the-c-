from typing import Dict, Any, Optional
from .base_fsm import BaseFSM

class ExpressionFSM(BaseFSM):
    """FSM for parsing expressions and operators."""
    
    def __init__(self):
        super().__init__()
        self.operand_stack = []
        self.operator_stack = []
    
    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect operand or unary operator."""
        if token['type'] in ['NUMBER', 'STRING', 'IDENTIFIER']:
            self.operand_stack.append({
                'type': 'Literal',
                'value': token['value'],
                'token_type': token['type']
            })
            self.state = 'expect_operator'
        elif token['type'] == 'OPERATOR' and token['value'] in ['+', '-', '!']:
            self.operator_stack.append(token['value'])
            self.state = 'expect_operand'
        elif token['type'] == 'LPAREN':
            self.operator_stack.append('(')
            self.state = 'expect_operand'
        else:
            self._set_error(f"Expected operand or unary operator, got {token['type']}")
    
    def _handle_expect_operator(self, token: Dict[str, Any]) -> None:
        """Handle state expecting an operator."""
        if token['type'] == 'OPERATOR':
            while (self.operator_stack and 
                   self.operator_stack[-1] != '(' and 
                   self._precedence(self.operator_stack[-1]) >= self._precedence(token['value'])):
                self._apply_operator()
            self.operator_stack.append(token['value'])
            self.state = 'expect_operand'
        elif token['type'] == 'RPAREN':
            while self.operator_stack and self.operator_stack[-1] != '(':
                self._apply_operator()
            if self.operator_stack and self.operator_stack[-1] == '(':
                self.operator_stack.pop()
            else:
                self._set_error("Unmatched right parenthesis")
        else:
            self._finalize_expression()
    
    def _handle_expect_operand(self, token: Dict[str, Any]) -> None:
        """Handle state expecting an operand."""
        if token['type'] in ['NUMBER', 'STRING', 'IDENTIFIER']:
            self.operand_stack.append({
                'type': 'Literal',
                'value': token['value'],
                'token_type': token['type']
            })
            self.state = 'expect_operator'
        elif token['type'] == 'LPAREN':
            self.operator_stack.append('(')
        else:
            self._set_error(f"Expected operand, got {token['type']}")
    
    def _precedence(self, operator: str) -> int:
        """Get operator precedence level."""
        precedence = {
            '||': 1,
            '&&': 2,
            '==': 3, '!=': 3,
            '<': 4, '>': 4, '<=': 4, '>=': 4,
            '+': 5, '-': 5,
            '*': 6, '/': 6, '%': 6,
            '**': 7
        }
        return precedence.get(operator, 0)
    
    def _apply_operator(self) -> None:
        """Apply operator to operands on stack."""
        if len(self.operand_stack) < 2 or not self.operator_stack:
            self._set_error("Invalid expression")
            return
            
        operator = self.operator_stack.pop()
        right = self.operand_stack.pop()
        left = self.operand_stack.pop()
        
        self.operand_stack.append({
            'type': 'BinaryExpression',
            'operator': operator,
            'left': left,
            'right': right
        })
    
    def _finalize_expression(self) -> None:
        """Finalize expression parsing."""
        while self.operator_stack and self.operator_stack[-1] != '(':
            self._apply_operator()
        
        if self.operator_stack:
            self._set_error("Unmatched left parenthesis")
        elif len(self.operand_stack) == 1:
            self._set_result(self.operand_stack[0])
        else:
            self._set_error("Invalid expression state")