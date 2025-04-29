import re

KEYWORDS = {
    "def": "DEF", "return": "RETURN", "if": "IF", "elif": "ELIF", "else": "ELSE",
    "while": "WHILE", "for": "FOR", "in": "IN", "import": "IMPORT", "as": "AS", "from": "FROM",
    "class": "CLASS", "try": "TRY", "except": "EXCEPT", "finally": "FINALLY", "with": "WITH",
    "pass": "PASS", "break": "BREAK", "continue": "CONTINUE", "and": "AND", "or": "OR", "not": "NOT",
    "is": "IS", "None": "NONE", "True": "TRUE", "False": "FALSE", "async": "ASYNC", "await": "AWAIT"
}

DELIMITERS = {
    '(': "LPAREN", ')': "RPAREN", ':': "COLON", ',': "COMMA",
    '[': "LBRACKET", ']': "RBRACKET", '{': "LBRACE", '}': "RBRACE",
    ';': "SEMICOLON"
}

DOUBLE_CHAR_OPS = {"==", "!=", "<=", ">=", "**", "//", "<<", ">>", "+=", "-=", "*=", "/=", "%=", "**=", "//=", "<<=", ">>="}
SINGLE_CHAR_OPS = set("+-*/%=<>!&|^~")

def token(value, type_, line=1, col=1):
    return {"value": value, "type": type_, "line": line, "col": col}

def is_alpha(ch): return ch.isalpha()
def is_digit(ch): return ch.isdigit()
def is_alnum(ch): return ch.isalnum() or ch == "_"
def is_whitespace(ch): return ch in [' ', '\t', '\r']
def is_newline(ch): return ch == '\n'

def tokenize(source_code):
    tokens = []
    indent_stack = [0]
    src = list(source_code)
    i, line, col = 0, 1, 1

    def handle_indentations(current_indent):
        nonlocal tokens
        prev_indent = indent_stack[-1]
        if current_indent > prev_indent:
            indent_stack.append(current_indent)
            tokens.append(token("INDENT", "INDENT", line, col))
        while current_indent < prev_indent:
            indent_stack.pop()
            tokens.append(token("DEDENT", "DEDENT", line, col))
            prev_indent = indent_stack[-1]

    while i < len(src):
        ch = src[i]

        if is_newline(ch):
            tokens.append(token("\n", "NEWLINE", line, col))
            i += 1
            col = 1
            # Measure indent level on next line
            start_i = i
            current_indent = 0
            while i < len(src) and src[i] in (' ', '\t'):
                current_indent += 4 if src[i] == '\t' else 1
                i += 1
            handle_indentations(current_indent)
            continue

        if is_whitespace(ch):
            col += 1
            i += 1
            continue

        if ch == "#":
            while i < len(src) and not is_newline(src[i]):
                i += 1
            continue

        if ch in DELIMITERS:
            tokens.append(token(ch, DELIMITERS[ch], line, col))
            col += 1
            i += 1
            continue

        if i + 2 < len(src) and src[i:i+3] == ['"', '"', '"']:
            value = '"""'
            i += 3
            while i + 2 < len(src) and src[i:i+3] != ['"', '"', '"']:
                value += src[i]
                if src[i] == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1
            if i + 2 < len(src):
                value += '"""'
                i += 3
                tokens.append(token(value, "STRING", line, col))
            else:
                raise Exception("Unterminated triple-quoted string")
            continue

        if ch in ('"', "'"):
            quote_type = ch
            value = ch
            i += 1
            while i < len(src) and src[i] != quote_type:
                if src[i] == "\\":
                    value += src[i] + src[i + 1]
                    i += 2
                    continue
                value += src[i]
                i += 1
            if i < len(src):
                value += src[i]
                i += 1
                tokens.append(token(value, "STRING", line, col))
            else:
                raise Exception("Unterminated string literal")
            continue

        if is_digit(ch):
            num = ""
            has_dot = False
            while i < len(src) and (is_digit(src[i]) or src[i] in "eE.+-_"):
                num += src[i]
                if src[i] == '.':
                    has_dot = True
                i += 1
            tokens.append(token(num, "NUMBER", line, col))
            continue

        if i + 1 < len(src) and ''.join(src[i:i+2]) in DOUBLE_CHAR_OPS:
            op = ''.join(src[i:i+2])
            tokens.append(token(op, "OPERATOR", line, col))
            i += 2
            continue
        elif ch in SINGLE_CHAR_OPS:
            tokens.append(token(ch, "OPERATOR", line, col))
            i += 1
            continue

        if is_alpha(ch) or ch == "_":
            ident = ""
            while i < len(src) and is_alnum(src[i]):
                ident += src[i]
                i += 1
            token_type = KEYWORDS.get(ident, "IDENTIFIER")
            tokens.append(token(ident, token_type, line, col))
            continue

        raise Exception(f"Unexpected character at line {line}, column {col}: {ch}")

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(token("DEDENT", "DEDENT", line, col))

    tokens.append(token("EOF", "EOF", line, col))
    return tokens
