#!/usr/bin/env python3
from typing import Dict, Any, Optional
from pathlib import Path
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.fsm.statement_fsm import StatementFSM
from compiler.fsm.expression_fsm import ExpressionFSM
from compiler.fsm.type_fsm import TypeFSM
from runtime.executor import RuntimeExecutor, ExecutionContext
from runtime.types.type_system import TypeSystem

class PythonPlusPlus:
    """Main entry point for Python++ language execution."""
    
    def __init__(self):
        self.type_system = TypeSystem()
        self.executor = RuntimeExecutor(self.type_system)
        
    def execute_file(self, file_path: str) -> Any:
        """Execute a Python++ source file."""
        # Read source file
        source = Path(file_path).read_text()
        
        # Initialize components
        lexer = Lexer(source)
        parser = Parser()
        
        # Set up FSMs
        parser.statement_fsm = StatementFSM()
        parser.expression_fsm = ExpressionFSM()
        parser.type_fsm = TypeFSM()
        
        # Parse source into AST
        ast = parser.parse(lexer.tokenize())
        
        # Create execution context
        context = ExecutionContext(
            variables={},
            type_context={},
            optimization_level=2
        )
        
        # Execute AST
        return self.executor.execute(ast, context)

def main():
    """Command line entry point."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python main.py <source_file>")
        sys.exit(1)
        
    interpreter = PythonPlusPlus()
    result = interpreter.execute_file(sys.argv[1])
    print(f"Result: {result}")

if __name__ == '__main__':
    main()