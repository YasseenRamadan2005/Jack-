import sys
from parser import *
import os
import traceback
from Program_State import A_Program_State
#Now I need to turn a .jack file into a .vm file
#Specifically, I have to compile the type of nodes: class, subroutineDec, statements, expressions
    # Structures are:
    # class, classVarDec, subroutineDec, parameterList, subroutineBody, varDec
    # statements, whileStatement, ifStatement, returnStatement, letStatement, doStatement
    # expression, term, and expressionList


#When compiling a node, ideally we should return a list of VM instructions. Or we add an item to a symbol table
def compile_tree(node: Node, the_Program: A_Program_State):
                   
    def compile_subroutine_call(nodes: list) -> list:
        """
        Compiles a subroutine call into VM instructions.
        """
        vm_instructions = []

        # Count the number of arguments in the expression list
        amount_of_arguments = 0
        for node in nodes[-2].children:
            if node.type == "expression":
                amount_of_arguments += 1
                vm_instructions.extend(compile_tree(node, the_Program))

        if len(nodes) in [4, 6]:  # Support for `func(args)` and `Class.func(args)`
            if len(nodes) == 6:
                # Handling `foo.bar(...)`, which could be a function or method call
                the_foo = nodes[0].value
                # Check if `foo` is a variable (method call) or a class (function call)
                symbol = the_Program.lookup_symbol(the_foo)
                if symbol:  # `the_foo` is a variable (method call)
                    vm_instructions.insert(0, the_Program.handle_var_name(the_foo, True)[0])
                    class_name = symbol[0]
                    vm_instructions.append(f"call {class_name}.{nodes[2].value}.{amount_of_arguments + 1} {amount_of_arguments + 1}")
                else:  # `the_foo` is a class (function call)
                    vm_instructions.append(f"call {nodes[0].value}.{nodes[2].value}.{amount_of_arguments} {amount_of_arguments}")
            else:
                # Handling `foo(...)`, which is a method within the current class. Therefore I don't need to push the pointer, saving instructions
                vm_instructions.extend(["push pointer 0", f"call {the_Program.get_class_name()}.{nodes[0].value}.{amount_of_arguments + 1} {amount_of_arguments + 1}"])

        return vm_instructions


    match node.type:
        case "class":
            "'class': className '{' classVarDec* subroutineDec* '}'"
            the_Program.set_class_name(node.children[1].value)
            return [
                instr for child in node.children[2:-1]
                for instr in compile_tree(child, the_Program)
            ]

        case "classVarDec":
            "classVarDec: ('static'|'field') type varName (',' varName)* ';'"
            for child in node.children[2:]:
                if child.type == "identifier":
                    the_Program.add_to_class_ST(child.value, node.children[1].value, node.children[0].value)
            return []

        case "subroutineDec":
            "('constructor'|'function'|'method') ('void' | type) subroutineName '(' parameterList ')' subroutineBody"
            the_Program.reset_Subroutine_ST()
            subroutine_type = node.children[0].value
            #If the function is a method, then there is always one "argument" - the pointer to the object
            if subroutine_type == "method":
                the_Program.increment_var_counts_for_a_type("argument")
            the_Program.set_subroutine_name(node.children[2].value)
            compile_tree(node.children[4], the_Program)
            the_Program.add_function_statement_counter()
            vm_instructions = compile_tree(node.children[6], the_Program)
            vm_instructions.insert(0, f"function {the_Program.get_fuction_declaraction_name()} {the_Program.get_var_counts_for_a_type('local')}")
            if subroutine_type == "method":
                vm_instructions[1:1] = ["push argument 0", "pop pointer 0"]
            elif subroutine_type == "constructor":
                vm_instructions[1:1] = [f"push constant {the_Program.get_var_counts_for_a_type('field')}", "call Memory.alloc.1 1", "pop pointer 0"]
            return vm_instructions

        case "parameterList":
            "parameterList: ((type varName) (',' type varName)*)?"
            for i in range(0, len(node.children), 3):
                the_Program.add_to_subroutine_ST(node.children[i + 1].value, node.children[i].value, "argument")
            return []

        case "subroutineBody":
            "subroutineBody: '{' varDec* statements '}'"
            return [instr for child in node.children[1:-1] for instr in compile_tree(child, the_Program)]

        case "varDec":
            "varDec: 'var' type varName (',' varName)* ';'"
            for child in node.children[2:]:
                if child.type == "identifier":
                    the_Program.add_to_subroutine_ST(child.value, node.children[1].value, "local")
            return []

        case "statements":
            "statements: statement*"
            return [instr for child in node.children for instr in compile_tree(child, the_Program)]
        
        #if-goto jumps if the condition is true (when the top of the stack is not zero)

        case "whileStatement":
            "whileStatement: 'while' '(' expression ')' '{' statements '}'"
            #print(node)
            label_format = the_Program.get_fuction_declaraction_name() + ".WHILE." + str(the_Program.get_statement_counter("while"))   
            #print(compile_tree(node.children[5], the_Program), node.children[5])       
            return [f"label {label_format}_BEGIN"] + compile_tree(node.children[2], the_Program) + [f"not", f"if-goto {label_format}_END"] + compile_tree(node.children[5], the_Program) + [f"goto {label_format}_BEGIN", f"label {label_format}_END"]
            

        case "ifStatement":
            "'if' '(' expression ')' '{' statements '}' ('else' '{' statements '}')?"
            label_format = the_Program.get_fuction_declaraction_name() + ".IF." + str(the_Program.get_statement_counter('if'))
            
            #No else:
                #If the expression is not true, continue then jump to end
            
            #With else:
                #If the expression is not true, jump to the second statements
                #Else, execute the first statements then jump to the end
                
            vm_instructions = []
            if len(node.children) > 7:
                vm_instructions += compile_tree(node.children[2], the_Program) + ["not", f"if-goto {label_format}_ELSE"] + compile_tree(node.children[5], the_Program) + [f"goto {label_format}_END", f"label {label_format}_ELSE"] + compile_tree(node.children[9], the_Program) + [f"label {label_format}_END"]
            else:
                vm_instructions += compile_tree(node.children[2], the_Program) + ["not", f"if-goto {label_format}_END"] + compile_tree(node.children[5], the_Program) + [f"label {label_format}_END"]
            return vm_instructions

        case "letStatement":
            "letStatement: 'let' varName ('[' expression ']')? '=' expression ';'"
            var_name = node.children[1].value
            if len(node.children) > 5:  
                return compile_tree(node.children[3], the_Program) + the_Program.handle_var_name(var_name, push=True) + ["add", "pop pointer 1"] + compile_tree(node.children[-2], the_Program) + ["pop that 0"]
            return compile_tree(node.children[-2], the_Program) + the_Program.handle_var_name(var_name, push=False)

        case "doStatement":
            "doStatement: 'do' subroutineCall ';'"
            return compile_subroutine_call(node.children[1:-1]) + ["pop temp 0"]

        case "returnStatement":
            "returnStatement: 'return' expression? ';'"
            if len(node.children) == 3:
                return compile_tree(node.children[1], the_Program) + ["return"]
            else:
                return ["push constant 0", "return"]

        case "expression":
            "term (op term)*"
            vm_instructions = compile_tree(node.children[0], the_Program)
            operators = {"+": "add", "-": "sub", "*": "call Math.multiply.2 2", "/": "call Math.divide.2 2",
                        "&": "and", "|": "or", "<": "lt", ">": "gt", "=": "eq"}
            for i in range(1, len(node.children), 2):
                vm_instructions += compile_tree(node.children[i + 1], the_Program) + [operators[node.children[i].value]]
            return vm_instructions

        case "term":
            """
            term: integerConstant | stringConstant | keywordConstant | varName |
                varName '[' expression ']' | subroutineCall |
                '(' expression ')' | unaryOp term
            """
            first_child = node.children[0]
            
            if first_child.type == "integerConstant":
                return [f"push constant {first_child.value}"]
            
            if first_child.type == "stringConstant":
                return (
                    [f"push constant {len(first_child.value)}", "call String.new.1 1"] + 
                    [f"push constant {ord(c)}\ncall String.appendChar 2" for c in first_child.value]
                )
            
            if first_child.type == "keyword":
                # Map the keyword constants to assembly instructions
                return {
                    "true": ["push constant 1", "neg"],
                    "false": ["push constant 0"],
                    "null": ["push constant 0"],
                    "this": ["push pointer 0"]
                }.get(first_child.value, [])
            
            if first_child.type == "identifier" and len(node.children) > 1 and node.children[1].value == "[":
                # Handling array indexing (e.g., varName[expression])
                return (
                    compile_tree(node.children[2], the_Program) + 
                    the_Program.handle_var_name(first_child.value, True) +
                    ["add", "pop pointer 1", "push that 0"]
                )

            
            if first_child.type == "identifier" and len(node.children) > 1:
                # Handling subroutine calls (e.g., varName(arg1, arg2))
                return compile_subroutine_call(node.children)
            
            if first_child.type == "identifier":
                # Handling varName
                return the_Program.handle_var_name(first_child.value, True)
            
            if first_child.value == "(":
                # Handling parentheses expression (e.g., (expression))
                return compile_tree(node.children[1], the_Program)
            
            if first_child.type == "symbol" and first_child.value in "-~":
                # Handling unary operators (e.g., -term or ~term)
                #- is arithmetic negation;
                #~ is  boolean negation
                return compile_tree(node.children[1], the_Program) + [{"-": "neg", "~": "not"}[first_child.value]]
            
            return []


        case "expressionList":
            "(expression (',' expression)* )?"
            return [instr for i in range(0, len(node.children), 2) for instr in compile_tree(node.children[i], the_Program)]

        case _:
            return []

