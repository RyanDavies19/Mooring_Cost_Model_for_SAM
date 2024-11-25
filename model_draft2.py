import numpy as np
import moorpy as mp

# ---------- Header ----------
"""
This is a draft cost model structure intended to be integrated into tools like SAM and MoorPy. It has two main components: 
1. A section that estimates mooring parameters, led by the function set_paramsA#
2. A section that calculates costs based on the parameters 

TODO:
----
[X] find_diam
[X] choose_anchor
[-] choose_hardware - placeholder in there for now
[-] cost coefficients - lit review values as placeholder for now
[X] add semi-taut mooring configuration option
[X] allow for multiple lines, anchors, buoys, etc. This needs to be done before more front end work

"""
# # ---------- Helper Code ----------
# def suppressOutput(func): # from https://stackoverflow.com/questions/42952623/stop-python-module-from-printing
#     def wrapper(*args, **kwargs):
#         with open(os.devnull,"w") as devNull:
#             original = sys.stdout
#             sys.stdout = devNull
#             func(*args, **kwargs)
#             sys.stdout = original
#     return wrapper

# ---------- Cost Coefficients ----------

"""
Cost metrics data from a look-up. This ca be substituted with pulling from the MoorPy values (which will be the same).

This is all now set up under a 3rd order polynomial assumption, where the coefficient number correspond to the polynomial order. This can be changed!

WARNING: Right now these values are based on what was found in lit review, they can and should be updated before release becasue they are not accurate in the limits of large or small sizes. 
"""

# Lines - Note that $/(m^4) = $/m/(m^3)
class chain_coeff: # eventally break this into different grades of chain if sufficient data. 
    max = 0.3 # maximum diameter curve is valid (m)
    C0 = 0 # $/m
    C1 = 5535.3 # $/m/m
    C2 = 2770 # $/m/m/m
    C3 = 0 # $/m/m/m/m

class poly_coeff:
    max = 0.3 # maximum diameter curve is valid (m)
    C0 = 232.51 # $/m
    C1 = -1905.6 # $/m/m
    C2 = 10431 # $/m/m/m
    C3 = 0 # $/m/m/m/m

class nylon_coeff:
    max = 0.15 # maximum diameter curve is valid (m)
    C0 = 0 # $/m
    C1 = 929.55 # $/m/m
    C2 = 0 # $/m/m/m
    C3 = 0 # $/m/m/m/m

class wire_coeff:
    max = 0.1 # maximum diameter curve is valid (m)
    C0 = 0.1516 # $/m
    C1 = 932.95 # $/m/m
    C2 = 0 # $/m/m/m
    C3 = 0 # $/m/m/m/m

class hmpe_coeff:
    max = 0.3 # maximum diameter curve is valid (m)
    C0 = 0 # $/m
    C1 = 8332 # $/m/m
    C2 = 14083 # $/m/m/m
    C3 = 0 # $/m/m/m/m

line_coeff = {"chain":chain_coeff, "polyester":poly_coeff, "nylon":nylon_coeff, "wire":wire_coeff, "hmpe":hmpe_coeff}

# Anchors
class DEA_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = 0 # $
    C1 = 10.46 # $/kg
    C2 = 0 # $/kg/kg
    C3 = 0 # $/kg/kg/kg

class congrav_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = 0 # $
    C1 = 0.6273 # $/kg
    C2 = 0 # $/kg/kg
    C3 = 0 # $/kg/kg/kg

class steelgrav_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = 0 # $
    C1 = 0.6273 # $/kg
    C2 = 0 # $/kg/kg
    C3 = 0 # $/kg/kg/kg

class VLA_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = None # $
    C1 = None # $/kg
    C2 = None # $/kg/kg
    C3 = None # $/kg/kg/kg

class SEPLA_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = None # $
    C1 = None # $/kg
    C2 = None # $/kg/kg
    C3 = None # $/kg/kg/kg

class suction_coeff:
    max = None # maximum mass curve is valid (kg)
    C0 = None # $
    C1 = None # $/kg
    C2 = None # $/kg/kg
    C3 = None # $/kg/kg/kg

