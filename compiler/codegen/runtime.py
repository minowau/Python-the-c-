# Runtime Component Module

# This module will enhance the runtime system for efficient memory management and type handling.

class Runtime:
    def __init__(self):
        self.stack = []
        self.variables = {}
        self.type_map = {}

    def _check_type(self, value, expected_type):
        """Verify value type matches expected type."""
        if not isinstance(value, expected_type):
            raise TypeError(f"Expected {expected_type}, got {type(value)}")

    def _execute_function(self, func_name, args):
        """Execute a built-in function with given arguments."""
        if func_name == 'print':
            print(*args)
            return None
        elif func_name == 'len':
            return len(args[0])
        elif func_name == 'max':
            return max(args)
        elif func_name == 'min':
            return min(args)
        else:
            raise NameError(f"Function {func_name} not defined")

    def _memory_check(self):
        """Perform memory usage check and cleanup."""
        if len(self.stack) > 1000:
            self.stack = self.stack[-100:]
        if len(self.variables) > 100:
            oldest = next(iter(self.variables))
            del self.variables[oldest]

    def execute(self, bytecode):
        """Execute the given bytecode."""
        pc = 0
        while pc < len(bytecode):
            instruction, *args = bytecode[pc]
            if instruction == 'PUSH_CONST':
                self._check_type(args[0], (int, float, str))
                self.stack.append(args[0])
            elif instruction == 'LOAD_VAR':
                value = self.variables.get(args[0], None)
                if value is not None:
                    self._check_type(value, self.type_map.get(args[0], type(value)))
                self.stack.append(value)
            elif instruction == 'STORE_VAR':
                value = self.stack.pop()
                self.type_map[args[0]] = type(value)
                self.variables[args[0]] = value
            elif instruction == 'BINARY_OP':
                right = self.stack.pop()
                left = self.stack.pop()
                self._check_type(left, (int, float))
                self._check_type(right, (int, float))
                if args[0] == '+':
                    self.stack.append(left + right)
                elif args[0] == '-':
                    self.stack.append(left - right)
                elif args[0] == '*':
                    self.stack.append(left * right)
                elif args[0] == '/':
                    self.stack.append(left / right)
            elif instruction == 'PRINT':
                print(self.stack.pop())
            elif instruction == 'JUMP_IF_FALSE':
                if not self.stack.pop():
                    pc = args[0] - 1
            elif instruction == 'JUMP':
                pc = args[0] - 1
            elif instruction == 'CALL_FUNCTION':
                func_name, arg_count = args
                args = [self.stack.pop() for _ in range(arg_count)]
                self.stack.append(self._execute_function(func_name, args))
            self._memory_check()
            pc += 1