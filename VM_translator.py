from enum import Enum
import sys
import os
# We need to keep track of the current scope when translating
current_file = ""
current_function = ""
# 1. Address (string + number)
    #Push + address
    #Pop + address
# 4. Call + string + number
# 5. Return
# 6. Function + string + number
# 7. Math instructions ('add', 'sub', 'or', 'and' and 'neg' and 'not')
# 8. Comparison instructions (gt, eq, lt)



class AddressType(Enum):
    CONSTANT = "constant"
    POINTER = "pointer"
    TEMP = "temp"
    THIS = "this"
    THAT = "that"
    STATIC = "static"
    ARGUMENT = "argument"
    LOCAL = "local"

class Math_Instruction(Enum):
    add = "add"
    subtract = "sub"
    bitwise_or = "or"
    bitwise_and = "and"
    negate = "neg"
    bitwise_not = "not"

class Compare_Instruction(Enum):
    gt = "gt"
    lt = "lt"
    eq = "eq"
    
C_I_mapping = {
    "gt" : 0,
    "lt" : 0,
    "eq" : 0
}

class Address:
    def __init__(self, string_part: AddressType, number_part: int):
        self.s = string_part
        self.n = number_part

    def __repr__(self):
        return f"Address(type={self.s.name}, number={self.n})"

    def get_shortened_name(self) -> str:
        match self.s:
            case AddressType.THIS:
                return "THIS"
            case AddressType.THAT:
                return "THAT"
            case AddressType.LOCAL:
                return "LCL"
            case AddressType.ARGUMENT:
                return "ARG"
            case _:
                raise ValueError(f"No shortened name for address type {self.s}")

    #This fuctions sets the A register to the value of the Address. In the case that the address time is a pointer, the A register is set to the pointer value. For example, the adress type "local 5" becomes:
    """
    @5
    D=A
    @LCL
    A=D+M //A is the pointer to the 5th local variable, where as M will be the value of the 5th local variable.
    """
    def set_A_reg_to_address_value(self) -> str:
        global current_file
        if self.s == AddressType.CONSTANT:
            return f"@{self.n}\n"
        if self.s == AddressType.STATIC:
            return f"@{current_file}.{self.n}\n"
        if self.s in {AddressType.TEMP, AddressType.POINTER}:
            base = 5 if self.s == AddressType.TEMP else 3
            return f"@{base + self.n}\n"
        if self.s in {AddressType.LOCAL, AddressType.THAT, AddressType.THIS, AddressType.ARGUMENT}:
            if self.n > 0:
                if self.n < 4:
                    # Base address
                    result = f"@{self.get_shortened_name()}\nA=M+1\n"
                    # Increment A step-by-step for n < 4
                    result += "A=A+1\n" * (self.n - 1)
                    return result
                else:
                    return f"@{self.n}\nD=A\n@{self.get_shortened_name()}\nA=D+M\n"
            return "@" + self.get_shortened_name() + "\nA=M\n"
        raise ValueError(f"Bad AddressType {self.s}")


    def set_D_reg_to_address_value(self) -> str:
        if self.s == AddressType.CONSTANT and self.n in {0,1}:
            return f"D={self.n}\n"
        if self.s == AddressType.CONSTANT:
            return self.set_A_reg_to_address_value() + "D=A\n" 
        return self.set_A_reg_to_address_value() + "D=M\n"

    """
    For pop instructions, it is more efficient to manually increment if the value is less than 8.
        pop local 100
            @100    @SP
            D=A     AM=M-1
            @LCL    D=M
            D=D+M   @LCL
            @13     A=M+1 |1
            M=D     A=A+1 |2
            @SP     A=A+1 |3
            AM=M-1  A=A+1 |4
            D=M     A=A+1 |5
            @13     A=A+1 |6
            A=M     A=A+1 |7
            M=D     M=D
            
    For push instructions, the limit is less than 4.
        push local 100
            @100    @LCL
            D=A     A=M+1 |1
            @LCL    A=A+1 |2
            A=D+M   A=A+1 |3
            D=M     D=M
                @SP
                M=M+1
                A=M-1
                M=D
    """
    #For a pop instruction who's address is unreachable without a register, the pointer is stored @13.
    def pop_to_address(self) -> str:
        result = f"\n//pop {self}\n"
        collect_SP_top = "@SP\nAM=M-1\nD=M\n"
        if self.s in {AddressType.LOCAL, AddressType.THAT, AddressType.THIS, AddressType.ARGUMENT}:
            if self.n < 8:
                if self.n == 0:
                    return result + collect_SP_top + f"@{self.get_shortened_name()}\nA=M\nM=D\n"
                the_amount_of_A_increments = "A=A+1\n" * (self.n - 1)
                return result +  collect_SP_top + f"@{self.get_shortened_name()}\nA=M+1\n{the_amount_of_A_increments}M=D\n"
            return result + f"@{self.n}\nD=A\n@{self.get_shortened_name()}\nD=D+M\n@13\nM=D\n" + collect_SP_top + "@13\nA=M\nM=D\n"
        if self.s in {AddressType.TEMP, AddressType.POINTER, AddressType.STATIC}:
            return result + collect_SP_top + self.set_A_reg_to_address_value() + "M=D\n"
        raise ValueError(f"Bad AddressType in a pop: {self.s}")

    def push_from_address(self) -> str:
        result = f"\n//push {self}\n"
        return result + self.set_D_reg_to_address_value() + "@SP\nAM=M+1\nA=A-1\nM=D\n"
    
