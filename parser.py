import re
import sys

keywords = {"class", "function", "method", "static", "field", "var", "int", "char", "boolean", "void", "true", "false", "null", "this", "let", "do", "if", "else", "while", "return"}

symbols = {'(', ')', '{', '}', ';', '[', ']', ',', '.', '+', '-', '<', '>', '=', '~', '|', "&", '*', '/'}


# Turns a .jack into a list of tokens
def process_file(filename):
    """
    Reads a file character by character, removes comments manually, and returns a list of tokens.
    """
    # Step 1: Read the file
    with open(filename, 'r') as file:
        chars = list(file.read())

    # Step 2: Remove comments manually
    def remove_comments(chars):
        """
        Removes single-line, block, and JavaDoc comments from a list of characters manually.
        """
        in_single_line_comment = False
        in_block_comment = False
        result = []
        i = 0

        while i < len(chars):
            if in_single_line_comment:
                # End single-line comment at newline
                if chars[i] == '\n':
                    in_single_line_comment = False
                    result.append(chars[i])  # Keep the newline
            elif in_block_comment:
                # End block comment at */
                if chars[i] == '*' and i + 1 < len(chars) and chars[i + 1] == '/':
                    in_block_comment = False
                    i += 1  # Skip '/'
            else:
                # Start of a single-line comment
                if chars[i] == '/' and i + 1 < len(chars) and chars[i + 1] == '/':
                    in_single_line_comment = True
                    i += 1  # Skip the second '/'
                # Start of a block comment
                elif chars[i] == '/' and i + 1 < len(chars) and chars[i + 1] == '*':
                    in_block_comment = True
                    i += 1  # Skip the '*'
                else:
                    # Regular code
                    result.append(chars[i])
            i += 1

        return ''.join(result)

    cleaned_code = remove_comments(chars)

    # Step 3: Tokenize the cleaned code
    # Match words, string constants, or symbols but ignore whitespace
    # Match strings in double quotes and treat them as a single token
    tokens = re.findall(r'"[^"]*"|\w+|[^\s\w]', cleaned_code)

    return tokens


# Turns a list of tokens into an AST
# There is no opertor priority, except the fact that expressions in parenthesis happen first
# Code is just statements and expressions

class Node:
    def __init__(self, value="", type=""):
        """
        Initialize a node with a value and an empty list of children.
        If the type is not provided, it will be determined based on the value.
        """
        self.value = value
        self.type = type
        self.children = []

        # Automatically determine the type if not provided
        if not type:
            if value.startswith('"') and value.endswith('"'):
                # Handle string constants (strip the quotes)
                self.type = "stringConstant"
                self.value = value[1:-1]
            elif value.isdigit():
                # Handle integer constants
                self.type = "integerConstant"
                self.value = int(value)  # Store as an integer
            elif value in keywords:
                # Handle predefined keywords
                self.type = "keyword"
            elif value in symbols:
                self.type = "symbol"
            else:
                self.type = "identifier"

    def add_child(self, child):
        """
        Add a child node to this node.
        """
        self.children.append(child)

    def add_children(self, the_children):
        """
        Add multiple child nodes to this node.
        """
        self.children.extend(the_children)

    def __repr__(self, level=0):
        """
        Return a string representation of the node for debugging, including children.
        It will print the node in a nested format to show its structure.
        """
        indent = "  " * level  # Indentation based on the depth of the node
        result = ""
        if self.value or self.value == 0:
            result = f"{indent}Node(value={repr(self.value)}, type={self.type})\n"
        else:
            result = f"{indent}Node(type={self.type})\n"
        if self.children:
            for child in self.children:
                result += child.__repr__(level + 1)

        return result

    def __str__(self, level=0):
        """
        Return a string representation of the node for debugging, including children.
        It will print the node in a nested format to show its structure.
        """
        indent = "  " * level  # Indentation based on the depth of the node
        result = ""
        if self.value or self.value == 0:
            result = f"{indent}Node(value={repr(self.value)}, type={self.type})\n"
        else:
            result = f"{indent}Node(type={self.type})\n"
        if self.children:
            for child in self.children:
                result += child.__repr__(level + 1)

        return result
    
    