anchor_coeff = {"drag-embedment":DEA_coeff, "congrav":congrav_coeff, "steelgrav":steelgrav_coeff, "VLA":VLA_coeff, "SEPLA":SEPLA_coeff, "suction":suction_coeff}

# Other
class con_coeff:
    max = None# maximum mass curve is valid (kg)
    C0 = 0 # $
    C1 = 0 # $/kg
    C2 = 0.0021 # $/kg/kg
    C3 = 0 # $/kg/kg/kg

class buoy_coeff:
    max = None # maximum volume curve is valid (m^3)
    C0 = 2702.7 # $
    C1 = 3062.1 # $/m^3
    C2 = 0 # $/m^3/m^3
    C3 = 0 # $/m^3/m^3/m^3


# ---------- Assumption Functions (MoorProps) ----------
# These are one place FAD tools could be coupled in, hardcorded the MoorProps values for the time being

def calc_diam(mbl = 0.0, mbl_d = 0.0, mbl_d2 = 0.0, mbl_d3 = 0.0, curve_max = 0.2):

    """
    This computes the diameter value in a given range (0 - curve_max) that give the corresponding mbl from a 
    third order polynomial with the coefficients mbl_d, mbl_d2, mbl_d3. 
    """

    roots = np.roots([mbl_d3, mbl_d2, mbl_d, -mbl])
    
    success = False
    diam = []
    for root in roots:
        if (root > 0) and (root < curve_max):
            diam.append(root)
            success = True

    if not success: 
        raise Exception(f"Diameters not found in MBL for range 0 - {curve_max} m")
    elif len(diam) > 1: # this should never happen becasue curves are all strictly increasing on the range 0 - curve_max, but good to check regardless
        print(f"WARNING: Multiple diameters found to produce MBL of {mbl} N. Diameter set to smallest, {diam[0]} m")
    return diam[0]

def find_diam(load,l_type):
    """
    This computes the diameter that is sufficient for a design load for different line types.
    """

    if l_type == "chain":
        line_diam = calc_diam(mbl = load, mbl_d = 9.11*10**2, mbl_d2 = 1.21*10**9, mbl_d3= -2.19*10**9, curve_max = 0.2) # coefficients from the moorprops report, with curve max being the upper bound where the curve fit is considered accurate
    elif l_type == "polyester":
        line_diam = calc_diam(mbl = load, mbl_d2 = 308*10**6, curve_max = 0.275) # coefficients from the moorprops report, with curve max being the upper bound where the curve fit is considered accurate
    elif l_type == "nylon":
        line_diam = calc_diam(mbl = load, mbl_d2 = 207*10**6, mbl_d3= 230*10**6, curve_max = 0.3) # coefficients from the moorprops report, with curve max being the upper bound where the curve fit is considered accurate
    elif l_type == "wire":
        line_diam = calc_diam(mbl = load, mbl_d2 = 1022*10**6, curve_max = 0.175) # coefficients from the moorprops report, with curve max being the upper bound where the curve fit is considered accurate
    elif l_type == "hmpe":
        line_diam = calc_diam(mbl = load, mbl_d2 = 580*10**6, mbl_d3 = 651*10**6, curve_max = 0.175) # coefficients from the moorprops report, with curve max being the upper bound where the curve fit is considered accurate
    else:
        raise Exception(f"Line type '{l_type}' does not exist.")

    print(f"INFO: Line type '{l_type}' diameter set to {line_diam:.3f} m corresponding to MBL of {load:.3f} N")

    return line_diam

