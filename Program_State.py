"""
When parsing the tree, there are things that need to be kept in mind
1. The name of the current class scope.
2. The name of the current subroutine scope.
3. The Symbol Table (ST) which for a scope maps an identifier to a tuple containing (type, kind, count). Kind refers to either static vs field or local vs argument). 
4. The current max amount of the four types of variables.
5. For each subroutine, I want to keep track of the amount of while and if statements. It maps a function name (in the proper {class}.{subroutine}.{arguments} format to a tuple that is (amount_of_while_statements, amount_of_if_statements))
"""

CLASS_INDEX = 0
SUBROUTINE_INDEX = 1
WHILE_INDEX = 0
IF_INDEX = 1

class A_Program_State:
    def __init__(self, a_class_name):
        self.class_name = ""
        self.subroutine_name = ""
        self.ST = [{}, {}]
        self.var_counts = {"static": 0, "field": 0, "argument" : 0, "local" : 0}
        self.PT = {}
        
    def __repr__(self):
        print(f"Class: {self.class_name}, Subroutine: {self.subroutine_name}, ST: {self.ST}, Variables: {self.var_counts}")      
        
    def __str__(self):
        return f"Class: {self.class_name}, Subroutine: {self.subroutine_name}, ST: {self.ST}, Variables: {self.var_counts}"    
        
    def get_class_name(self):
        return self.class_name
    
    def get_subroutine_name(self):
        return self.subroutine_name
    
    def set_subroutine_name(self, foo):
        self.subroutine_name = foo
    
    def set_class_name(self, foo):
        self.class_name = foo
        
    def reset_Subroutine_ST(self):
        self.ST[SUBROUTINE_INDEX].clear()
        self.var_counts["argument"] = 0
        self.var_counts["local"] = 0
        
    def get_var_counts_for_a_type(self, type):
        return self.var_counts[type]
    
    def increment_var_counts_for_a_type(self, type):
        self.var_counts[type] += 1
    
    def add_to_class_ST(self, foo, type, kind):
        self.ST[CLASS_INDEX][foo] = (type, kind, self.var_counts[kind])
        self.var_counts[kind] += 1
    
    def add_to_subroutine_ST(self, foo, type, kind):
        self.ST[SUBROUTINE_INDEX][foo] = (type, kind, self.var_counts[kind])
        self.var_counts[kind] += 1
        
    def get_fuction_declaraction_name(self):
        return f"{self.class_name}.{self.subroutine_name}." + str(self.var_counts["argument"])
    
    
    def lookup_symbol(self, foo):
        # Check the subroutine-level symbol table first
        if foo in self.ST[SUBROUTINE_INDEX].keys():
            return self.ST[SUBROUTINE_INDEX].get(foo)
        
        # If not found, check the class-level symbol table
        if foo in self.ST[CLASS_INDEX]:
            return self.ST[CLASS_INDEX].get(foo)

        # Return None if the identifier is not found in any symbol table
        return None

    def handle_var_name(self, var_name : "str", push : bool):
        kind = ""
        count = 0
        if var_name in self.ST[SUBROUTINE_INDEX].keys():
            kind = self.ST[SUBROUTINE_INDEX].get(var_name)[1]
            count = self.ST[SUBROUTINE_INDEX].get(var_name)[2]
        else:
            kind = self.ST[CLASS_INDEX].get(var_name)[1]
            count = self.ST[CLASS_INDEX].get(var_name)[2]
            if kind == "field":
                kind = "this"
        return [("push" if push else "pop") + f" {kind} {count}"]
    
    def add_function_statement_counter(self):
        #print(self.get_fuction_declaraction_name())
        self.PT[self.get_fuction_declaraction_name()] = [0, 0]
    
    def get_statement_counter(self, statement_type):
        function_name = self.get_fuction_declaraction_name()
        if function_name in self.PT:
            index = WHILE_INDEX if statement_type == "while" else IF_INDEX
            #print(self.PT[function_name][index], function_name, statement_type)
            self.PT[function_name][index] += 1
            return self.PT[function_name][index]
        else:
            print(f"Error: Function '{function_name}' not found in PT.")

                
