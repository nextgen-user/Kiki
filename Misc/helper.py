# default_api.keep_listening_for_follow_up(reason='User wants to know if timer is running successfully.')
# [FunctionCall(id='function-call-3447380871376185328', args={'reason': 'User wants to know if timer is running successfully.'}, name='keep_listening_for_follow_up')]
import ast

def parse_function_call_string(call_string: str) -> tuple[str, dict]:
    """
    Parses a string representation of a function call into its name and arguments.

    Args:
        call_string: The string to parse, e.g.,
                     "module.func_name(param1='value1', param2=123)"

    Returns:
        A tuple containing:
        - name (str): The function name (e.g., "func_name").
        - args (dict): A dictionary of arguments (e.g., {'param1': 'value1', 'param2': 123}).

    Raises:
        ValueError: If the input string is malformed.
    """
    try:
        open_paren_index = call_string.index('(')

        close_paren_index = call_string.rindex(')')
    except ValueError:
        raise ValueError("Malformed function call string: Missing parentheses.")

    full_name_part = call_string[:open_paren_index]

    if '.' in full_name_part:
        function_name = full_name_part.split('.')[-1]
    else:
        function_name = full_name_part

    args_str = call_string[open_paren_index + 1:close_paren_index].strip()

    parsed_args = {}
    if not args_str: # No arguments
        return function_name, parsed_args
    try:
        tree = ast.parse(f"dummy_func({args_str})")
    except SyntaxError as e:
        raise ValueError(f"Malformed arguments string: '{args_str}'. Error: {e}")
    if not (tree.body and isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, ast.Call)):
        raise ValueError("Could not parse arguments into a function call structure.")

    call_node = tree.body[0].value
    for keyword in call_node.keywords:
        arg_name = keyword.arg
        try:
            arg_value = ast.literal_eval(keyword.value)
        except ValueError as e:
            raise ValueError(f"Could not evaluate argument '{arg_name}' value. Error: {e}")
        parsed_args[arg_name] = arg_value

    return function_name, parsed_args

# input_string1 = 'print(default_api.search_web(query="print(hellowrold)"))'
# codee= input_string1.replace("print(","")
# codee=codee[:-1]
# print(codee)
# name1, args1 = parse_function_call_string(codee)
# print(f"name=\"{name1}\"")
# print(f"args={args1}")