def convert_math_instruction(instruction):
    operation_map = {
        "add": "D+M",
        "sub": "M-D",
        "or": "D|M",
        "and": "D&M",
        "neg": "-M",
        "not": "!M"
    }

    if instruction not in operation_map:
        raise ValueError(f"Invalid instruction: {instruction}")

    result = f"\n//{instruction}\n"
    stack_decrement = "@SP\nAM=M-1\nD=M\nA=A-1\n"
    stack_neutral = "@SP\nA=M-1\n"

    return result + (
        f"{stack_decrement}M={operation_map[instruction]}\n"
        if instruction in {"add", "sub", "or", "and"}
        else f"{stack_neutral}M={operation_map[instruction]}\n"
    )


def convert_Compare_Instruction(instruction):
    global current_function
    # Ensure the instruction is valid
    if instruction not in Compare_Instruction.__members__:
        raise ValueError(f"Invalid instruction: {instruction}")

    the_string_to_return = f"\n//{instruction}\n"
    comp_map = {"lt": "M=-1\n", "eq": "M=0\n", "gt": "M=1\n"}
    return_label = (
        f"{current_function}.{instruction}.{C_I_mapping[instruction]}"
    )
        
    the_string_to_return += (
            f"@{return_label}\nD=A\n@14\n"
            f"{comp_map[instruction]}"
            "@COMP_BEGIN\n0;JMP\n"
            f"({return_label})\n"
        )
    C_I_mapping[instruction] += 1
    return the_string_to_return

def convert_return():
    return f"\n//return\n@RETURN\n0;JMP\n"


"""
I can assume function foo in class Bar with k arguments will be compliled as function "function Bar.foo.k"
Each function has it's call number - the amount of times it calls another function.
This is used to generate unique return addresses for each function called"""

func_mapping = {"": 0}


def convert_call(name_of_the_function_im_calling, number_of_arguments):
    #When I jump to the pre-defined CALL subroutine, I need the return address in the D register already, the function pointer in @13, and the number of arguments plus 5 in @14
    func_mapping[current_function] += 1
    return f"""\n//call {name_of_the_function_im_calling}
@{number_of_arguments + 5}
D=A
@14
M=D
@{name_of_the_function_im_calling}
D=A
@13
M=D
@{current_function}$ret.{func_mapping[current_function]}
D=A
@CALL
0;JMP
({current_function}$ret.{func_mapping[current_function]})

    """


def convert_function(name_of_the_function, number_of_lcls):
    global current_function
    func_mapping[f"{name_of_the_function}"] = 0
    current_function = name_of_the_function
    initializing_the_lcls = Address(AddressType.CONSTANT, 0).push_from_address() * int(number_of_lcls)
    return f"""\n//function {name_of_the_function} with {number_of_lcls}
({name_of_the_function}){initializing_the_lcls}
    """