def find_MBL(diam, l_type):
    """
    This computes the MBL from line diameter for different line types and checks the diameters are valid for the curves.
    """

    if l_type == "chain":
        if diam > 0.2:
            raise Exception("Chain MBL (design load) curve not valid above 200mm diameter")
        MBL = 9.11*10**2 * diam + 1.21*10**9 * diam**2 - 2.19*10**9 * diam**3 # coefficients from the moorprops report
    elif l_type == "polyester":
        if diam > 0.275:
            raise Exception("Polyester MBL (design load) curve not valid above 275mm diameter")
        MBL = 308*10**6 * diam**2 # coefficients from the moorprops report
    elif l_type == "nylon":
        if diam > 0.3:
            raise Exception("Nylon MBL (design load) curve not valid above 300mm diameter")
        MBL = 207*10**6 * diam**2 + 230*10**6 * diam**3 # coefficients from the moorprops report
    elif l_type == "wire":
        if diam > 0.175:
            raise Exception("Wire MBL (design load) curve not valid above 175mm diameter")
        MBL = 1022*10**6 * diam**2 # coefficients from the moorprops report
    elif l_type == "hmpe":
        if diam > 0.175:
            raise Exception("HMPE MBL (design load) curve not valid above 175mm diameter")
        MBL = 580*10**6 * diam**2 + 651*10**6 * diam**3 # coefficients from the moorprops report
    else:
        raise Exception(f"Line type '{l_type}' does not exist.")

    print(f"INFO: Design load set to {MBL:.3f} N corresponding line type '{l_type}' with a diameter of {diam:.3f} m")

    return MBL

def choose_anchor(load, load_dir, a_type, soil_type):

    """
    This uses moorpy to calculate the anchor size needed for a design load and mooring shape.
    Soil type checking is handled inside of MoorPy
    """

    g = 9.81 # gravity

    if load_dir == "horizontal":
        loadx = load
        loadz = 0.0

        if a_type == None:
            a_type = "drag-embedment"
            print(f"INFO: Anchor type set to '{a_type}'")

    elif load_dir == "both":   # 45 deg hang off angle, forces split 50/50
        loadx = np.sqrt(2*load**2)
        loadz = loadx
        if a_type == "drag-embedment":
            print("WARNING: drag embedment anchors should not be used with taut moorings")

        if a_type == None:
            a_type = "congrav"
            print(f"INFO: Anchor type set to '{a_type}'")

    elif load_dir == "vertical":
        loadx = 0.0
        loadz = load
        if a_type == "drag-embedment":
            print("WARNING: drag embedment anchors should not be used with tension moorings")

        if a_type == None:
            a_type = "congrav"
            print(f"INFO: Anchor type set to '{a_type}'")
    else:
        print("WARNING: load direction not recognized, assuming no vertical loading and drag anchor")
        a_type = "drag-embedment"
        loadx = load
        loadz = 0.0

    if a_type == "drag-embedment" or (a_type == "VLA") or (a_type == "SEPLA") or (a_type == "suction"):

        outputs = mp.getAnchorMass(uhc_mode=False, fx = loadx, fz = loadz, anchor = a_type, soil_type = soil_type)
        if outputs == Exception:
            raise outputs

        mass = outputs[2]["Mass"]

    elif (a_type == "congrav") or (a_type == "steelgrav"):
        mass = max(2 * loadz / g, 1.65 * loadx / g) # 2x safety factor for vertial 1.6x for horizontal per API standards. Use the larger value
    else:
        raise Exception(f"Anchor type '{a_type}' does not exist")

    print(f"INFO: '{a_type}' anchor mass set to {mass:.3f} kg for load direction '{load_dir}' and soil type '{soil_type}'" )

    return mass, a_type


def choose_hardware(load):
    """
    This finds the total connection hardware mass sufficient for the design load
    """

    # some curve relating line MBL to connection hardware mass
    A = 0
    B = 10**-5 # rough guess based on TidGen chain MBL and connection hardware mass
    mass = A + B * load #  maybe its linear?

    print(f"INFO: {mass:.3f} kg of connection hardware calculated for design load of {load:.3f} N")

    return mass


# ---------- Model backend ----------
# These cost functions are just third order polynomials of the cost coefficients with error checking to ensure costs are within model range. Costs returned in 2024$