def create_vm_file(filename):
    # Step 1: Process the file to get the list of tokens
    tokens = process_file(filename)

    # Step 2: Parse the list of tokens to generate the node tree
    node_tree = parse_list_of_token(tokens)

    # Step 3: Convert the node tree to an XML string
    list_of_vm_instructions = compile_tree(node_tree, A_Program_State(""))

    # Step 4: Save the XML string to a file
    vm_filename = filename.rsplit('.', 1)[0] + '.vm'  # Replace .jack with .xml
    with open(vm_filename, 'w') as f:
        for instruction in list_of_vm_instructions:
            f.write(instruction + "\n")
    print(f"VM file saved as {vm_filename}")

def process_directory(directory):
    # Process each .jack file in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".jack"):
            file_path = os.path.join(directory, filename)
            try:
                create_vm_file(file_path)
                print(f"Successfully created VM file from {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}, {traceback.format_exc()}")
                
                
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 compiler.py <filename or directory>")
    else:
        input_path = sys.argv[1]
        
        if os.path.isdir(input_path):
            # If input is a directory, process all .jack files in the directory
            process_directory(input_path)
        elif os.path.isfile(input_path) and input_path.endswith(".jack"):
            # If input is a single file, process that specific file
            try:
                create_vm_file(input_path)
                print(f"Successfully created VM file from {input_path}")
            except FileNotFoundError:
                print(f"Error: File '{input_path}' not found.")
            except Exception as e:
                print(f"An unexpected error occurred while processing {input_path}: {e}, {traceback.format_exc()}")
        else:
            print("Error: Please provide a valid .jack file or a directory containing .jack files.")