def convert_lbl(name_of_the_label):
    global current_file
    global current_function
    return f"\n//label {name_of_the_label[1]}\n({current_function}${name_of_the_label[1]})\n"

def convert_goto(name_of_the_label):
    global current_file
    global current_function
    return f"\n//goto {name_of_the_label}\n@{current_function}${name_of_the_label[1]}\n0;JMP\n"
    
def convert_if_goto(label_name):
    print(label_name)
    global current_file
    global current_function
    return f"\n//if-goto {label_name}\n@SP\nAM=M-1\nD=M\n" + f"@{current_function}${label_name[1]}\nD;JNE\n"



#This is the code for comparison instructions and call/return. It does not set SP to 256 initially and it does not call Sys.init
def give_starter_code() -> str:
    """
    Returns the string containing the starter code.
    """
    with open("starter_code.txt", "r") as starter_file:
        return starter_file.read()

#This is bootstrap code. It sets SP to 256. Then it calls Sys.init. This assume we have the starter code.
def give_boot_strap_code():
    result = "@256\nD=A\n@SP\n\nM=D\n"
    #Since Sys.vm goes into an infinite loop after calling the OS inital functions and then calling Main.main, we don't care about the name of the "function" that calls Sys.init 
    global current_file
    current_file = ""
    result += convert_call("Sys.init", 0)
    return result


def remove_comments(lines):
    """
    Removes comments from each line in the given list of lines.
    :param lines: List of VM instructions.
    :return: List of instructions without comments.
    """
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.split("//")[0].strip()  # Remove comments and whitespace
        if cleaned_line:  # Keep non-empty lines
            cleaned_lines.append(cleaned_line)
    return cleaned_lines

#When being run directly, the code translates a spefic .vm file into it's associated .asm file - without the starter code.
def translate_vm(vm_filename: str):
    """
    Translates a single .vm file into its corresponding .asm file.
    """
    print(f"Translating: {vm_filename}")
    
    # Read VM file content
    with open(vm_filename, 'r') as vm_file:
        lines = remove_comments(vm_file.readlines())

    asm_filename = vm_filename.replace('.vm', '.asm')
    with open(asm_filename, 'a') as asm_file:
        global current_file
        current_file = os.path.splitext(os.path.basename(vm_filename))[0]
        
        command_map = {
            "push": lambda parts: Address(AddressType[parts[1].upper()], int(parts[2])).push_from_address(),
            "pop": lambda parts: Address(AddressType[parts[1].upper()], int(parts[2])).pop_to_address(),
            "add": convert_math_instruction, "sub": convert_math_instruction,
            "neg": convert_math_instruction, "and": convert_math_instruction,
            "or": convert_math_instruction, "not": convert_math_instruction,
            "eq": convert_Compare_Instruction, "gt": convert_Compare_Instruction, "lt": convert_Compare_Instruction,
            "label": convert_lbl, "goto": convert_goto, "if-goto": convert_if_goto,
            "function": lambda parts: convert_function(parts[1], int(parts[2])),
            "call": lambda parts: convert_call(parts[1], int(parts[2])),
            "return": lambda _: convert_return()
        }

        for line in lines:
            parts = line.split()
            command = parts[0].lower()
            if command in command_map:
                asm_file.write(command_map[command](parts) if command in {"push", "pop", "function", "call", "goto", "if-goto", "label"} else command_map[command](command))
            else:
                raise ValueError(f"Unrecognized VM command: {line}")



def give_bootstrap_code():
    """
    Generates the bootstrap code that initializes the stack pointer and calls Sys.init.
    """
    return """// Bootstrap code
@256
D=A
@SP
M=D
""" + convert_call("Sys.init", 0)


