import unittest
from compiler.lexer import Lexer, Token, TokenType


class TestLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()
    
    def test_keywords(self):
        source = 'def class if else while for'
        tokens = self.lexer.tokenize(source)
        
        expected_types = [
            TokenType.DEF,
            TokenType.CLASS,
            TokenType.IF,
            TokenType.ELSE,
            TokenType.WHILE,
            TokenType.FOR,
            TokenType.EOF
        ]
        
        self.assertEqual(len(tokens), len(expected_types))
        for token, expected_type in zip(tokens, expected_types):
            self.assertEqual(token.type, expected_type)
    
    def test_identifiers(self):
        source = 'variable_name _private counter123'
        tokens = self.lexer.tokenize(source)
        
        self.assertEqual(len(tokens), 4)  # 3 identifiers + EOF
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, 'variable_name')
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, '_private')
        self.assertEqual(tokens[2].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[2].value, 'counter123')
    
    def test_numbers(self):
        source = '42 3.14 123.456'
        tokens = self.lexer.tokenize(source)
        
        self.assertEqual(len(tokens), 4)  # 3 numbers + EOF
        self.assertEqual(tokens[0].type, TokenType.INTEGER)
        self.assertEqual(tokens[0].value, '42')
        self.assertEqual(tokens[1].type, TokenType.FLOAT)
        self.assertEqual(tokens[1].value, '3.14')
        self.assertEqual(tokens[2].type, TokenType.FLOAT)
        self.assertEqual(tokens[2].value, '123.456')
    
    def test_strings(self):
        source = '"hello" \'world\''
        tokens = self.lexer.tokenize(source)
        
        self.assertEqual(len(tokens), 3)  # 2 strings + EOF
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, 'hello')
        self.assertEqual(tokens[1].type, TokenType.STRING)
        self.assertEqual(tokens[1].value, 'world')
    
    def test_operators(self):
        source = '+ - * / % = == != < > <= >='
        tokens = self.lexer.tokenize(source)
        
        expected_types = [
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.MULTIPLY,
            TokenType.DIVIDE,
            TokenType.MODULO,
            TokenType.ASSIGN,
            TokenType.EQUALS,
            TokenType.NOT_EQUALS,
            TokenType.LESS_THAN,
            TokenType.GREATER_THAN,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_EQUAL,
            TokenType.EOF
        ]
        
        self.assertEqual(len(tokens), len(expected_types))
        for token, expected_type in zip(tokens, expected_types):
            self.assertEqual(token.type, expected_type)
    
    def test_indentation(self):
        source = '''
        def test():
            x = 1
                y = 2
            z = 3
        '''
        tokens = self.lexer.tokenize(source)
        
        # Find INDENT and DEDENT tokens
        indent_count = sum(1 for token in tokens if token.type == TokenType.INDENT)
        dedent_count = sum(1 for token in tokens if token.type == TokenType.DEDENT)
        
        self.assertEqual(indent_count, 2)  # One for function body, one for nested block
        self.assertEqual(dedent_count, 2)  # Matching DEDENTs
    
    def test_token_caching(self):
        # Test that frequently used tokens are cached
        source = 'def def def class class if if'
        tokens = self.lexer.tokenize(source)
        
        # Verify that cached tokens maintain correct line and column info
        self.assertEqual(tokens[0].line, tokens[1].line)
        self.assertNotEqual(tokens[0].column, tokens[1].column)
        
        # Verify that the cache contains the keywords
        self.assertIn('def', self.lexer.token_cache)
        self.assertIn('class', self.lexer.token_cache)
        self.assertIn('if', self.lexer.token_cache)

if __name__ == '__main__':
    unittest.main()