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
        # Add placeholders for new statement types
        self.try_body = []
        self.except_handlers = []
        self.finally_body = None
        self.with_items = []
        self.match_subject = None
        self.case_patterns = []
        self.current_except_handler = None
        self._parser = None # Store parser instance

    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect statement keyword."""
        if token['type'] in ['IF', 'WHILE', 'FOR']:
            self.statement_type = token['type'].lower()
            self.state = 'expect_condition'
        elif token['type'] == 'TRY':
            self.statement_type = 'try'
            self.state = 'expect_try_colon' # New state for try
        elif token['type'] == 'WITH':
            self.statement_type = 'with'
            self.state = 'expect_with_item' # New state for with
        elif token['type'] == 'MATCH':
            self.statement_type = 'match'
            self.state = 'expect_match_subject' # New state for match
        else:
            self._set_error(f"Expected statement keyword, got {token['type']}")

    def _handle_expect_condition(self, token: Dict[str, Any]) -> None:
        
        if self.statement_type == 'for' and token['type'] == 'IDENTIFIER':
            self.condition = {
                'type': 'Identifier',
                'name': token['value']
            }
            self.state = 'expect_in'
            return

   

        if not self._parser:
            self._set_error("Parser instance not set in StatementFSM")
            return

        expr_fsm = ExpressionFSM()
        expr_fsm.set_parser(self._parser)  # Assuming ExpressionFSM requires parser context

        self.condition = expr_fsm.parse()
        if self.condition:
            self.state = 'expect_colon'
        else:
            self._set_error("Failed to parse condition expression")

    
    def _handle_expect_in(self, token: Dict[str, Any]) -> None:
        """Handle state expecting 'in' keyword in for loop."""
        if token['type'] == 'IN':
            self.state = 'expect_iterable'
        else:
            self._set_error(f"Expected 'in' keyword, got {token['type']}")
    
    def _handle_expect_iterable(self, token: Dict[str, Any]) -> None:
        """Handle state expecting iterable expression in for loop."""
        from .expression_fsm import ExpressionFSM
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        expr_fsm = ExpressionFSM()
        self.condition = {
            'type': 'ForCondition',
            'variable': self.condition,
            'iterable': expr_fsm.parse(self._parser) # Need parser instance
        }
        if self.condition['iterable']:
            self.state = 'expect_colon'
    
    def parse(self, parser: 'Parser') -> Optional[Dict[str, Any]]:
        """Parse tokens using this FSM, requires parser instance."""
        self._parser = parser # Store parser instance
        return super().parse(parser)

    # --- Handlers for try/except/finally --- 

    def _handle_expect_try_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon after 'try'."""
        if token['type'] == 'COLON':
            self.state = 'expect_indent' # Reuse expect_indent for try body
        else:
            self._set_error(f"Expected ':' after 'try', got {token['type']}")

    def _handle_expect_try_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing the body of the try block."""
        # Delegate statement parsing to the main parser
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        statement = self._parser._parse_statement()
        if statement:
            self.try_body.append(statement)
        # Stay in this state until DEDENT or except/finally
        if self._parser._check('DEDENT'):
            self._set_error("Unexpected DEDENT after try block without except or finally")
        elif self._parser._check('EXCEPT'):
            self.state = 'expect_except_clause'
        elif self._parser._check('FINALLY'):
            self.state = 'expect_finally_colon'

    def _handle_expect_except_clause(self, token: Dict[str, Any]) -> None:
        """Handle state expecting an except clause (type and optional alias)."""
        if token['type'] == 'EXCEPT':
            self.current_except_handler = {'type': None, 'alias': None, 'body': []}
            self.state = 'expect_except_type'
        elif token['type'] == 'FINALLY': # Can go directly to finally
             self.state = 'expect_finally_colon'
        elif token['type'] == 'DEDENT': # End of try-except block
             self._finalize_try_statement()
        else:
            self._set_error(f"Expected 'except', 'finally', or DEDENT, got {token['type']}")

    def _handle_expect_except_type(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the exception type."""
        if token['type'] == 'IDENTIFIER':
            # TODO: Use expression parser for complex types?
            self.current_except_handler['type'] = {'type': 'Identifier', 'name': token['value']}
            self.state = 'expect_except_as_or_colon'
        elif token['type'] == 'COLON': # Bare except
            self.state = 'expect_except_body_indent'
        else:
            self._set_error(f"Expected exception type or ':', got {token['type']}")

    def _handle_expect_except_as_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting 'as' or ':' after exception type."""
        if token['type'] == 'AS':
            self.state = 'expect_except_alias'
        elif token['type'] == 'COLON':
            self.state = 'expect_except_body_indent'
        else:
            self._set_error(f"Expected 'as' or ':', got {token['type']}")

    def _handle_expect_except_alias(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the alias for the exception."""
        if token['type'] == 'IDENTIFIER':
            self.current_except_handler['alias'] = {'type': 'Identifier', 'name': token['value']}
            self.state = 'expect_except_colon'
        else:
            self._set_error(f"Expected identifier for exception alias, got {token['type']}")

    def _handle_expect_except_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting ':' after except clause."""
        if token['type'] == 'COLON':
            self.state = 'expect_except_body_indent'
        else:
            self._set_error(f"Expected ':' after except clause, got {token['type']}")

    def _handle_expect_except_body_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting INDENT before except body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_except_body'
        else:
            self._set_error(f"Expected INDENT for except block body, got {token['type']}")

    def _handle_parse_except_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing the body of the except block."""
        if not self._parser:
            self._set_error("Parser instance not set")
            return

        if token['type'] == 'DEDENT':
            self.except_handlers.append(self.current_except_handler)
            self.current_except_handler = None
            # After dedenting from except, look for another except, finally, or end of try block
            self.state = 'expect_except_clause' # Go back to check for more except/finally
            # Need to re-evaluate the DEDENT token in the new state
            self.transition(token)
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.current_except_handler['body'].append(statement)
            # Stay in this state until DEDENT

    def _handle_expect_finally_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting ':' after 'finally'."""
        if token['type'] == 'COLON':
            self.state = 'expect_finally_body_indent'
        else:
            self._set_error(f"Expected ':' after 'finally', got {token['type']}")

    def _handle_expect_finally_body_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting INDENT before finally body."""
        if token['type'] == 'INDENT':
            self.finally_body = [] # Initialize finally body list
            self.state = 'parse_finally_body'
        else:
            self._set_error(f"Expected INDENT for finally block body, got {token['type']}")

    def _handle_parse_finally_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing the body of the finally block."""
        if not self._parser:
            self._set_error("Parser instance not set")
            return

        if token['type'] == 'DEDENT':
            self._finalize_try_statement()
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.finally_body.append(statement)
            # Stay in this state until DEDENT

    def _finalize_try_statement(self) -> None:
        """Finalize the try statement AST node."""
        self.result = {
            'type': 'TryStatement',
            'body': self.try_body,
            'handlers': self.except_handlers,
            'finalbody': self.finally_body
        }
        self.state = 'final'

    # --- Handlers for with statement ---

    def _handle_expect_with_item(self, token: Dict[str, Any]) -> None:
        """Handle state expecting item(s) for 'with'. Placeholder."""
        # TODO: Implement parsing of with items (e.g., expr [as var])
        # For now, assume a simple expression and move to colon
        from .expression_fsm import ExpressionFSM
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        expr_fsm = ExpressionFSM()
        item = expr_fsm.parse(self._parser)
        if item:
            self.with_items.append(item) # Store placeholder item
            # TODO: Handle 'as' keyword and multiple items
            self.state = 'expect_colon' # Expect colon after with items
        else:
            self._set_error(f"Expected expression for 'with' item, got {token['type']}")

    def _handle_expect_with_item_as_or_comma_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state after parsing a with item expression."""
        if token['type'] == 'AS':
            self.state = 'expect_with_alias'
        elif token['type'] == 'COMMA':
            self.state = 'expect_with_item' # Expect another item
        elif token['type'] == 'COLON':
            self.state = 'expect_with_body_indent' # End of items, expect body
        else:
            self._set_error(f"Expected 'as', ',', or ':' after with item, got {token['type']}")

    def _handle_expect_with_alias(self, token: Dict[str, Any]) -> None:
        """Handle state expecting alias identifier after 'as'."""
        if token['type'] == 'IDENTIFIER':
            # Assume the last item in with_items needs the alias
            if self.with_items:
                 # Simple structure for now, might need refinement
                 self.with_items[-1] = {'item': self.with_items[-1], 'alias': {'type': 'Identifier', 'name': token['value']}}
            else:
                 self._set_error("Found 'as' without preceding with item")
                 return
            self.state = 'expect_with_comma_or_colon'
        else:
            self._set_error(f"Expected identifier for 'with' alias, got {token['type']}")

    def _handle_expect_with_comma_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state after parsing an alias or a non-aliased item."""
        if token['type'] == 'COMMA':
            self.state = 'expect_with_item' # Expect another item
        elif token['type'] == 'COLON':
            self.state = 'expect_with_body_indent' # End of items, expect body
        else:
            self._set_error(f"Expected ',' or ':' after with item/alias, got {token['type']}")

    def _handle_expect_with_body_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting INDENT before with body."""
        if token['type'] == 'INDENT':
            self.body = [] # Reset body for the with statement
            self.state = 'parse_with_body'
        else:
            self._set_error(f"Expected INDENT for 'with' block body, got {token['type']}")

    def _handle_parse_with_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing the body of the with block."""
        if not self._parser:
            self._set_error("Parser instance not set")
            return

        if token['type'] == 'DEDENT':
            self._finalize_with_statement()
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.body.append(statement)
            # Stay in this state until DEDENT

    def _finalize_with_statement(self) -> None:
        """Finalize the with statement AST node."""
        self.result = {
            'type': 'WithStatement',
            'items': self.with_items,
            'body': self.body
        }
        self.state = 'final'

    # --- Handlers for match statement ---

    def _handle_expect_match_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon after match subject."""
        if token['type'] == 'COLON':
            self.state = 'expect_match_body_indent'
        else:
            self._set_error(f"Expected ':' after match subject, got {token['type']}")

    def _handle_expect_match_body_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting INDENT before match body."""
        if token['type'] == 'INDENT':
            self.state = 'expect_case_clause'
        else:
            self._set_error(f"Expected INDENT for match block body, got {token['type']}")

    def _handle_expect_case_clause(self, token: Dict[str, Any]) -> None:
        """Handle state expecting a 'case' clause or DEDENT."""
        if token['type'] == 'CASE':
            self.current_case_pattern = {'pattern': None, 'guard': None, 'body': []}
            self.state = 'expect_case_pattern'
        elif token['type'] == 'DEDENT':
            self._finalize_match_statement()
        else:
            self._set_error(f"Expected 'case' or DEDENT, got {token['type']}")

    def _handle_expect_case_pattern(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the pattern for a 'case' clause. Placeholder."""
        # TODO: Implement detailed pattern parsing (literal, capture, wildcard, class, etc.)
        # For now, treat it like a simple expression
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        from .expression_fsm import ExpressionFSM # Reusing for simplicity, needs dedicated pattern parser
        expr_fsm = ExpressionFSM()
        pattern = expr_fsm.parse(self._parser)
        if pattern:
            self.current_case_pattern['pattern'] = pattern
            self.state = 'expect_case_guard_or_colon'
        else:
            self._set_error(f"Expected pattern for 'case' clause, got {token['type']}")

    def _handle_expect_case_guard_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting an optional 'if' guard or ':' after pattern."""
        if token['type'] == 'IF':
            self.state = 'expect_case_guard_condition'
        elif token['type'] == 'COLON':
            self.state = 'expect_case_body_indent'
        else:
            self._set_error(f"Expected 'if' or ':' after case pattern, got {token['type']}")

    def _handle_expect_case_guard_condition(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the condition expression for the 'if' guard."""
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        from .expression_fsm import ExpressionFSM
        expr_fsm = ExpressionFSM()
        guard = expr_fsm.parse(self._parser)
        if guard:
            self.current_case_pattern['guard'] = guard
            self.state = 'expect_case_colon_after_guard'
        else:
            self._set_error(f"Expected condition for 'if' guard, got {token['type']}")

    def _handle_expect_case_colon_after_guard(self, token: Dict[str, Any]) -> None:
        """Handle state expecting ':' after the guard condition."""
        if token['type'] == 'COLON':
            self.state = 'expect_case_body_indent'
        else:
            self._set_error(f"Expected ':' after 'if' guard, got {token['type']}")

    def _handle_expect_case_body_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting INDENT before case body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_case_body'
        else:
            self._set_error(f"Expected INDENT for case block body, got {token['type']}")

    def _handle_parse_case_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing the body of the case block."""
        if not self._parser:
            self._set_error("Parser instance not set")
            return

        if token['type'] == 'DEDENT':
            self.case_patterns.append(self.current_case_pattern)
            self.current_case_pattern = None
            # After dedenting from case, look for another case or end of match
            self.state = 'expect_case_clause'
            # Re-evaluate the DEDENT token in the new state
            self.transition(token)
        else:
            statement = self._parser._parse_statement()
            if statement:
                self.current_case_pattern['body'].append(statement)
            # Stay in this state until DEDENT

    def _finalize_match_statement(self) -> None:
        """Finalize the match statement AST node."""
        self.result = {
            'type': 'MatchStatement',
            'subject': self.match_subject,
            'cases': self.case_patterns
        }
        self.state = 'final'

    # --- Common handlers ---

    def _handle_expect_match_subject(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the subject expression for 'match'. Placeholder."""
        # TODO: Implement parsing of match subject expression
        from .expression_fsm import ExpressionFSM
        if not self._parser:
            self._set_error("Parser instance not set")
            return
        expr_fsm = ExpressionFSM()
        subject = expr_fsm.parse(self._parser)
        if subject:
            self.match_subject = subject
            self.state = 'expect_match_colon'
        else:
            self._set_error(f"Expected subject expression for 'match', got {token['type']}")
        if subject:
            self.match_subject = subject
            self.state = 'expect_colon' # Expect colon after match subject
        else:
            self._set_error(f"Expected expression for 'match' subject, got {token['type']}")

    # --- End Placeholder handlers --- 

    def _handle_expect_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting indentation for body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_body'
        else:
            self._set_error(f"Expected indented block, got {token['type']}")
    
    def _handle_parse_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing statement body."""
        if token['type'] == 'DEDENT':
            # Transition based on statement type after body
            if self.statement_type == 'try':
                self.state = 'expect_except_or_finally' # New state after try body
            elif self.statement_type in ['if', 'while', 'for', 'with', 'match']: # Match needs case handling
                 # For match, this should transition to expect_case
                 if self.statement_type == 'match':
                     self.state = 'expect_case' # New state for match cases
                 else:
                     self.state = 'expect_else' # Or finalize if no else/except/finally
            else:
                 self._finalize_statement() # Should not happen for try/with/match here
        else:
            statement = self._parser._parse_statement()
            if statement:
                # Store body based on context
                if self.statement_type == 'try':
                    self.try_body.append(statement)
                # elif self.statement_type == 'match': # Case body handled separately
                #     pass 
                else: # if, while, for, with
                    self.body.append(statement)

    def _handle_expect_except_or_finally(self, token: Dict[str, Any]) -> None:
        """Handle state expecting 'except' or 'finally' after try block. Placeholder."""
        if token['type'] == 'EXCEPT':
            # TODO: Implement except clause parsing
            self.state = 'expect_except_expression' # Placeholder state
            self._set_error("Except clause parsing not implemented")
        elif token['type'] == 'FINALLY':
            # TODO: Implement finally clause parsing
            self.state = 'expect_finally_colon' # Placeholder state
            self._set_error("Finally clause parsing not implemented")
        else:
            # If neither except nor finally, finalize the try statement (might be invalid Python)
            self._finalize_statement()

    def _handle_expect_case(self, token: Dict[str, Any]) -> None:
        """Handle state expecting 'case' keyword. Placeholder."""
        if token['type'] == 'CASE':
            # TODO: Implement case pattern parsing
            self.state = 'expect_case_pattern' # Placeholder state
            self._set_error("Case pattern parsing not implemented")
        else:
            # No more cases, finalize match statement
            self._finalize_statement()

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
        # Adapt finalization based on statement type
        if self.statement_type == 'try':
            result = {
                'type': 'TryStatement',
                'body': self.try_body,
                'handlers': self.except_handlers, # Placeholder
                'finalbody': self.finally_body # Placeholder
            }
        elif self.statement_type == 'with':
             result = {
                 'type': 'WithStatement',
                 'items': self.with_items, # Placeholder
                 'body': self.body
             }
        elif self.statement_type == 'match':
             result = {
                 'type': 'MatchStatement',
                 'subject': self.match_subject, # Placeholder
                 'cases': self.case_patterns # Placeholder
             }
        else: # if, while, for
            result = {
                'type': f'{self.statement_type.capitalize()}Statement',
                'condition': self.condition,
                'body': self.body
            }
            if self.else_body:
                result['else_body'] = self.else_body
        
        self._set_result(result)