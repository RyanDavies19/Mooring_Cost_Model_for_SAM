import model_draft2
import logging
import platform
import os
import time

# ---------- Error handling stuff ----------

# thanks stack exchange: https://stackoverflow.com/questions/3702675/catch-and-print-full-python-exception-traceback-without-halting-exiting-the-prog
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class End(Exception): # derived class to trigger program end
 
    # Constructor or Initializer
    def __init__(self):
        self.value = 'exiting'
 
class Restart(Exception): # derived class to trigger program restart
 
    # Constructor or Initializer
    def __init__(self):
        self.value = 'restarting'

# ---------- User Interface Helpers ----------

def clear_console():
    if platform.system() == "Linux" or platform.system() == "Darwin":
        os.system("clear")
    elif platform.system() == "Windows":
        os.system("cls")
    else:
        print("NOTE: Cannot determine OS, outputs not cleared")
    # pass

def ask(string, answers = None, dtype = 's', table = False): 
    """
    asks for user inputs and checks for valid answers and types
    """
    # if (input.lower() = "exit"):
    #   end = True
    #   break

    # if (input.lower() = "restart"):
    #   restart() 

    # ^^ how do we get these to do what I want them to? I.e. restart the deal, or exit the program
    
    valid = False
    while not valid:
        inp = input(string).lower()

        if inp == "restart":
            print("Restarting...")
            raise Restart
        elif inp == "exit":
            raise End
        
        else:
            try:
                if dtype == "float": 
                    inp = float(inp)
                elif dtype == "integer":
                    inp = int(inp)
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

def ask_table(headers, answers, types, rows):
    """
    asks users to fill in a table
    headers: a list of headers for the table 
    answers: a list of lists, the possible answers corresponding to each header. If no right answers, then None
    types: a list of data types (s, f, or i) for each header category
    rows: number of rows
    """

    print("Please fill in the following table:")

    if len(headers) != len(answers):
        raise ValueError("Length of headers needs to match length of answers")

    table = []
    for r in range(rows):
        table_i = []
        print(f"\n   Row {r+1}:")
        for i, header in enumerate(headers):
            inp = ask("      "+header+": ", answers[i], types[i], table = True)
            table_i.append(inp)
        table.append(table_i)

    clear_console()

    return table

# ------ User interface -----
if __name__ == "__main__":

    clear_console()
    end = False
    while not end:
        print("----------\nWelcome to the SAM user interface draft 2. \nThis built to work in command consoles.\nThis attempts to simulate the dropdown menu paths you can take with the proposed SAM user interface. \nOnce you fill out all the required information for a given path you will see the cost printed. \nYou can restart the script at any time by typing restart as an input. \nYou can end the script at any time by typing exit as an input. \nEnjoy!\n----------")
        try:
            inputs = ask("Import WEC? (y/n) ", ["y","n"])
            if inputs == "y":
                inputs = ask("Foundation type (1: floating, 2: bottom fixed)? ", ["1", "2"])
                if inputs == "1":
                    
                    # running the model
                    model = model_draft2.model()

                    depth = abs(ask("Depth (m)? ", dtype = "float"))
                    # inflation scale disabled for now

                    inputs = ask("Include buoy costs? (y/n) ", ["y","n"])
                    buoys = [] # list of lists, one for each buoy type. Values are: "Num of these buoys", "buoyancy (m^3)"
                    if inputs == "y":
                        inputs2 = ask("How many different buoy sizes are in your design? (no buoys in design = 0) ", dtype="integer")
                        headers = ["Num of these buoys", "Buoyancy (m^3)"]
                        answers = [None, None] # acceptable answers
                        types = ["integer","float"] # data types for each entry
                        buoys = ask_table(headers, answers, types, inputs2)

                    inputs = ask("Level of input (1: mooring library, 2: line data, 3: full mooring data)? ", ["1", "2", "3"])
                    if inputs == "1": # mooring library 

                        inputs1 = ask("Mooring configuration (catenary, semi-taut, taut, tension)? ", ["catenary", "semi-taut", "taut", "tension"])
                        inputs2 = ask("Design load (N)? ", dtype = "float") # TODO: check negatives
                        inputs3 = ask("Soil type (soft clay, medium clay, hard clay, sand)? ", ["soft clay", "medium clay", "hard clay", "sand"])

                        model.set_paramsA1(shape = inputs1, depth = depth, design_load = inputs2, soil_type = inputs3, Buoy_Table = buoys)

                    elif inputs == "2": # line data 

                        inputs1 = ask("How many different line types are in your design? ", dtype="integer")
                        headers = ["Num of these lines", "Line material (chain, polyester, nylon, wire, hmpe)", "Diameter (m)", "Length (m)", "Anchor load direction (none, horizontal, both, vertical)", "Number of anchors per line"]
                        answers = [None, ["chain", "polyester", "nylon", "wire", "hmpe"], None, None, ["none", "horizontal", "both", "vertical"], None] # acceptable answers
                        types = ["integer","string","float","float","string","integer"] # data types for each entry

                        lines = ask_table(headers, answers, types, inputs1)  # a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)", "Anchor load direction", "Number of anchors for line"

                        inputs2 = ask("Soil type (soft clay, medium clay, hard clay, sand)? ", ["soft clay", "medium clay", "hard clay", "sand"])

                        model.set_paramsA2(Line_Table = lines, soil_type = inputs2, depth = depth, Buoy_Table = buoys)

                    elif inputs == "3": # full mooring data
                        inputs1 = ask("How many different line types are in your design? ", dtype="integer")
                        headers = ["Num of these lines", "Line material (chain, polyester, nylon, wire, hmpe)", "Diameter (m)", "Length (m)"]
                        answers = [None, ["chain", "polyester", "nylon", "wire", "hmpe"], None, None] # acceptable answers
                        types = ["integer","string","float","float"] # data types for each entry
                        lines = ask_table(headers, answers, types, inputs1) # a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)"

                        inputs2 = ask("How many different anchor types are in your design? ", dtype="integer")
                        headers = ["Num of these anchors", "Anchor type (drag-embedment, congrav, steelgrav, VLA, SEPLA, suction)", "Mass (kg)", "Soil type (soft clay, medium clay, hard clay, sand)"]
                        answers = [None, ["drag-embedment", "congrav", "steelgrav", "VLA", "SEPLA", "suction"], None, ["soft clay", "medium clay", "hard clay", "sand"]] # acceptable answers
                        types = ["integer","string","float","string"] # data types for each entry
                        anchors = ask_table(headers, answers, types, inputs2) # a list of lists, one for each anchor type in the system. Values are: "Num of these anchors", "Anchor type", "Mass (kg)", "Soil type"

                        inputs3 = ask("Provide connection hardware total mass or enter -1 to estimate mass based on line MBL: ", dtype="float")
                        if inputs3 < 0:
                            inputs3 = None

                        model.set_paramsA3(Line_Table = lines, Anchor_Table = anchors, con_mass = inputs3, depth = depth, Buoy_Table = buoys) 

                    else:
                        print("Invalid input. Restarting...")
                        raise Restart

                    model.calc_cost()

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
            time.sleep(1.5)
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

    print("------------------------\nThanks for using draft 2! \n--------- END ----------")