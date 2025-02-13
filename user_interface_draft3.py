import logging
import platform
import os
import time
import model_draft3 as model_draft 

# ---------- Error handling stuff ----------

# thanks stack exchange: https://stackoverflow.com/questions/3702675/catch-and-print-full-python-exception-traceback-without-halting-exiting-the-prog
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class End(Exception): # derived class to trigger program end
    '''custom exception class to end program'''
    # Constructor or Initializer
    def __init__(self):
        self.value = 'exiting'
 
class Restart(Exception): # derived class to trigger program restart
    '''custom class to restart program''' 
    # Constructor or Initializer
    def __init__(self):
        self.value = 'restarting'

# ---------- User Interface Helpers ----------
def clear_console():
    '''clears the console between messages displayed. Adding the colse outputs to a log file before clearing would be a cool addition...'''  
    if platform.system() == "Linux" or platform.system() == "Darwin":
        os.system("clear")
    elif platform.system() == "Windows":
        os.system("cls")
    else:
        print("NOTE: Cannot determine OS, outputs not cleared")

def ask(string, answers = None, dtype = 'string', table = False, ignore_case = True): 
    '''asks for user inputs and checks for valid answers and types
    
    Parameters
    ----------
    string : string
        prompt for user input
    answers : list 
        list of acceptable answers
    dtype : string
        required data type for user input
    table : bool (optional)
        flag to indicate if ask function is being called by the ask_table function
    ignore_case : bool (optional)
        flag to make answer checking case insensitive 
    
    Returns
    -------
    inp : string
        user input formatted as the datatype dtype
    '''  
    
    valid = False
    while not valid:
        
        inp = input(string)
        if ignore_case:
            inp = inp.lower()


        if inp == "restart":
            print("Restarting...")
            raise Restart
        elif inp == "exit":
            raise End
        
        else:
            try:
                if dtype == "float": 
                    inp = abs(float(inp))
                elif dtype == "integer":
                    inp = abs(int(inp))
                else:
                    inp = str(inp)
            except:
                print(f"Invalid response, must be data type {dtype}. Try again")
            else:

                if answers == None:
                    valid = True
                elif not (inp in answers):
                    print(f"Invalid response, must be one of: {answers}. Try again")
                else:
                    valid = True

    if not table:
        clear_console()

    return inp

def ask_table(headers, answers, types, rows, ignore_case = True):
    '''asks users to fill in a table
    
    Parameters
    ----------
    headers : list
        a list of headers for the table to display to the user
    answers : list
         a list of lists or Nones. The possible answers corresponding to each header. If no right answers, then None.
    types : list
        a list of data types (string, float, or integer) for each header category
    rows : int
        the number of rows
    ignore_case : bool (optional)
        flag to make answer checking case insensitive 
    
    Returns
    -------
    table : list
        a list of lists, where each sublist is the user inputs to a row of the table
    '''  

    print("Please fill in the following table:")

    if len(headers) != len(answers):
        raise ValueError("Length of headers needs to match length of answers")

    table = []
    for r in range(rows):
        table_i = []
        print(f"\n   Row {r+1}:")
        for i, header in enumerate(headers):
            inp = ask("      "+header+": ", answers[i], types[i], table = True, ignore_case = ignore_case)
            table_i.append(inp)
        table.append(table_i)

    clear_console()

    return table

