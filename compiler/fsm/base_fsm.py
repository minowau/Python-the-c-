from typing import Dict, Any, Optional

class BaseFSM:
    """Base Finite State Machine for parsing Python++ constructs."""
    
    def __init__(self):
        self.state = 'initial'
        self.error = None
        self.result: Optional[Dict[str, Any]] = None
    
    def transition(self, token: Dict[str, Any]) -> None:
        """Transition to next state based on current token.
        
        Args:
            token: Current token being processed
        """
        method = getattr(self, f'_handle_{self.state}', None)
        if method:
            method(token)
        else:
            self.error = f"Invalid state: {self.state}"
    
    def parse(self, parser: 'Parser') -> Optional[Dict[str, Any]]:
        """Parse tokens using this FSM.
        
        Args:
            parser: Parser instance providing token stream access
            
        Returns:
            AST node or None if parsing fails
        """
        self.state = 'initial'
        self.error = None
        self.result = None
        
        while not parser._is_at_end() and not self.error and not self.result:
            token = parser._peek()
            self.transition(token)
            if not self.error and not self.result:
                parser._advance()
        
        if self.error:
            raise Exception(f"Parse error: {self.error} at line {token['line']}, col {token['col']}")
        
        return self.result
    
    def _set_error(self, message: str) -> None:
        """Set error state with message."""
        self.error = message
    
    def _set_result(self, result: Dict[str, Any]) -> None:
        """Set successful parse result."""
        self.result = result