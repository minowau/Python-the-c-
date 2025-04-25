import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from compiler.lexer import tokenize


class TestLexerComprehensive(unittest.TestCase):

    def test_keywords_and_identifiers(self):
        code = "def function return if else class myClass"
        tokens = tokenize(code)
        expected_types = ["DEF", "IDENTIFIER", "RETURN", "IF", "ELSE", "CLASS", "IDENTIFIER", "EOF"]
        self.assertEqual([t['type'] for t in tokens], expected_types)

    def test_numbers(self):
        code = "123 0.456 789_123"
        tokens = tokenize(code)
        self.assertEqual(tokens[0]['type'], "NUMBER")
        self.assertEqual(tokens[1]['type'], "NUMBER")
        self.assertEqual(tokens[2]['type'], "NUMBER")

    def test_strings_single_double(self):
        code = "'hello' \"world\""
        tokens = tokenize(code)
        self.assertEqual(tokens[0]['type'], "STRING")
        self.assertEqual(tokens[1]['type'], "STRING")

    def test_unterminated_string(self):
        with self.assertRaises(Exception):
            tokenize("'oops")

    def test_comments_and_whitespace(self):
        code = "   # comment\ndef x(): pass  # trailing"
        tokens = tokenize(code)
        self.assertTrue(any(t['type'] == "DEF" for t in tokens))
        self.assertTrue(any(t['type'] == "IDENTIFIER" and t['value'] == "x" for t in tokens))

    def test_operators_single_double(self):
        code = "a == b != c <= d >= e ** f // g and or not"
        tokens = tokenize(code)
        types = [t['type'] for t in tokens if t['type'] != "IDENTIFIER"]
        expected = ["OPERATOR"] * 7 + ["OPERATOR", "OPERATOR", "OPERATOR"] + ["AND", "OR", "NOT"] + ["EOF"]
        self.assertEqual(types[-len(expected):], expected)

    def test_floating_point_numbers(self):
        code = "x = 3.14\ny = 2.5e3"
        tokens = tokenize(code)
        self.assertEqual(tokens[0]['type'], 'IDENTIFIER')
        self.assertEqual(tokens[2]['type'], 'NUMBER')
        self.assertEqual(tokens[2]['value'], '3.14')
        self.assertEqual(tokens[5]['type'], 'NUMBER')
        self.assertEqual(tokens[5]['value'], '2.5e3')

    def test_delimiters(self):
        code = "( ) : , [ ] { } ;"
        expected = ["LPAREN", "RPAREN", "COLON", "COMMA", "LBRACKET", "RBRACKET", "LBRACE", "RBRACE", "SEMICOLON", "EOF"]
        tokens = tokenize(code)
        self.assertEqual([t['type'] for t in tokens], expected)

    def test_unexpected_character(self):
        with self.assertRaises(Exception):
            tokenize("def x$y:")

    def test_mixed_quote_string(self):
        code = "\"hello 'world'\""
        tokens = tokenize(code)
        self.assertEqual(tokens[0]['type'], "STRING")

    def test_full_program_snippet(self):
        code = '''
        def greet(name):
            # Greet the user
            print("Hello, " + name)
        '''
        tokens = tokenize(code)
        self.assertTrue(any(t['value'] == 'greet' for t in tokens))
        self.assertTrue(any(t['type'] == 'STRING' for t in tokens))


if __name__ == '__main__':
    unittest.main()