# ------ User Interface DRAFT -----
if __name__ == "__main__":
    '''this is the main user interface to be replicated in SAM'''
    
    clear_console()
    end = False
    while not end:
        print("----------\nWelcome to the SAM user interface draft 3. \nThis built to work in command consoles.\nThis attempts to simulate the dropdown menu paths you can take with the proposed SAM user interface. \nOnce you fill out all the required information for a given path you will see the cost printed. \nYou can restart the script at any time by typing restart as an input. \nYou can end the script at any time by typing exit as an input.\n\nDISCLAIMER: This is a work in progress, and there are no checks to ensure inputs are realsitic for the described systems. \nAll negative numerical inputs are assumed positive via abs() \n\nEnjoy!\n----------")
        try:
            inputs = ask("Import WEC? (y/n) ", ["y","n"])
            if inputs == "y":
                inputs = ask("Foundation type (1: floating, 2: bottom fixed)? ", ["1", "2"])
                if inputs == "1":
                    
                    # running the model
                    model = model_draft.model()

                    # load in data from MoorPy structures (TODO: do we even want users to know this? Or should it just be always defaults)
                    inputs = ask("Use default mooring system properties? (y or <path to lineprops yaml>, <path to pointprops yaml>) ")
                    if inputs == "y": 
                        model.load_database()
                    elif (inputs != "y") and (", " not in inputs):
                        print(f"Invalid path provided: {inputs}. Restarting...")
                        raise Restart
                    else:
                        print(f"Using custom paths: {inputs}") # this wont work because we hard coded inputs already (like pointProps["general"])
                        path = str.split(inputs,", ")
                        if len(path) != 2:
                            print("Two paths must be provided. Restarting...")
                            raise Restart
                        model.load_database(path)

                    depth = abs(ask("Depth (m)? ", dtype = "float"))
                    # inflation scale disabled for now

                    inputs = ask("Include buoy costs? (y/n) ", ["y","n"])
                    buoys = [] # list of lists, one for each buoy type. Values are: "Num of these buoys", "buoyancy (m^3)"
                    if inputs == "y":
                        inputs2 = ask("How many different buoy sizes are in your design? (no buoys in design = 0) ", dtype="integer")
                        headers = ["Num of these buoys", "Buoyancy (kN)"]
                        answers = [None, None] # acceptable answers
                        types = ["integer","float"] # data types for each entry
                        buoys = ask_table(headers, answers, types, inputs2)

                    inputs = ask("Level of input (1: mooring library, 2: line data, 3: full mooring data)? ", ["1", "2", "3"])
                    if inputs == "1": # mooring library 
                        
                        # default is catenary
                        inputs1 = ask("Mooring configuration [default is catenary] (catenary, semi-taut, taut, tension)? ", ["catenary", "semi-taut", "taut", "tension"])
                        inputs2 = ask("Design load (kN)? ", dtype = "float")
                        # default is sand
                        inputs3 = ask("Soil type [default is sand] (soft clay, medium clay, hard clay, sand)? ", ["soft clay", "medium clay", "hard clay", "sand"])

                        model.set_paramsA1(shape = inputs1, depth = depth, design_load = inputs2, soil_type = inputs3, Buoy_Table = buoys)

                    elif inputs == "2": # line data 

                        inputs1 = ask("How many different line types are in your design? ", dtype="integer")
                        if inputs1 > 0:
                            headers = ["Num of these lines", "Line material (chain, polyester, nylon, wire, hmpe)", "Diameter (m)", "Factor of safety", "Length (m)", "Anchor load direction (none, horizontal, both, vertical)", "Number of anchors per line", "Num connections per line (ensure not double counting)"]
                            answers = [None, ["chain", "polyester", "nylon", "wire", "hmpe"], None, None, None, ["none", "horizontal", "both", "vertical"], None, None] # acceptable answers
                            types = ["integer","string","float","float","float","string","integer","integer"] # data types for each entry

                            lines = ask_table(headers, answers, types, inputs1)  # a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)", "Anchor load direction", "Number of anchors for line"

                            inputs2 = ask("Soil type (soft clay, medium clay, hard clay, sand)? ", ["soft clay", "medium clay", "hard clay", "sand"])

                            model.set_paramsA2(Line_Table = lines, depth = depth, soil_type = inputs2, Buoy_Table = buoys)
                        
                        else: 
                            print("1 or more lines required for the line data option. Restarting...")
                            raise Restart

                    elif inputs == "3": # full mooring data
                        inputs1 = ask("How many different line types are in your design? ", dtype="integer")
                        if inputs1 > 0:
                            headers = ["Num of these lines", "Line material (chain, polyester, nylon, wire, hmpe)", "Diameter (m)", "Factor of safety", "Length (m)", "Num connections (ensure not double counting)"]
                            answers = [None, ["chain", "polyester", "nylon", "wire", "hmpe"], None, None, None, None] # acceptable answers
                            types = ["integer","string","float","float","float","float"] # data types for each entry
                            lines = ask_table(headers, answers, types, inputs1) # a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)"
                        else: # if no lines just an empty list
                            lines = []

                        inputs2 = ask("How many different anchor types are in your design? ", dtype="integer")
                        if inputs2 > 0:
                            headers = ["Num of these anchors", "Anchor type (drag-embedment, gravity, VLA, SEPLA, suction, driven) [case sensitive]", "Mass (kg) [unused if VLA]", "Area (m^2) [only for VLA]", "Soil type (soft clay, medium clay, hard clay, sand)"] # soilType unused
                            answers = [None, ["drag-embedment", "gravity", "VLA", "SEPLA", "suction", "driven"], None, None, ["soft clay", "medium clay", "hard clay", "sand"]] # acceptable answers
                            types = ["integer","string","float","float","string"] # data types for each entry
                            anchors = ask_table(headers, answers, types, inputs2, ignore_case = False) # a list of lists, one for each anchor type in the system. Values are: "Num of these anchors", "Anchor type", "Mass (kg)", "Soil type"
                        else: # if no anchors just an empty list
                            anchors = []

                        model.set_paramsA3(Line_Table = lines, Anchor_Table = anchors, depth = depth, Buoy_Table = buoys) 

                    else:
                        print("Invalid input. Restarting...")
                        raise Restart

                    model.calc_cost()
                    print("INFO: connections are sized based on the MBL of the attached lines")

                else:
                    print("This model does not support fixed bottom. Restarting...")
                    raise Restart
                
            else:
                print("Reference model defaults not yet implemented. Restarting...")
                raise Restart
            
            inputs = ask("Start again? (y/n) ", ["y","n"])
            if inputs == "n":
                raise End

        except Restart:
            time.sleep(1)
            clear_console()
        except End:
            clear_console()
            end = True
        except Exception as e:
            logger.exception(e)
            print("--------------------\nA backend error has occured")
            inputs = ask("Start again? (y/n) ", ["y","n"])
            if inputs == "n":
                clear_console()
                end = True

    print("------------------------\nThanks for using draft 3! \n--------- END ----------")