def translate_directory(directory_name: str):
    """
    Translates all VM files in a directory.
    If `Sys.vm` is found, generates a single combined `.asm` file with bootstrap code.
    Otherwise, each file is translated independently with starter code.
    The final combined .asm file is named after the lowest directory.
    """
    print(f"Translating directory: {directory_name}")

    # Collect all .vm files in the directory
    vm_files = [os.path.join(directory_name, f) for f in os.listdir(directory_name) if f.endswith(".vm")]

    if not vm_files:
        raise ValueError(f"No .vm files found in the directory: {directory_name}")

    # Get the name of the lowest directory
    directory_base_name = os.path.basename(os.path.normpath(directory_name))

    # Check if Sys.vm is present
    sys_vm_present = any(os.path.basename(file) == "Sys.vm" for file in vm_files)

    if sys_vm_present:
        # Create the name for the combined output .asm file
        combined_asm_filename = os.path.join(directory_name, f"{directory_base_name}.asm")
        
        # Create a temporary file for writing
        temp_asm_filename = os.path.join(directory_name, ".temp.asm")
        print(f"Temporary file: {temp_asm_filename}")

        with open(temp_asm_filename, "w") as temp_asm_file:
            # Write bootstrap code
            temp_asm_file.write(give_bootstrap_code() + "\n")
            
            # Append starter code
            temp_asm_file.write(give_starter_code() + "\n")
            
            # Translate each VM file and append its content to the temp file
            for vm_file in vm_files:
                print(f"Translating file: {vm_file}")
                translate_vm(vm_file)  # Generates a separate .asm file for each .vm file
                asm_file = vm_file.replace(".vm", ".asm")
                with open(asm_file, "r") as individual_asm_file:
                    temp_asm_file.write(individual_asm_file.read())
                os.remove(asm_file)  # Clean up the individual .asm file

        # Rename the temp file to the final combined .asm file
        os.rename(temp_asm_filename, combined_asm_filename)
        print(f"Final combined file: {combined_asm_filename}")
    else:
        # If Sys.vm is not present, translate each file independently with starter code
        starter_code = give_starter_code()
        for vm_file in vm_files:
            asm_file_name = vm_file.replace(".vm", ".asm")
            with open(asm_file_name, "w") as asm_file:
                asm_file.write(starter_code + "\n")  # Write starter code to each file
            print(f"Translating file independently: {vm_file}")
            translate_vm(vm_file)  # Append VM translation to the respective .asm file
      
      
            
#Recieve a foo.vm filw and return a g_foo.vim file        
def group(filename: str):
    print(f"Grouping: {filename}")
    
    # Read VM file content
    with open(filename, 'r') as vm_file:
        lines = remove_comments(vm_file.readlines())
    new_vm_filename = "g_" + filename
    
    #bookeep
    running_SP_count = 0
    with open(new_vm_filename, 'w') as new_vm_filename:
        for line in lines:
            parts = line.split()
            command = parts[0].lower()
            # Translate VM commands to assembly

            if command == "push":
                new_vm_filename.write(line)
                running_SP_count += 1

            elif command == "pop":
                new_vm_filename.write(line)
                running_SP_count += -1
                
            elif command in {"add", "sub", "and", "or"}:
                new_vm_filename.write(line)
                running_SP_count += -1
                
            elif command in {"neg", "not"}:
                new_vm_filename.write(line)
                running_SP_count += 0
                
            elif command in {"eq", "gt", "lt"}:
                new_vm_filename.write(line)
                running_SP_count += -1
                
            
            elif command == "label":
                new_vm_filename.write(line)
                running_SP_count = 0
                

            elif command == "goto":
                new_vm_filename.write(line)
                running_SP_count = 0
                

            elif command == "if-goto":
                new_vm_filename.write(line)
                running_SP_count = 0
                

            elif command == "function":
                new_vm_filename.write(line)
                running_SP_count = 0
                

            #When calling a function with n arguments, it always turns the N arguments into 1 value. Therefore, it remove N-1. If N was zero, it adds 1
            elif command == "call":
                new_vm_filename.write(line)
                running_SP_count -= int(parts[2]) - 1
                
            
            elif command == "return":
                new_vm_filename.write(line)
                running_SP_count += -1
                
            
            else:
                raise ValueError(f"Unrecognized VM command: {line}")       
            
            
            new_vm_filename.write("\n")
            print(line)
            
            if running_SP_count == 0:
                new_vm_filename.write("\n\n")
    


"""Types of optimizations

1. Push/Pop groups. A push instruction followed by a pop instruction. Even in the worst case scenario, we still save space by not using the stack.

2. A push followed by a neg/not instruction

3. Two pushes followed by a add/sub/or or a gt/lt/eq (can only optimize if they are the same or contants)


"""   
print(translate_directory(sys.argv[1]))
#print(group(sys.argv[1]))