def line_cost_func(material, diam, length):

    if not material in line_coeff.keys():
        raise Exception(f"Line type {material} does not exist.")
    elif (line_coeff[material].C0 == None) or (line_coeff[material].C1 == None) or (line_coeff[material].C2 == None) or (line_coeff[material].C3 == None):
        raise Exception(f"Cost coefficients for {material} do not exist yet.")
    elif (line_coeff[material].max != None):
        if (diam > line_coeff[material].max):
            raise Exception(f"Cost curve for {material} not valid above diameter of {line_coeff[material].max} m.")
    
    # store the line data as a dictionary by line type where each value is a class containing the four coefficients
    cost_per_m = line_coeff[material].C0 + (line_coeff[material].C1 * diam) + (line_coeff[material].C2 * diam**2) + (line_coeff[material].C3 * diam**3) # third order fit for now, adjust this once data is given by manufacturers 
    return length * cost_per_m

def anchor_cost_func(a_type, mass):

    if not a_type in anchor_coeff.keys():
        raise Exception(f"Anchor type {a_type} does not exist")
    elif (anchor_coeff[a_type].C0 == None) or (anchor_coeff[a_type].C1 == None) or (anchor_coeff[a_type].C2 == None) or (anchor_coeff[a_type].C3 == None):
        raise Exception(f"Cost coefficients for {a_type} anchors do not exist yet.")
    elif (anchor_coeff[a_type].max != None):
        if (mass > anchor_coeff[a_type].max):
            raise Exception(f"Cost curve for {a_type} not valid above mass of {anchor_coeff[a_type].max} kg.")

    return anchor_coeff[a_type].C0 + (anchor_coeff[a_type].C1 * mass) + (anchor_coeff[a_type].C2 * mass**2) + (anchor_coeff[a_type].C3 * mass**3)
    
def connection_cost_func(mass):
    if (con_coeff.C0 == None) or (con_coeff.C1 == None) or (con_coeff.C2 == None) or (con_coeff.C3 == None): # should never be triggered unless someone removes coefficients
        raise Exception(f"Cost coefficients for connection hardware do not exist yet.")
    elif (con_coeff.max != None):
        if (mass > con_coeff.max):
            raise Exception(f"Cost curve for connection hardware not valid above mass of {con_coeff.max} kg.")

    return con_coeff.C0 + (con_coeff.C1 * mass) + (con_coeff.C2 * mass**2) + (con_coeff.C3 * mass**3)

def buoy_cost_func(buoyancy):
    if (buoy_coeff.C0 == None) or (buoy_coeff.C1 == None) or (buoy_coeff.C2 == None) or (buoy_coeff.C3 == None): # should never be triggered unless someone removes coefficients
        raise Exception(f"Cost coefficients for buoys do not exist yet.")
    elif (buoy_coeff.max != None):
        if (buoyancy > buoy_coeff.max):
            raise Exception(f"Cost curve for buoys not valid above buoyancy of {buoy_coeff.max} m^3.")

    return buoy_coeff.C0 + (buoy_coeff.C1 * buoyancy) + (buoy_coeff.C2 * buoyancy**2) + (buoy_coeff.C3 * buoyancy**3)