def parse_list_of_token(tokens):
    # Each subfunction treats tokens like a global, deleting from the start when done with each token
    # Sometimes we need to look ahead to the next token, since Jack is not a pure LL(0) language
    # There are only five 'things' in Jack - five types of tokens: keywords, symbols, integerConstants, StringConstants, and identifiers (anything else not starting with a digit)
    # Each token is associated with a type. We can say these nodes 'contain' actual value, they refer to actual tokens and do not point to other nodes
    # However, we need to add structure
    # Structures are:
    # class, classVarDec, subroutineDec, parameterList, subroutineBody, varDec
    # statements, whileStatement, ifStatement, returnStatement, letStatement, doStatement
    # expression, term, and expressionList
    # Each structure (called terminal elements in the book) creates a node of that type. Instead of holding a value, it holds a list of nodes.

    head = tokens[0] if tokens else None

    # Helper functions
    def parse_class():
        # Creates a class node with a list of children
        class_node = Node("", 'class')
        #'class', className, '{'
        class_node.add_children([Node(tokens.pop(0), "keyword"),Node(tokens.pop(0), "identifier"), Node(tokens.pop(0), "symbol")])
        while tokens[0] in {"static", "field"}:
            class_node.add_child(parse_classVarDec())

        while tokens[0] in {"constructor", "function", "method"}:
            class_node.add_child(parse_subroutineDec())

        class_node.add_child(Node(tokens.pop(0), "symbol"))  # '}'
        return class_node

    def parse_classVarDec():
        classVar_node = Node("", 'classVarDec')
        children = [Node(tokens.pop(0), "keyword"), Node(tokens.pop(0))]  # 'static' or 'field', type

        while True:
            children.append(Node(tokens.pop(0), "identifier"))  # varName
            if tokens[0] != ',':
                break
            children.append(Node(tokens.pop(0), "symbol"))  # ','

        children.append(Node(tokens.pop(0), "symbol"))  # ';'
        classVar_node.add_children(children)
        return classVar_node

    def parse_subroutineDec():
        subroutineDec_node = Node("", 'subroutineDec')
        subroutineDec_node.add_children([
            Node(tokens.pop(0), "keyword"),  # 'constructor', 'function', or 'method'
            Node(tokens.pop(0)),  # 'void' or type
            Node(tokens.pop(0), "identifier"),  # subroutineName
            Node(tokens.pop(0), "symbol")  # '('
        ])
        subroutineDec_node.add_child(parse_parameterList())
        subroutineDec_node.add_children([
            Node(tokens.pop(0), "symbol"),  # ')'
            parse_subroutineBody()
        ])
        return subroutineDec_node

    def parse_parameterList():
        parameterList_node = Node("", 'parameterList')
        while tokens[0] != ')':
            #type varName
            parameterList_node.add_children([Node(tokens.pop(0)), Node(tokens.pop(0), "identifier")])
            if tokens[0] == ',':
                parameterList_node.add_child(Node(tokens.pop(0), "symbol"))  # ','
        return parameterList_node

    def parse_subroutineBody():
        # { varDecs* statements }
        subroutineBody_node = Node("", 'subroutineBody')
        subroutineBody_node.add_child(Node(tokens.pop(0), "symbol"))  # '{'
        while tokens[0] == 'var':
            subroutineBody_node.add_child(parse_varDec())
        subroutineBody_node.add_children([parse_statements(), Node(tokens.pop(0), "symbol")])
        return subroutineBody_node

    def parse_varDec():
        varDec_node = Node("", 'varDec')
        varDec_node.add_child(Node(tokens.pop(0), "keyword"))  # 'var'
        varDec_node.add_child(Node(tokens.pop(0)))  # type

        while True:
            varDec_node.add_child(Node(tokens.pop(0), "identifier"))  # varName (identifier)
            if tokens[0] != ',':
                break
            varDec_node.add_child(Node(tokens.pop(0), "symbol"))  # ','

        varDec_node.add_child(Node(tokens.pop(0), "symbol"))  # ';'
        return varDec_node

    def parse_statements():
        statements_node = Node("", "statements")

        dispatch_table = {
            "let": parse_letStatement,
            "if": parse_ifStatement,
            "while": parse_whileStatement,
            "do": parse_doStatement,
            "return": parse_returnStatement
        }

        while tokens and tokens[0] in dispatch_table:
            statements_node.add_child(dispatch_table[tokens.pop(0)]())

        return statements_node

    def parse_letStatement():
        letStatement_node = Node("", "letStatement")
        children = [
            Node(tokens.pop(0), "keyword"),  # 'let'
            Node(tokens.pop(0), "identifier")  # varName
        ]

        if tokens[0] == '[':
            children.extend([
                Node(tokens.pop(0), "symbol"),  # '['
                parse_expression(),
                Node(tokens.pop(0), "symbol")   # ']'
            ])

        children.extend([
            Node(tokens.pop(0), "symbol"),  # '='
            parse_expression(),
            Node(tokens.pop(0), "symbol")  # ';'
        ])
        letStatement_node.add_children(children)
        return letStatement_node

    def parse_ifStatement():
        ifStatement_node = Node("", "ifStatement")
        children = [
            Node(tokens.pop(0), "keyword"),  # 'if'
            Node(tokens.pop(0), "symbol"),  # '('
            parse_expression(),
            Node(tokens.pop(0), "symbol"),  # ')'
            Node(tokens.pop(0), "symbol"),  # '{'
            parse_statements(),
            Node(tokens.pop(0), "symbol")   # '}'
        ]

        if tokens[0] == 'else':
            children.extend([
                Node(tokens.pop(0), "keyword"),  # 'else'
                Node(tokens.pop(0), "symbol"),  # '{'
                parse_statements(),
                Node(tokens.pop(0), "symbol")   # '}'
            ])

        ifStatement_node.add_children(children)
        return ifStatement_node

    def parse_whileStatement():
        whileStatement_node = Node("", "whileStatement")
        whileStatement_node.add_children([
            Node(tokens.pop(0), "keyword"),  # 'while'
            Node(tokens.pop(0), "symbol"),  # '('
            parse_expression(),
            Node(tokens.pop(0), "symbol"),  # ')'
            Node(tokens.pop(0), "symbol"),  # '{'
            parse_statements(),
            Node(tokens.pop(0), "symbol")  # '}'            
        ])
        return whileStatement_node

    def parse_doStatement():
        doStatement_node = Node("", "doStatement")
        doStatement_node.add_children(
            [Node(tokens.pop(0), "keyword")] + parse_subroutine_call() + [Node(tokens.pop(0), "symbol")]
        )
        return doStatement_node

    def parse_returnStatement():
        returnStatement_node = Node("", "returnStatement")
        returnStatement_node.add_child(Node(tokens.pop(0), "keyword"))  # 'return'
        if tokens[0] != ';':
            returnStatement_node.add_child(parse_expression())
        returnStatement_node.add_child(Node(tokens.pop(0), "symbol"))  # ';'
        return returnStatement_node

    def parse_expression():
        expression_node = Node("", "expression")
        expression_node.add_child(parse_term())

        while tokens[0] in {'+', '-', '*', '/', '&', '|', '<', '>', '='}:
            expression_node.add_child(Node(tokens.pop(0), "symbol"))  # op
            expression_node.add_child(parse_term())

        return expression_node

    def parse_term():
        term_node = Node("", "term")

        if tokens[0].isdigit():
            term_node.add_child(Node(tokens.pop(0), "integerConstant"))
        elif tokens[0].startswith('"'):
            term_node.add_child(Node(tokens.pop(0)[1:-1], "stringConstant"))
        elif tokens[0] in {"true", "false", "null", "this"}:
            term_node.add_child(Node(tokens.pop(0), "keyword"))
        elif tokens[0] == '(':
            #( expression )
            term_node.add_children([Node(tokens.pop(0), "symbol") , parse_expression(), Node(tokens.pop(0), "symbol")])
        elif tokens[0] in {'-', '~'}:
            term_node.add_children([Node(tokens.pop(0), "symbol"), parse_term()])
        elif len(tokens) > 1 and tokens[1] == '[':
            #varName [ expression ]
            term_node.add_children([Node(tokens.pop(0), "identifier"), Node(tokens.pop(0), "symbol"), parse_expression(), Node(tokens.pop(0), "symbol")])
        elif len(tokens) > 1 and tokens[1] in {'.', '('}:
            term_node.add_children(parse_subroutine_call())
        else:
            term_node.add_child(Node(tokens.pop(0), "identifier"))  # varName

        return term_node

    def parse_expressionList():
        expressionList_node = Node("", "expressionList")
        if tokens[0] != ')':
            expressionList_node.add_child(parse_expression())
            while tokens[0] == ',':
                #, expression
                expressionList_node.add_children([Node(tokens.pop(0), "symbol"), parse_expression()])
        return expressionList_node

    def parse_subroutine_call():
        subroutine_call_nodes = []
        subroutine_call_nodes.append(Node(tokens.pop(0), "identifier"))  # subroutineName or className/varName

        if tokens[0] == '.':
            subroutine_call_nodes.extend([
                Node(tokens.pop(0), "symbol"),  # '.'
                Node(tokens.pop(0), "identifier")  # subroutineName  
            ])

        subroutine_call_nodes.extend([
            Node(tokens.pop(0), "symbol"),  # '('
            parse_expressionList(),
            Node(tokens.pop(0), "symbol")  # ')'  
        ])

        return subroutine_call_nodes

    if head == 'class':
        return parse_class()

    elif head in {"field", "static"}:
        return parse_classVarDec()

    elif head in {"constructor", "function", "method"}:
        return parse_subroutineDec()

    elif head == 'var':
        return parse_varDec()

    elif head in {"while", "let", "if", "return", "do"}:
        return parse_statements()


