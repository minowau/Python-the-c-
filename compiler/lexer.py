# compiler/lexer.py

KEYWORDS = {
    "def": "DEF",
    "return": "RETURN",
    "if": "IF",
    "elif": "ELIF",
    "else": "ELSE",
    "while": "WHILE",
    "for": "FOR",
    "in": "IN",
    "import": "IMPORT",
    "as": "AS",
    "from": "FROM",
    "class": "CLASS",
    "try": "TRY",
    "except": "EXCEPT",
    "finally": "FINALLY",
    "with": "WITH",
    "pass": "PASS",
    "break": "BREAK",
    "continue": "CONTINUE",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "is": "IS",
    "None": "NONE",
    "True": "TRUE",
    "False": "FALSE"
}

def token(value, type_):
    return {"value": value, "type": type_}

def is_alpha(ch):
    return ch.isalpha()

def is_digit(ch):
    return ch.isdigit()

def is_alnum(ch):
    return ch.isalnum() or ch == "_"

def is_whitespace(ch):
    return ch in [' ', '\t', '\r']

def is_newline(ch):
    return ch == '\n'

def tokenize(source_code):
    tokens = []
    src = list(source_code)
    i = 0

    while i < len(src):
        ch = src[i]

        # Skip whitespace
        if is_whitespace(ch):
            i += 1
            continue

        # Handle newlines
        if is_newline(ch):
            tokens.append(token("\n", "NEWLINE"))
            i += 1
            continue

        # Handle comments (single-line)
        if ch == "#":
            while i < len(src) and not is_newline(src[i]):
                i += 1
            continue

        # Handle parentheses, colons, commas, and braces
        if ch in '():,[]{}':
            token_type = {
                '(': "LPAREN", ')': "RPAREN",
                ':': "COLON", ',': "COMMA",
                '[': "LBRACKET", ']': "RBRACKET",
                '{': "LBRACE", '}': "RBRACE",
                ';': "SEMICOLON"
            }[ch]
            tokens.append(token(ch, token_type))
            i += 1
            continue

        # Handle semicolon
        if ch == ";":
            tokens.append(token(ch, "SEMICOLON"))
            i += 1
            continue

        # Handle string literals with mixed quotes
        if ch in ('"', "'"):
            quote_type = ch
            value = ch
            i += 1
            while i < len(src) and src[i] != quote_type:
                value += src[i]
                i += 1
            if i < len(src):
                value += src[i]  # closing quote
                i += 1
                tokens.append(token(value, "STRING"))
            else:
                raise Exception("Unterminated string literal")
            continue

        # Handle numbers, including large integers
        if is_digit(ch):
            num = ""
            while i < len(src) and (is_digit(src[i]) or src[i] == '.'):
                num += src[i]
                i += 1
            tokens.append(token(num, "NUMBER"))
            continue

        # Handle operators
        double_char_ops = {"==", "!=", "<=", ">=", "**", "//", "&&", "||"}
        if i + 1 < len(src) and src[i:i+2] in map(list, double_char_ops):
            op = src[i] + src[i+1]
            tokens.append(token(op, "OPERATOR"))
            i += 2
            continue
        elif ch in "+-*/%=<>!":
            tokens.append(token(ch, "OPERATOR"))
            i += 1
            continue

        # Handle identifiers and keywords
        if is_alpha(ch) or ch == "_":
            ident = ""
            while i < len(src) and is_alnum(src[i]):
                ident += src[i]
                i += 1
            if ident in KEYWORDS:
                tokens.append(token(ident, KEYWORDS[ident]))
            else:
                tokens.append(token(ident, "IDENTIFIER"))
            continue

        # If no valid token is found, raise an error
        raise Exception(f"Unexpected character: {ch}")

    # Add the EOF token at the end
    tokens.append(token("EOF", "EOF"))
    return tokens
