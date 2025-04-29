from typing import Dict, Any, Optional, List
from .base_fsm import BaseFSM
# Need access to the parser instance to call its methods like _parse_statement
from ..parser import Parser 

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
        self.is_async = False # Flag for async functions
        self._parser_instance: Optional[Parser] = None # Store parser instance
        self.parsing_default = False # Flag to indicate parsing default value
        self.seen_vararg = False # Flag for *args
        self.seen_kwarg = False # Flag for **kwargs

    def parse(self, parser: 'Parser') -> Optional[Dict[str, Any]]:
        """Parse tokens using this FSM.
        
        Args:
            parser: Parser instance providing token stream access
            
        Returns:
            AST node or None if parsing fails
        """
        self._parser_instance = parser # Store parser for internal use
        self.state = 'initial'
        self.error = None
        self.result = None
        self.def_type = None
        self.name = None
        self.params = []
        self.body = []
        # Decorators and async flag are handled by the main parser now
        # self.decorators = [] 
        self.current_param = None
        # self.is_async = False

        # Check for async keyword BEFORE 'def'
        if parser._check('ASYNC'):
            self.is_async = True
            parser._advance() # Consume 'async'

        # Expect 'def' or 'class'
        if not parser._check('DEF') and not parser._check('CLASS'):
             self._set_error(f"Expected 'def' or 'class', got {parser._peek()['type']}")
             return None

        # Start processing from the 'def' or 'class' token
        while not parser._is_at_end() and not self.error and not self.result:
            token = parser._peek()
            # Special handling for dedent to finalize body
            if self.state == 'parse_body' and token['type'] == 'DEDENT':
                parser._advance() # Consume DEDENT
                self._finalize_definition()
                break # Exit loop after finalizing
            
            self.transition(token)
            
            # Advance only if no error and not finalized
            # And avoid advancing if transition led to finalization (e.g., in _finalize_definition)
            if not self.error and not self.result:
                 # Check if the state requires advancing (most do)
                 # Avoid advancing after parsing default value, let expression FSM handle it
                 if self.state != 'parse_default_value':
                     parser._advance()
            elif self.result: # If finalized, break
                break
            elif self.error: # If error, break
                break
        
        if self.error:
            # Use the token where the error occurred if possible
            error_token = parser._peek() # Get current token for error reporting
            raise Exception(f"Parse error in {self.def_type or 'definition'}: {self.error} at line {error_token['line']}, col {error_token['col']}")
        
        # If loop finished without result (e.g. EOF), check state
        if not self.result and not self.error:
            if self.state not in ['initial']: # Allow finishing if nothing started
                 self._set_error(f"Unexpected end of input during {self.state}")
                 error_token = parser._peek(-1) # Last consumed token
                 raise Exception(f"Parse error: {self.error} near line {error_token['line']}, col {error_token['col']}")

        return self.result

    def _handle_initial(self, token: Dict[str, Any]) -> None:
        """Handle initial state - expect def or class keyword."""
        # Async is handled before calling parse
        if token['type'] == 'DEF':
            self.def_type = 'function'
            self.state = 'expect_name'
        elif token['type'] == 'CLASS':
            self.def_type = 'class'
            self.state = 'expect_name'
        else:
            # This state should technically be unreachable if called correctly by parser
            self._set_error(f"Expected 'def' or 'class', got {token['type']}")
    
    def _handle_expect_name(self, token: Dict[str, Any]) -> None:
        """Handle state expecting function/class name."""
        if token['type'] == 'IDENTIFIER':
            self.name = token['value']
            # Function needs params, class might go straight to colon (if no inheritance)
            self.state = 'expect_params' if self.def_type == 'function' else 'expect_inheritance_or_colon'
        else:
            self._set_error(f"Expected identifier for name, got {token['type']}")

    def _handle_expect_inheritance_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state for class expecting '(' for inheritance or ':' for body."""
        if token['type'] == 'LPAREN':
            # TODO: Implement inheritance parsing
            self._set_error("Inheritance parsing not yet implemented")
            # self.state = 'parse_inheritance'
        elif token['type'] == 'COLON':
            self.state = 'expect_indent'
        else:
            self._set_error(f"Expected '(' for inheritance or ':' for body, got {token['type']}")

    def _handle_expect_params(self, token: Dict[str, Any]) -> None:
        """Handle state expecting parameter list opening parenthesis."""
        if token['type'] == 'LPAREN':
            self.state = 'parse_params'
        else:
            self._set_error(f"Expected '(' for parameter list, got {token['type']}")

    def _handle_parse_params(self, token: Dict[str, Any]) -> None:
        """Handle state parsing parameter list."""
        if token['type'] == 'RPAREN':
            # If there was a param being processed, add it before closing
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'expect_colon'
        elif token['type'] == 'IDENTIFIER':
            # Starting a new parameter
            if self.current_param:
                 self._set_error("Expected comma between parameters")
                 return
            self.current_param = {
                'type': 'Parameter',
                'name': token['value'],
                'param_type': None, # TODO: Add type hint parsing
                'default_value': None
            }
            self.state = 'expect_param_type_or_default_or_comma_or_end'
        elif token['type'] == 'COMMA':
            # Separator between parameters
            if not self.params and not self.current_param:
                self._set_error("Unexpected comma at start of parameter list")
            elif not self.current_param:
                 self._set_error("Unexpected comma after another comma")
            else:
                 # Comma is valid only after a full parameter definition
                 self.params.append(self.current_param)
                 self.current_param = None
                 # Stay in parse_params, expecting next identifier or RPAREN
        elif token['type'] == 'OPERATOR' and token['value'] == '*': # Start of *args
            if self.seen_vararg or self.seen_kwarg:
                self._set_error("Cannot have multiple *args or *args after **kwargs")
                return
            self.state = 'expect_vararg_name'
        elif token['type'] == 'OPERATOR' and token['value'] == '**': # Start of **kwargs
            if self.seen_kwarg:
                self._set_error("Cannot have multiple **kwargs")
                return
            self.state = 'expect_kwarg_name'
        elif not self.params and not self.current_param and token['type'] != 'RPAREN': # Allow empty params list only if next is ')'
             self._set_error(f"Expected parameter name, '*', '**', or ')', got {token['type']}")
        else:
            self._set_error(f"Unexpected token in parameter list: {token['type']}")

    def _handle_expect_param_type_or_default_or_comma_or_end(self, token: Dict[str, Any]) -> None:
        """Handle state after param name, expecting type hint ':', default '=', comma ',', or end ')'"""
        if token['type'] == 'COLON':
            # TODO: Implement type hint parsing
            self._set_error("Parameter type hints not yet implemented")
            # self.state = 'parse_param_type'
        elif token['type'] == 'ASSIGN':
            if self.seen_vararg or self.seen_kwarg:
                self._set_error("Default argument follows *args or **kwargs")
                return
            self.state = 'parse_default_value'
        elif token['type'] == 'COMMA':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'parse_params' # Go back to expect next param identifier
        elif token['type'] == 'RPAREN':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'expect_return_type_or_colon' # End of params, expect return type hint or body colon
        else:
            self._set_error(f"Expected ':', '=', ',', or ')', got {token['type']}")

    # Placeholder for type hint parsing state
    # def _handle_parse_param_type(self, token: Dict[str, Any]) -> None:
    #     # ... parse type expression ...
    #     self.current_param['param_type'] = parsed_type
    #     self.state = 'expect_param_default_or_separator' # Expect default or separator after type

    def _handle_expect_param_default_or_separator(self, token: Dict[str, Any]) -> None:
        """Handle state after type hint, expecting default value or separator."""
        if token['type'] == 'ASSIGN':
            if self.seen_vararg or self.seen_kwarg:
                 self._set_error("Default argument follows *args or **kwargs")
                 return
            self.state = 'parse_default_value'
        elif token['type'] == 'COMMA':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'parse_params'
        elif token['type'] == 'RPAREN':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'expect_return_type_or_colon'
        else:
            self._set_error(f"Expected '=', ',', or ')', got {token['type']}")

    
    def _handle_expect_param_separator(self, token: Dict[str, Any]) -> None:
        """Handle state expecting parameter separator or default value."""
    #     if token['type'] == 'COMMA':
    #         if self.current_param:
    #             self.params.append(self.current_param)
    #             self.current_param = None
    #         self.state = 'parse_params'
    #     elif token['type'] == 'ASSIGN': # Use ASSIGN if lexer distinguishes it
    #         self.state = 'parse_default_value'
    #     elif token['type'] == 'RPAREN':
    #         if self.current_param:
    #             self.params.append(self.current_param)
    #             self.current_param = None
    #         self.state = 'expect_colon'
    #     else:
    #         self._set_error(f"Expected ',' or '=', got {token['type']}")
    
    def _handle_parse_default_value(self, token: Dict[str, Any]) -> None:
        """Handle state parsing parameter default value."""
        # We need the parser instance to call its expression parsing logic
        if not self._parser_instance:
             self._set_error("Parser instance not available for parsing default value")
             return

        # Use the parser's general expression parsing method
        # This assumes _parse_expression consumes tokens until the expression ends
        default_value = self._parser_instance._parse_expression()
        
        if default_value:
            if not self.current_param:
                 self._set_error("Parsing default value without current parameter")
                 return
            self.current_param['default_value'] = default_value
            # After parsing default value, expect comma or closing paren
            # After parsing default value, expect comma or closing paren
            # The parser._parse_expression() consumes tokens, so check the *next* token
            next_token = self._parser_instance._peek()
            if next_token['type'] == 'COMMA':
                if self.current_param:
                    self.params.append(self.current_param)
                    self.current_param = None
                self._parser_instance._advance() # Consume comma
                self.state = 'parse_params' # Go back to expect next param identifier
            elif next_token['type'] == 'RPAREN':
                if self.current_param:
                    self.params.append(self.current_param)
                    self.current_param = None
                # Don't consume RPAREN here, let the main loop handle it in 'parse_params' state
                self.state = 'parse_params'
            else:
                self._set_error(f"Expected ',' or ')' after default value, got {next_token['type']}")
        else:
            # _parse_expression should raise error or return None on failure
            # If it returns None without error, it means unexpected token
            if not self.error:
                 self._set_error(f"Expected expression for default value, got {self._parser_instance._peek()['type']}")

    # This state is removed as logic is handled within _handle_parse_default_value
    # def _handle_expect_param_separator_after_default(self, token: Dict[str, Any]) -> None:
    #     """Handle state after parsing a default value, expecting ',' or ')'"""

    # --- Handlers for *args and **kwargs --- 

    def _handle_expect_vararg_name(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the name for *args."""
        if token['type'] == 'IDENTIFIER':
            self.params.append({'type': 'VarArgParameter', 'name': token['value']})
            self.seen_vararg = True
            self.state = 'expect_vararg_comma_or_end' # Can be followed by comma (for **kwargs) or ')'
        else:
            self._set_error(f"Expected identifier for *args name, got {token['type']}")

    def _handle_expect_vararg_comma_or_end(self, token: Dict[str, Any]) -> None:
        """Handle state after *args, expecting comma or end parenthesis."""
        if token['type'] == 'COMMA':
            # Check if next is **kwargs
            if self._parser_instance._peek(1)['type'] == 'OPERATOR' and self._parser_instance._peek(1)['value'] == '**':
                 self.state = 'parse_params' # Let parse_params handle the comma and then **
            else:
                 self._set_error("Only **kwargs can follow *args after a comma")
        elif token['type'] == 'RPAREN':
            self.state = 'expect_return_type_or_colon'
        else:
            self._set_error(f"Expected ',' or ')' after *args, got {token['type']}")

    def _handle_expect_kwarg_name(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the name for **kwargs."""
        if token['type'] == 'IDENTIFIER':
            self.params.append({'type': 'KwArgParameter', 'name': token['value']})
            self.seen_kwarg = True
            self.state = 'expect_kwarg_end_only' # Must be the last parameter
        else:
            self._set_error(f"Expected identifier for **kwargs name, got {token['type']}")

    def _handle_expect_kwarg_end_only(self, token: Dict[str, Any]) -> None:
        """Handle state after **kwargs, expecting only the closing parenthesis."""
        if token['type'] == 'RPAREN':
            self.state = 'expect_return_type_or_colon'
        else:
            self._set_error(f"Expected ')' after **kwargs, got {token['type']}")

    # --- End *args/**kwargs handlers ---
        if token['type'] == 'COMMA':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'parse_params' # Go back to expect next param identifier
        elif token['type'] == 'RPAREN':
            if self.current_param:
                self.params.append(self.current_param)
                self.current_param = None
            self.state = 'expect_colon' # End of params, expect body colon
        else:
            self._set_error(f"Expected ',' or ')' after default value, got {token['type']}")

    def _handle_expect_return_type_or_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting '->' for return type or ':' for body."""
        if token['type'] == 'ARROW': # Assuming lexer produces ARROW for '->'
            self.state = 'expect_return_type'
        elif token['type'] == 'COLON':
            self.state = 'expect_indent'
        else:
            self._set_error(f"Expected '->' for return type or ':' for body, got {token['type']}")

    def _handle_expect_return_type(self, token: Dict[str, Any]) -> None:
        """Handle state expecting the return type expression."""
        # TODO: Implement return type expression parsing
        if token['type'] == 'IDENTIFIER': # Simple type for now
            # Store return type info somewhere, maybe on the result dict later
            self.return_type_hint = {'type': 'Identifier', 'name': token['value']}
            self.state = 'expect_colon_after_return'
        else:
            self._set_error(f"Expected return type identifier, got {token['type']}")

    def _handle_expect_colon_after_return(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon after return type hint."""
        if token['type'] == 'COLON':
            self.state = 'expect_indent'
        else:
            self._set_error(f"Expected ':' after return type hint, got {token['type']}")

    def _handle_expect_colon(self, token: Dict[str, Any]) -> None:
        """Handle state expecting colon before body (kept for class def)."""
        if token['type'] == 'COLON':
            self.state = 'expect_indent'
        else:
            self._set_error(f"Expected ':' after definition header, got {token['type']}")

    def _handle_expect_indent(self, token: Dict[str, Any]) -> None:
        """Handle state expecting indentation for body."""
        if token['type'] == 'INDENT':
            self.state = 'parse_body'
        # Allow empty body (just pass)
        elif token['type'] == 'PASS': 
             self._parser_instance._advance() # Consume PASS
             # Check for dedent immediately after pass
             if self._parser_instance._check('DEDENT'):
                  self._parser_instance._advance() # Consume DEDENT
                  self._finalize_definition()
             else: # Or EOF
                  # TODO: Handle EOF case better
                  self._finalize_definition()
        else:
            self._set_error(f"Expected indented block or 'pass', got {token['type']}")

    def _handle_parse_body(self, token: Dict[str, Any]) -> None:
        """Handle state parsing function/class body.
           Note: DEDENT is handled in the main parse loop.
        """
        # Delegate statement parsing back to the main parser instance
        if not self._parser_instance:
             self._set_error("Parser instance not available for parsing body")
             return

        # Let the main parser parse one statement within the body
        # The main parser's _parse_statement will handle FSM delegation
        statement = self._parser_instance._parse_statement()
        if statement:
            self.body.append(statement)
        elif not self._parser_instance._is_at_end() and not self.error:
            # If _parse_statement returned None but not at EOF and no error set,
            # it might mean an unexpected token at the start of a statement.
            # The error should ideally be raised within _parse_statement or its sub-FSMs.
            # If we reach here, it's likely an issue in the sub-parsers.
            # We can set a generic error or rely on sub-parsers.
            pass # Assume sub-parser handled error or advanced past something

    def _finalize_definition(self) -> None:
        """Finalize function/class definition parsing."""
        # Decorators are now attached by the main parser
        # async flag is stored in self.is_async
        result = {
            'type': 'FunctionDefinition' if self.def_type == 'function' else 'ClassDefinition',
            'name': self.name,
            'body': self.body,
            'async': self.is_async # Add async flag
        }
        
        if self.def_type == 'function':
            result['params'] = self.params
        # else: # Class specific fields like base classes
            # result['bases'] = self.bases # If inheritance is parsed
        
        # Decorators are added by the caller (Parser._parse_statement)
        # if self.decorators:
        #     result['decorators'] = self.decorators
        
        self._set_result(result)