# User interface class and functions
class model():
    """
    line_length, line type, mooring design_load, depth, diameter
    anchor_type, soil type, required size

    For SAM we will need to make an additional input section similar to cable specifications on the array page.

    Three levels of assumptions: where the level of user inputs determine the ammount of assumptions. Could this be 
    correlated to an accuracy number reported back (to tell them the more components you add the more accurate this 
    will be)?

    There are three levels of input that a user can provide: 
    1)	Assumption Level 1: Current SAM inputs plus design_load
        a.	Users give general mooring system properties: depth,mooring configuration, design_load, seabed type
        b.	anchor_types and sizes, line_lengths and diameters and materials, and con_mass assumed.
    2)	Assumption level 2: Current MoorPy inputs + seabed type 
        a.	Users give line_lengths, types, sizes, depth, anchor load direction, seabed type
        b.	anchor_types and sizes, con_mass assumed
    3)	Assumption level 3: Current FAD inputs + connection mass + buoys
        a.	User provides line_diam, length, and material
        b.	User provides anchor_type and mass
        c.	User provides con_mass mass or an estimate is made based on line MBL

    For buoyancy, this will be a parameter that has to be entered by the users at any level of assumption. Because it is 
    not super common for basic mooring designs, it doesn’t need to be included in the higher-level estimates. The user will 
    be required to input the number of buoys of a certain size (as total buoyancy wouldn’t accurately capture the cost 
    differences between different sized buoys). 

    Units:
    ------
    depth: m
    design_load: N
    line_diam: m
    P: N/m
    line_length: m
    anchor_mass: kg
    con_mass: kg
    buoyancy: m^3

    Types of Lines (case sensitvie):
    --------------
    chain
    polyester
    nylon
    wire 
    hmpe

    Types of Anchors (case sensitive):
    ----------------
    drag-embedment <-- drag embedment
    congrav <-- concrete gravity
    steelgrav <-- steel gravity
    VLA <-- Vertical Load
    SEPLA <-- Suction plate embedment
    suction <-- suction pile

    Types of soil (case sensitive):
    -------------------------------
    soft clay
    medium clay
    hard clay
    sand

    Mooring Shapes (case sensitive):
    --------------------------------
    catenary
    semi-taut
    taut
    tension

    Anchor load directions (case sensitive):
    --------------------------------
    none
    horizontal
    both
    vertical

    """

    def __init__(self):
        # structures for tables
        self.line_type = {"id" : None, "num" : None, "material" : None, "diam" : None, "length" : None, "shape" : None, "design_load" : None, "nAnch" : None, "aLoadDir" : None}
        self.anchor_type = {"id" : None, "num" : None, "kind" : None, "mass" : None, "soil_type" : None}
        self.buoy_type = {"id" : None, "num" : None, "buoyancy" : None}

    def set_nLineTypes(self, n):
        self.nLineTypes = n
        self.LineTypes = []
        for i in range(n):
            self.LineTypes.append(self.line_type.copy())

    def set_nAnchTypes(self, n):
        self.nAnchTypes = n
        self.AnchTypes = []
        for i in range(n):
            self.AnchTypes.append(self.anchor_type.copy())

    def set_nBuoyTypes(self, n):
        self.nBuoyTypes = n
        self.BuoyTypes = []
        for i in range(n):
            self.BuoyTypes.append(self.buoy_type.copy())

    def set_paramsA0(self):

        print("Using default parameters (catenary shape)")

        # system values
        self.depth = 200 # m
        soil_type = "soft clay"
        design_load = 10000 * 10**3 # N
        
        # inflation adjustment from 2024$
        self.inflation_scale = 1.0 # optional

        # Line values (for each type)
        self.set_nLineTypes(1)
        self.LineTypes[0]["design_load"] = design_load
        self.LineTypes[0]["num"] = 3
        self.LineTypes[0]["material"] = "chain"
        self.LineTypes[0]["diam"] = find_diam(self.LineTypes[0]["design_load"], self.LineTypes[0]["material"])
        P = ((21.9*10**3 * self.LineTypes[0]["diam"] ** 2) - (np.pi/4)*(1.89*self.LineTypes[0]["diam"])**2 * 1025) * 9.81 # Wet weight per meter (N/m). MoorProps for R4 sudlink chain
        self.LineTypes[0]["length"] = 15 + self.depth * np.sqrt(2*(self.LineTypes[0]["design_load"]/(P*self.depth))-1) # where P is the wet weight per meter. Assuming 15m on seabed. Eqn 5.15 from https://www.sciencedirect.com/book/9780128185513/mooring-system-engineering-for-offshore-structures
        self.LineTypes[0]["design_load"] = design_load
        self.LineTypes[0]["nAnch"] = 3
        self.LineTypes[0]["aLoadDir"] = 'horizontal'

        # Connection values
        self.con_mass = choose_hardware(self.LineTypes[0]["design_load"])
        
        # Anchor values (for each type)
        self.set_nAnchTypes(1)
        self.AnchTypes[0]["num"] = self.LineTypes[0]["nAnch"]
        self.AnchTypes[0]["kind"] = None # assigned by the anchor tool according to the shape
        self.AnchTypes[0]["soil_type"] = soil_type
        self.AnchTypes[0]["mass"], self.AnchTypes[0]["kind"] = choose_anchor(self.LineTypes[0]["design_load"], self.LineTypes[0]["aLoadDir"], self.AnchTypes[0]["kind"], self.AnchTypes[0]["soil_type"])

        # buoy values (optional)
        self.set_nBuoyTypes(0)

    def set_paramsA1(self, shape = None, depth = None, soil_type = None, design_load = None, Buoy_Table = [], inflation_scale = 1):

        print("Using SAM level user provided parameters")

        # system values
        self.depth = depth
        
        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # Line values (based on shape, depth, and design load)
        if shape == "catenary":
            self.set_nLineTypes(1)
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["num"] = 3
            self.LineTypes[0]["material"] = "chain"
            self.LineTypes[0]["diam"] = find_diam(self.LineTypes[0]["design_load"], self.LineTypes[0]["material"])
            P = ((21.9*10**3 * self.LineTypes[0]["diam"] ** 2) - (np.pi/4)*(1.89*self.LineTypes[0]["diam"])**2 * 1025) * 9.81 # Wet weight per meter (N/m). MoorProps for R4 sudlink chain
            self.LineTypes[0]["length"] = 15 + self.depth * np.sqrt(2*(self.LineTypes[0]["design_load"]/(P*self.depth))-1) # where P is the wet weight per meter. Assuming 15m on seabed. Eqn 5.15 from https://www.sciencedirect.com/book/9780128185513/mooring-system-engineering-for-offshore-structures
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'horizontal'
        elif shape == "semi-taut":
            self.set_nLineTypes(2)
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[1]["design_load"] = design_load
            self.LineTypes[0]["num"] = 3
            self.LineTypes[1]["num"] = 3
            self.LineTypes[0]["material"] = "polyester"
            self.LineTypes[1]["material"] = "chain"
            self.LineTypes[0]["diam"] = find_diam(self.LineTypes[0]["design_load"], self.LineTypes[0]["material"])
            self.LineTypes[1]["diam"] = find_diam(self.LineTypes[1]["design_load"], self.LineTypes[1]["material"])
            self.LineTypes[0]["length"] = np.sqrt(2* self.depth**2) # Assuming 45 deg hang off, straight to seabed
            self.LineTypes[1]["length"] = 15 # assuming 15m of chain on the seabed
            self.LineTypes[0]["nAnch"] = 0
            self.LineTypes[1]["nAnch"] = 1
            self.LineTypes[1]["aLoadDir"] = 'none'
            self.LineTypes[1]["aLoadDir"] = 'horizontal'
        elif shape == "taut":
            self.set_nLineTypes(1)
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["num"] = 3
            self.LineTypes[0]["material"] = "polyester"
            self.LineTypes[0]["diam"] = find_diam(self.LineTypes[0]["design_load"], self.LineTypes[0]["material"])
            self.LineTypes[0]["length"] = np.sqrt(2* self.depth**2) # Assuming 45 deg hang off
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'both'
        elif shape == "tension":
            self.set_nLineTypes(1)
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["num"] = 8
            self.LineTypes[0]["material"] = "hmpe"
            self.LineTypes[0]["diam"] = find_diam(self.LineTypes[0]["design_load"], self.LineTypes[0]["material"])
            self.LineTypes[0]["length"] = self.depth
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'vertical'
        else:
            raise Exception(f"Line shape {self.shape} is not supported")

        # Anchor Values
        self.set_nAnchTypes(0)
        self.con_mass = 0
        for i in range(self.nLineTypes):
            if self.LineTypes[i]["nAnch"] > 0: # while this may lead to duplicative anchor types, it keeps the code functioning. Assuming a unique anchor type for each line type with attached anchors
                if self.LineTypes[i]["aLoadDir"] == "none":
                    raise Exception(f"Anchor direction cannot be 'none' if nAnch is greater than zero (line {self.LineTypes[i]['id']+1})")
                self.AnchTypes.append(self.anchor_type.copy())
                self.nAnchTypes += 1

                self.AnchTypes[-1]["kind"] = None # assigned by the anchor tool according to the shape
                self.AnchTypes[-1]["soil_type"] = soil_type
                self.AnchTypes[-1]["mass"], self.AnchTypes[-1]["kind"] = choose_anchor(self.LineTypes[i]["design_load"], self.LineTypes[i]["aLoadDir"], self.AnchTypes[-1]["kind"], self.AnchTypes[-1]["soil_type"])
                self.AnchTypes[-1]["num"] = self.LineTypes[i]["nAnch"] * self.LineTypes[i]["num"]
        
            # Connection values
            self.con_mass += choose_hardware(self.LineTypes[i]["design_load"])        # buoy values (optional)

        # Buoy values
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"]= buoy[1] # m^3

    def set_paramsA2(self, Line_Table = None, soil_type = None, depth = None, Buoy_Table = [], inflation_scale = 1):
        """
        Line_Table: a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)", "Load Direction", "Number of anchors for line"
        """

        print(f"Using MoorPy level parameters. {len(Line_Table)} different line types")

        # system values
        self.depth = depth # unused. TODO: Do we get rid of it? Or add a check that intput line lengths are sufficient for depth?
        
        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # Line values
        self.set_nLineTypes(len(Line_Table))

        for i,line in enumerate(Line_Table):
            self.LineTypes[i]["id"] = i
            self.LineTypes[i]["num"] = line[0]
            self.LineTypes[i]["material"] = line[1]
            self.LineTypes[i]["diam"] = line[2]
            self.LineTypes[i]["length"] = line[3]
            self.LineTypes[i]["aLoadDir"] = line[4]
            self.LineTypes[i]["design_load"] = find_MBL(line[2], line[1]) # calc from line diam and material
            self.LineTypes[i]["nAnch"] = line[5]

        # Anchor values 
        self.set_nAnchTypes(0)
        self.con_mass = 0
        for i in range(len(Line_Table)):
            if self.LineTypes[i]["nAnch"] > 0: # while this may lead to duplicative anchor types, it keeps the code functioning. Assuming a unique anchor type for each line type with attached anchors
                if self.LineTypes[i]["aLoadDir"] == "none":
                    raise Exception(f"Anchor direction cannot be 'none' if nAnch is greater than zero (line {self.LineTypes[i]['id']+1})")
                self.AnchTypes.append(self.anchor_type.copy())
                self.nAnchTypes += 1

                self.AnchTypes[-1]["kind"] = None # assigned by the anchor tool according to the shape
                self.AnchTypes[-1]["soil_type"] = soil_type
                self.AnchTypes[-1]["mass"], self.AnchTypes[-1]["kind"] = choose_anchor(self.LineTypes[i]["design_load"], self.LineTypes[i]["aLoadDir"], self.AnchTypes[-1]["kind"], self.AnchTypes[-1]["soil_type"])
                self.AnchTypes[-1]["num"] = self.LineTypes[i]["nAnch"] * self.LineTypes[i]["num"]
        
            # Connection values
            self.con_mass += choose_hardware(self.LineTypes[i]["design_load"])

        # buoy values (optional)
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"]= buoy[1] # m^3

    def set_paramsA3(self, Line_Table = None, Anchor_Table = None, con_mass = None, depth = None, Buoy_Table = [], inflation_scale = 1):
        
        """
        Line_Table: a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter (m)", "Length (m)"
        
        Anchor_Table: a list of lists, one for each anchor type in the system. Values are: anchor type num, anchor type, anchor mass, soil type
        """

        print("Using FAD level user provided parameters")

        # system values
        self.depth = depth

        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # Line and connection values
        self.set_nLineTypes(len(Line_Table))
        self.con_mass = 0
        for i,line in enumerate(Line_Table):
            self.LineTypes[i]["id"] = i
            self.LineTypes[i]["num"] = line[0]
            self.LineTypes[i]["material"] = line[1]
            self.LineTypes[i]["diam"] = line[2]
            self.LineTypes[i]["length"] = line[3]
            self.LineTypes[i]["design_load"] = find_MBL(line[2], line[1]) # calc from line diam

            # Connection values
            self.con_mass += choose_hardware(self.LineTypes[i]["design_load"]) # calculated based on line variable, overwritten if provided
        
        self.set_nAnchTypes(len(Anchor_Table))
        for i, anchor in enumerate(Anchor_Table):
            self.AnchTypes[i]["id"] = i
            self.AnchTypes[i]["num"] = anchor[0]
            self.AnchTypes[i]["kind"] = anchor[1]
            self.AnchTypes[i]["mass"] = anchor[2]
            self.AnchTypes[i]["soil_type"] = anchor[3]
        
        if con_mass != None:
            self.con_mass = con_mass # overwrite if provided

        # buoy values (optional)
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"]= buoy[1] # m^3

    # ---------- Outputs ----------
    """
    Fo SAM: we want outputs to be Mooring Lines, Anchors, Connecting Hardware, and Bouys
    For MoorPy / LineDesign: we want outputs to be total mooring cost, Mooring Lines, Anchors, Connecting Hardware, and Bouys
    """

    def calc_cost(self):

        Line_cost = 0
        for lType in self.LineTypes:
            Line_cost += self.inflation_scale * (lType["num"] *  line_cost_func(lType["material"], lType["diam"], lType["length"]))
        Anchor_cost = 0
        for aType in self.AnchTypes:
            Anchor_cost += self.inflation_scale * (aType["num"] * anchor_cost_func(aType["kind"], aType["mass"]))
        
        Connection_cost = self.inflation_scale * connection_cost_func(self.con_mass)

        Buoy_cost = 0
        for bType in self.BuoyTypes:
            Buoy_cost += self.inflation_scale * (bType["num"] * buoy_cost_func(bType["buoyancy"]))

        Total_cost = Line_cost + Anchor_cost + Connection_cost + Buoy_cost

        print("--------- Cost Report (2024$) ---------")
        print(f"System Parameters")
        print(f"    Water Depth: {self.depth:.3f} m")
        print(f"Line Parameters")
        for lType in self.LineTypes:
            print(f"    Material   : {lType['material']}")
            print(f"    Number     : {lType['num']}")
            print(f"    Length     : {lType['length']:.3f} m")
            print(f"    Diameter   : {lType['diam']:.3f} m")
            print(f"    Design Load: {lType['design_load']:.3f} N")
        print(f"Anchor Parameters")
        for aType in self.AnchTypes:
            print(f"    Type       : {aType['kind']}")
            print(f"    Number     : {aType['num']}")
            print(f"    Mass       : {aType['mass']:.3f} kg")
            print(f"    Soil type  : {aType['soil_type']}")
        print(f"Connection Hardware Parameters")
        print(f"    Mass       : {self.con_mass:.3f} kg")
        print(f"Buoyancy Module Parameters")
        for bType in self.BuoyTypes:
            print(f"    Num Buoys  : {bType['num']}")
            print(f"    Buoyancy   : {bType['buoyancy']:.3f} m^3")
        print(f"--------------------------------------")
        print(f"Anchor cost     : $ {Anchor_cost:.2f}")
        print(f"Line cost       : $ {Line_cost:.2f}")
        print(f"Buoy cost       : $ {Buoy_cost:.2f}")
        print(f"Connection cost : $ {Connection_cost:.2f}")
        print(f"Total cost      : $ {Total_cost:.2f}")
        print("---------------------------------------")

if __name__ == "__main__":
    tool = model()
    # lines = [[1, "chain", 0.2, 100, "horizontal", 1]]
    # tool.set_paramsA2(Line_Table = lines, soil_type = "sand", depth = 100)

    # tool.set_paramsA1(shape = "taut", depth = 100, design_load = 100000, soil_type = "soft clay")

    tool.set_paramsA2(Line_Table = [[3,"polyester",.2,50,"none",0],[3,"chain",.1,20,"horizontal",1]],depth = 100, soil_type = "soft clay")
    tool.calc_cost()