# Example usage
# create_xml_file('Foo.jack')  # This will generate 'Foo.xml'

def create_xml_file(filename):
    # Step 1: Process the file to get the list of tokens
    tokens = process_file(filename)

    # Step 2: Parse the list of tokens to generate the node tree
    node_tree = parse_list_of_token(tokens)

    # Step 3: Convert the node tree to an XML string
    xml_string = convert_to_xml(node_tree)

    # Step 4: Save the XML string to a file
    xml_filename = filename.rsplit('.', 1)[0] + '.xml'  # Replace .jack with .xml
    with open(xml_filename, 'w') as f:
        f.write(xml_string)
    print(f"XML file saved as {xml_filename}")


def convert_to_xml(node, level=0):
    """
    Recursively converts a node tree to XML format as a string, manually doing DFS.
    - Nodes with children are formatted with indented children on new lines.
    - Nodes with no children are formatted on a single line.
    """
    indent = "  " * level  # Current indentation based on depth level
    xml_str = ""

    if isinstance(node, Node):
        if node.children:
            # Nodes with children: opening tag, children on new lines, closing tag
            xml_str += f"{indent}<{node.type}>\n"
            for child in node.children:
                xml_str += convert_to_xml(child, level + 1)
            xml_str += f"{indent}</{node.type}>\n"
        else:
            # Nodes with no children: single-line tag
            if node.value:
                #XML weirdness
                if node.value == '<':
                    xml_str += f"{indent}<{node.type}> &lt; </{node.type}>\n"
                elif node.value == '>':
                    xml_str += f"{indent}<{node.type}> &gt; </{node.type}>\n"
                elif node.value == '&':
                    xml_str += f"{indent}<{node.type}> &amp; </{node.type}>\n"
                else:
                    xml_str += f"{indent}<{node.type}> {node.value} </{node.type}>\n"
            else:
                xml_str += f"{indent}<{node.type}>\n{indent}</{node.type}>\n"

    return xml_str

# Run the script with a file as input
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 parser.py <filename>")
    else:
        filename = sys.argv[1]
        try:
            create_xml_file(filename)
            print(parse_list_of_token( process_file(filename)))
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")