import numpy as np
import moorpy as mp
import moorpy.helpers as helpers

# ---------- Header ----------
"""
This is a draft cost model structure intended to be integrated into tools like SAM and MoorPy. It has two main components: 
1. A class that estimates mooring designs and loads data from MoorPy, called by the function set_paramsA# (in C++ this would be a private class)
2. A class that contains the user interface functions

TODO:
----
[X] find_diam
[X] getAnchor
[X] choose_hardware - placeholder in there for now
[X] cost coefficients - lit review values as placeholder for now
[X] add semi-taut mooring configuration option
[X] allow for multiple lines, anchors, buoys, etc. This needs to be done before more front end work
[X] remove hardcoded coefficients and add in MoorPy dependency
[ ] check entire dependency on custom MoorPy yamls. (i.e. chain, hmpe, etc. not in here at all expect for default params). Eventually same for points 

"""

class backend():
    '''This backend class handles the interface between the model and MoorPy, which holds the sizing tools and the 
    datasets w/ associated structures to define a mooring system. MoorPy is also responsible for calculating the 
    costs that are produced by this model.
    '''

    def __init__(self):
        '''initializes the class'''        
        pass

    # load in MoorPy data from YAMLs
    def load(self, path = None):
        '''Loads the line and point props dictionaries using the respective MoorPy.helpers methods
        
        Parameters
        ----------
        path : list of strings
            A list of two strings holding the paths to the LineProps and PointProps yamls respectively.
        '''
        
        if path == None:
            self.lineProps = helpers.loadLineProps(path)
            self.pointProps = helpers.loadPointProps(path)
        else:
            self.lineProps = helpers.loadLineProps(path[0])
            self.pointProps = helpers.loadPointProps(path[1])  

    ### Line Stuff
    def calc_diam(self, mbl = 0.0, mbl_0 = 0.0, mbl_d = 0.0, mbl_d2 = 0.0, mbl_d3 = 0.0, curve_min = -1, curve_max = -1):
        '''Given a target MBL value, the values of the 3rd order polynomial MBL curve, 
        and curve limits this calcualtes the diameter of a line with the target MBL.
        It finds the roots of the function y = a + bx + cx^2 + dx^3 (0 = (a-y) + bx + cx^2 + dx^3)
        that are within the provided curve limits. If multiple matching values are found, 
        the smallest value greater than zero is selected. 
        
        Parameters
        ----------
        mbl : float
            target MBL [N]
        mbl_0 : float
            minimum breaking load offset [N]
        mbl_d : float
            minimum breaking load per diameter [N/m]
        mbl_d2 : float
            minimum breaking load per diameter^2 [N/m^2]
        mbl_d3 : float
            minimum breaking load per diameter^3 [N/m^3]
        curve_min : float
            minimum valid diameter for the MBL curve (values < 0 ignored) [m]
        curve_max : float
            maximum valid diameter for the MBL curve (values < 0 ignored) [m]
        
        Returns
        -------
        float
            The smallest diameter greater than zero that provides the target MBL
        '''

        roots = np.roots([mbl_d3, mbl_d2, mbl_d, mbl_0-mbl])
        
        success = False
        diam = []
        for root in roots:
            if curve_max >= 0 and curve_min >= 0: # if min and max values given and the diameter in the range
                if root >= curve_min and root <= curve_max:
                    diam.append(root)
                    success = True

            elif curve_max >= 0 and root <= curve_max : # if a max value is given and the diameter is less than the max
                diam.append(root)
                success = True
            
            elif curve_min >= 0 and root >= curve_min : # if a min value is given and the diameter is more than the min
                diam.append(root)
                success = True
            
            elif root >= 0: # no max or min value is given, just check if the root is > 0
                diam.append(root)
                success = True

        if not success: 
            raise Exception(f"Diameters not found in MBL for range {curve_min} - {curve_max} m")
        elif len(diam) > 1: # this should never happen becasue curves are all strictly increasing on the range 0 - curve_max, but good to check regardless
            print(f"WARNING: Multiple diameters found to produce MBL of {mbl} N. Diameter set to smallest, {min(diam):.3f} m")
        return min(diam)

    def find_diam(self, load, material, fos = 1):
        '''Given a line material and design load return the line diameter that
        provides the design load. This serves to wrap the calc_diam function and
        pass the values in self.lineProps for the respective material. 
        
        Parameters
        ----------
        load : float
            the design load [N]
        material : string
            the line type material keyword. Options are: chain, polyester, nylon, wire, hmpe
        fos : float
            factor of safety to convert from design load to line MBL
        
        Returns
        -------
        line_diam : float
            the diameter of the line that meets the design load [m]
        '''
        
        mat = self.lineProps[material]       # shorthand for the sub-dictionary of properties for the material in question 
        
        line_diam = self.calc_diam(mbl = load * fos, mbl_0 = mat['MBL_0'], mbl_d = mat['MBL_d'], mbl_d2 = mat['MBL_d2'], mbl_d3 = mat['MBL_d3'], curve_min = mat['MBL_dmin'], curve_max = mat['MBL_dmax'])

        print(f"INFO: Line type '{material}' diameter set to {line_diam:.3f} m corresponding to MBL of {load:.3f} N")

        return line_diam

    def getLine(self, design_load = None, material = None, diam = None, fos = None):
        '''calculate the diameter to get the line data structure from MoorPy.helpers
        and checks for valid inputs.
        
        Parameters
        ----------
        design_load : float
            the design load for the line [N]
        material : string
            the line type material keyword. Options are: chain, polyester, nylon, wire, hmpe
        diam : float
            the diameter of the line [m]
        fos : float
            factor of safety to convert from design load to line MBL
            
        Returns
        -------
        dictionary
            A lineType dictionary
        '''
        dLoad = design_load

        if material == None:
            raise Exception("Material not provided")

        if dLoad == None and diam == None:
            raise Exception("Either design load or diameter is needed to load moorpy data")
        elif dLoad != None and diam != None:
            print("WARNING: Both design load and diameter provided to getLine. input diameter will be used.")
            dLoad = None

        if dLoad != None:
            if dLoad >= 0: 
                dnommm = self.find_diam(design_load, material, fos=fos) / 0.001 # in mm for MP input
            else:
                raise Exception("Design load must be greater than zero")
        elif diam != None:
            if diam >= 0:
                dnommm = diam / 0.001 # in mm for MP input
            else:
                raise Exception("Diameter must be greater than zero")
        else:
            raise Exception("Somethings not right")
        
        return helpers.getLineProps(dnommm, material, lineProps = self.lineProps) # a moorpy lineType structure (dictionary)

    ### Point Stuff
    def getAnchor(self, soil_type, a_type = None, load = None, load_dir = None, mass = None):
        '''This uses moorpy to calculate the anchor size needed 
        for a design load and mooring shape. This function also 
        handles autosizing and selection of anchor types based 
        on load and load direction. Valid soil type checking is 
        handled inside of MoorPy. Uses anchor functons from 
        MoorProps, which contain factor of safety values. 
        
        Parameters
        ----------
        soli_type : string
            keyword that identifies the soil type. Options are: soft clay, medium clay, hard clay, sand
        a_type : string 
            keyword that identifies the anchor type. Options are: drag-embedment, gravity, VLA, SEPLA, suction
        load : float
            the design load for the anchor [N]
        load_dir : string
            keyword to identify anchor load direction. Options are: vertical, horizontal, both
        mass : float
            anchor mass [kg]
        
        Returns
        -------
        cost : float
            the cost of the anchor [2024$]
        mass : float
            the mass of the anchor [kg]
        a_type : string
            the anchor type
        '''        

        if mass == None and load != None and load_dir != None:

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
                    a_type = "gravity"
                    print(f"INFO: Anchor type set to '{a_type}'")

            elif load_dir == "vertical":
                loadx = 0.0
                loadz = load

                if a_type == "drag-embedment":
                    print("WARNING: drag embedment anchors should not be used with tension moorings")

                if a_type == None:
                    a_type = "gravity"
                    print(f"INFO: Anchor type set to '{a_type}'")
            else:
                print("WARNING: load direction not recognized, assuming no vertical loading and drag anchor") # TODO: should this be changed to a safer assumption?
                a_type = "drag-embedment"
                loadx = load
                loadz = 0.0

            outputs = mp.getAnchorCost(fx = loadx, fz = loadz, type = a_type, soil_type = soil_type, method = 'dynamic')
            if outputs == Exception:
                raise outputs
            
            mass = outputs[3]["Mass"] # from the MoorPy info data structure

            print(f"INFO: '{a_type}' anchor mass set to {mass:.3f} kg for load direction '{load_dir}' and soil type '{soil_type}'" )
        
        elif mass != None and load == None and load_dir == None:

            outputs = mp.getAnchorCost(fx = None, fz = None, type = a_type, mass = mass, soil_type = soil_type, method = 'dynamic')
            if outputs == Exception:
                raise outputs
            
        else:
            raise ValueError("Invalid input combo to getAnchor")
    
        cost = outputs[0] + outputs[1] + outputs[2] # Summing the first three outputs of MoorPy getAnchorCost: anchorMatCost, anchorInstCost, anchorDecomCost

        return cost, mass, a_type
    
    def getBuoy(self, buoyancy):
        '''Determines the cost of a buoy based on the defaults in MoorPy.
        
        Parameters
        ----------
        buoyancy : float
            the buoyancy of the buoy [kN]
        
        Returns
        -------
        float
            the cost of the buoy [2024$]
        '''        
        if buoyancy < 0: 
            raise Exception("Buoyancy must be greater than zero")

        # overwrite structure in self.pointProps. Most basic struture that gives buoys data from PointProps_default.yaml
        bProps = self.pointProps["BuoyProps"]
        bProps["general"]["buoyancy"] = buoyancy 
        props = dict(PointProps = dict(buoy = dict(num_b_general = 1, design_load = 0)), BuoyProps = bProps, ConnectProps = dict(placeholder = "placeholder")) # this is a dummy pointprops starting point that mimics a pointprops yaml. Passing it to loadPointProps will initialize all the unused variables that are needed for the code.
        
        
        MP_data = helpers.getPointProps(Type = "buoy", Props = helpers.loadPointProps(props)) # a moorpy pointType structure (dictionary)

        return MP_data["cost"]

    def getConnect(self, design_load):
        '''Given a design load, calculates the cost of a connection.
        This relies on the general connection design in the default 
        PointProps yaml to determine the number of different components.
        
        Parameters
        ----------
        design_load : float
            the design load of the connection [N]
        
        Returns
        -------
        float
            the cost of the connection [2024$]
        '''        
        if design_load < 0: 
            raise Exception("Design load must be greater than zero")
        
        # general type uses the PointProps general design
        MP_data = helpers.getPointProps(design_load = design_load, Type = "general", Props = self.pointProps) # a moorpy pointType structure (dictionary)

        return MP_data["cost"] # only cost data reutrned for now, mass coefficients not yet known

# User interface class and functions
class model():
    """
    This holds the mooring system design data.

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
    gravity <-- gravity
    VLA <-- vertical Load
    SEPLA <-- suction plate embedment
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
        '''Initializes the data structures for running the model, including the backend class'''
        # structures for tables
        self.line_type = {"id" : None, "num" : None, "MP_data" : None, "length" : None, "shape" : None, "design_load" : None, "FOS" : None, "nAnch" : None, "aLoadDir" : None, "nCon" : None}
        self.anchor_type = {"id" : None, "num" : None, "kind" : None, "mass" : None, "soil_type" : None}
        self.buoy_type = {"id" : None, "num" : None, "buoyancy" : None}
        self.backend = backend() # initialize the backend

    def load_database(self, path = None):
        '''Loads the lineProps and pointProps databases for determining mooring costs
        
        Parameters
        ----------
        path : list of strings
            A two element list of strings, that contains the paths to the lineProps and pointProps yamls to use with MoorPy.helpers. 
            If no path is given the default yamls in MoorPy are used.
        '''
        self.backend.load(path)

    def set_nLineTypes(self, n):
        '''sets the number of line types
        
        Parameters
        ----------
        n : int
            the number of line types
        '''
        self.nLineTypes = n
        self.LineTypes = []
        for i in range(n):
            self.LineTypes.append(self.line_type.copy())

    def set_nAnchTypes(self, n):
        '''sets the number of anchor types
        
        Parameters
        ----------
        n : int
            the number of anchor types
        '''
        self.nAnchTypes = n
        self.AnchTypes = []
        for i in range(n):
            self.AnchTypes.append(self.anchor_type.copy())

    def set_nBuoyTypes(self, n):
        '''sets the number of buoy types
        
        Parameters
        ----------
        n : int
            the number of buoy types
        '''
        self.nBuoyTypes = n
        self.BuoyTypes = []
        for i in range(n):
            self.BuoyTypes.append(self.buoy_type.copy())

    def set_paramsA0(self):
        '''Calcaultes the default mooring system design with no user inputs. This is a testing function.
        '''

        print("Using default parameters (catenary shape)")

        # system values
        self.depth = 200 # m
        soil_type = "soft clay"
        design_load = 10000 * 10**3 # N
        
        # inflation adjustment from 2024$
        self.inflation_scale = 1.0 # optional

        # Linetype data
        self.set_nLineTypes(1)
        self.LineTypes[0]["id"] = 0

        # user inputs
        self.LineTypes[0]["design_load"] = design_load
        self.LineTypes[0]["FOS"] = 2
        self.LineTypes[0]["num"] = 3
        self.LineTypes[0]["nAnch"] = 3
        self.LineTypes[0]["aLoadDir"] = 'horizontal'
        self.LineTypes[0]["nCon"] = 2

        # Load line type data from MoorProps
        self.LineTypes[0]["MP_data"] = self.backend.getLine(design_load=design_load, material="chain", fos = self.LineTypes[0]["FOS"])


        # Calculate length with MoorPy
        P = ((21.9*10**3 * self.LineTypes[0]["MP_data"]["input_d"] ** 2) - (np.pi/4)*(1.89*self.LineTypes[0]["MP_data"]["input_d"])**2 * 1025) * 9.81 # Wet weight per meter (N/m). MoorProps for R4 sudlink chain. TODO: change this to Moorpy
        self.LineTypes[0]["length"] = 15 + self.depth * np.sqrt(2*(self.LineTypes[0]["design_load"]/(P*self.depth))-1) # where P is the wet weight per meter. Assuming 15m on seabed. Eqn 5.15 from https://www.sciencedirect.com/book/9780128185513/mooring-system-engineering-for-offshore-structures

        # Connection values
        self.con_cost = self.backend.getConnect(design_load=design_load) * self.LineTypes[0]["nCon"]
        
        # Anchor values (for each type)
        self.set_nAnchTypes(1)
        self.AnchTypes[0]["num"] = self.LineTypes[0]["nAnch"]
        self.AnchTypes[0]["soil_type"] = soil_type
        self.AnchTypes[0]["cost"], self.AnchTypes[0]["mass"], self.AnchTypes[0]["kind"] = self.backend.getAnchor(self.AnchTypes[0]["soil_type"], load = self.LineTypes[0]["design_load"], load_dir = self.LineTypes[0]["aLoadDir"])

        # buoy values (optional)
        self.set_nBuoyTypes(0)

    def set_paramsA1(self, shape = None, depth = None, soil_type = None, design_load = None, Buoy_Table = [], inflation_scale = 1):
        '''Calculates the mooring system parameters, including unit cost,
        based on a low level of user inputs (similar to existing SAM inputs). 
        
        Parameters
        ----------
        shape : string
            the shape of the mooring lines. Options are: catenary, semi-taut, taut, tension
        depth : float
            the water depth [m]
        soil_type : string
            the type of soil. Options are: soft clay, medium clay, hard clay, sand
        design_load : float
            the design load of the system [N]
        BuoyTable : list
            a list of lists containing buoy parameters. Values are: "Num of these buoys", "Buoyancy [kN]"
        inflation_scale : float
            value to scale costs by to account for inflation from 2024$
        '''
        print("Using SAM level user provided parameters")

        # system values
        self.depth = depth
        
        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # assume fos of 2
        fos = 2

        # Line values (based on shape, depth, and design load)
        if shape == "catenary":
            self.set_nLineTypes(1)
            self.LineTypes[0]["id"] = 0
            # Load line type data from MoorProps
            self.LineTypes[0]["MP_data"] = self.backend.getLine(design_load=design_load, material="chain", fos=fos)
            # user inputs
            self.LineTypes[0]["shape"] = shape
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["FOS"] = fos
            self.LineTypes[0]["num"] = 3
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'horizontal'
            self.LineTypes[0]["nCon"] = 2
            # find length
            P = ((21.9*10**3 * self.LineTypes[0]["MP_data"]["input_d"] ** 2) - (np.pi/4)*(1.89*self.LineTypes[0]["MP_data"]["input_d"])**2 * 1025) * 9.81 # Wet weight per meter (N/m). MoorProps for R4 sudlink chain
            self.LineTypes[0]["length"] = 15 + self.depth * np.sqrt(2*(self.LineTypes[0]["design_load"]/(P*self.depth))-1) # where P is the wet weight per meter. Assuming 15m on seabed. Eqn 5.15 from https://www.sciencedirect.com/book/9780128185513/mooring-system-engineering-for-offshore-structures

        elif shape == "semi-taut":
            self.set_nLineTypes(2)
            self.LineTypes[0]["id"] = 0
            self.LineTypes[1]["id"] = 1
            # Load line type data from MoorProps
            self.LineTypes[0]["MP_data"] = self.backend.getLine(design_load=design_load, material="polyester", fos=fos)
            self.LineTypes[1]["MP_data"] = self.backend.getLine(design_load=design_load, material="chain", fos=fos)
            # user inputs
            self.LineTypes[0]["shape"] = shape
            self.LineTypes[1]["shape"] = shape
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[1]["design_load"] = design_load
            self.LineTypes[0]["FOS"] = fos
            self.LineTypes[1]["FOS"] = fos
            self.LineTypes[0]["num"] = 3
            self.LineTypes[1]["num"] = 3
            self.LineTypes[0]["nAnch"] = 0
            self.LineTypes[1]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'none'
            self.LineTypes[1]["aLoadDir"] = 'horizontal'
            self.LineTypes[0]["nCon"] = 1
            self.LineTypes[1]["nCon"] = 2
            # find length
            self.LineTypes[0]["length"] = np.sqrt(2* self.depth**2) # Assuming 45 deg hang off, straight to seabed
            self.LineTypes[1]["length"] = 15 # assuming 15m of chain on the seabed

        elif shape == "taut":
            self.set_nLineTypes(1)
            self.LineTypes[0]["id"] = 0
            # Load line type data from MoorProps
            self.LineTypes[0]["MP_data"] = self.backend.getLine(design_load=design_load, material="polyester", fos=fos)
            # user inputs
            self.LineTypes[0]["shape"] = shape
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["FOS"] = fos
            self.LineTypes[0]["num"] = 3
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'both'
            self.LineTypes[0]["nCon"] = 2
            # find length
            self.LineTypes[0]["length"] = np.sqrt(2* self.depth**2) # Assuming 45 deg hang off

        elif shape == "tension":
            self.set_nLineTypes(1)
            self.LineTypes[0]["id"] = 0
            # Load line type data from MoorProps
            self.LineTypes[0]["MP_data"] = self.backend.getLine(design_load=design_load, material="hmpe", fos=fos)
            # user inputs
            self.LineTypes[0]["shape"] = shape
            self.LineTypes[0]["design_load"] = design_load
            self.LineTypes[0]["FOS"] = fos
            self.LineTypes[0]["num"] = 8
            self.LineTypes[0]["nAnch"] = 1
            self.LineTypes[0]["aLoadDir"] = 'vertical'
            self.LineTypes[0]["nCon"] = 2
            # find length
            self.LineTypes[0]["length"] = self.depth

        else:
            raise Exception(f"Line shape {self.shape} is not supported")

        # Anchor Values
        self.set_nAnchTypes(0)
        self.con_cost = 0
        for i in range(self.nLineTypes):

            # Anchor values
            if self.LineTypes[i]["nAnch"] > 0: # while this may lead to duplicative anchor types, it keeps the code functioning. Assuming a unique anchor type for each line type with attached anchors
                if self.LineTypes[i]["aLoadDir"] == "none":
                    raise Exception(f"Anchor direction cannot be 'none' if nAnch is greater than zero (line {self.LineTypes[i]['id']+1})")
                self.AnchTypes.append(self.anchor_type.copy())
                self.nAnchTypes += 1

                self.AnchTypes[-1]["soil_type"] = soil_type
                self.AnchTypes[-1]["cost"], self.AnchTypes[-1]["mass"], self.AnchTypes[-1]["kind"] = self.backend.getAnchor(self.AnchTypes[-1]["soil_type"], load = self.LineTypes[i]["design_load"], load_dir = self.LineTypes[i]["aLoadDir"])
                self.AnchTypes[-1]["num"] = self.LineTypes[i]["nAnch"] * self.LineTypes[i]["num"]
        
            # Connection values
            self.con_cost += self.backend.getConnect(design_load=self.LineTypes[i]["design_load"]) * self.LineTypes[i]["nCon"]

        # Buoy values
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"] = buoy[1] # kN
            self.BuoyTypes[i]["cost"] = self.backend.getBuoy(self.BuoyTypes[i]["buoyancy"])

    def set_paramsA2(self, Line_Table = None, soil_type = None, depth = None, Buoy_Table = [], inflation_scale = 1):
        '''Calculates the mooring system parameters, including unit 
        cost, based on a medium level of user inputs (similar to 
        existing MoorPy/MoorDyn inputs). 
        
        Parameters
        ----------
        Line_Table : list
            a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter [m]", "Factor of safety", "Length [m]", "Load Direction", "Number of anchors for line", "Num connections per line"
        soil_type : string
            the type of soil. Options are: soft clay, medium clay, hard clay, sand
        depth : float
            the water depth [m]
        BuoyTable : list
            a list of lists containing buoy parameters. Values are: "Num of these buoys", "Buoyancy [kN]"
        inflation_scale : float
            value to scale costs by to account for inflation from 2024$
        '''

        print(f"Using MoorPy level parameters. {len(Line_Table)} different line types")

        # system values
        self.depth = depth # unused. TODO: Do we get rid of it? Or add a check that intput line lengths are sufficient for depth?
        
        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # Line values
        self.set_nLineTypes(len(Line_Table))

        for i,line in enumerate(Line_Table):
            self.LineTypes[i]["id"] = i
            # Load line type data from MoorProps
            self.LineTypes[i]["MP_data"] = self.backend.getLine(material=line[1], diam=line[2], fos=line[3])
            self.LineTypes[i]["FOS"] = line[3]
            self.LineTypes[i]["design_load"] = self.LineTypes[i]["MP_data"]["MBL"] / self.LineTypes[i]["FOS"]
            # user inputs 
            self.LineTypes[i]["num"] = line[0]
            self.LineTypes[i]["length"] = line[4]
            self.LineTypes[i]["aLoadDir"] = line[5]
            self.LineTypes[i]["nAnch"] = line[6]
            self.LineTypes[i]["nCon"] = line[7]


        # Anchor values 
        self.set_nAnchTypes(0)
        self.con_cost = 0
        for i in range(len(Line_Table)):
            if self.LineTypes[i]["nAnch"] > 0: # while this may lead to duplicative anchor types, it keeps the code functioning. Assuming a unique anchor type for each line type with attached anchors
                if self.LineTypes[i]["aLoadDir"] == "none":
                    raise Exception(f"Anchor direction cannot be 'none' if nAnch is greater than zero (line {self.LineTypes[i]['id']+1})")
                self.AnchTypes.append(self.anchor_type.copy())
                self.nAnchTypes += 1

                self.AnchTypes[-1]["soil_type"] = soil_type
                self.AnchTypes[-1]["cost"], self.AnchTypes[-1]["mass"], self.AnchTypes[-1]["kind"] = self.backend.getAnchor(self.AnchTypes[-1]["soil_type"], load = self.LineTypes[i]["design_load"], load_dir = self.LineTypes[i]["aLoadDir"])
                self.AnchTypes[-1]["num"] = self.LineTypes[i]["nAnch"] * self.LineTypes[i]["num"]
        
            # Connection values
            self.con_cost += self.backend.getConnect(design_load=self.LineTypes[i]["design_load"]) * self.LineTypes[i]["nCon"]

        # buoy values (optional)
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"]= buoy[1] # kN
            self.BuoyTypes[i]["cost"] = self.backend.getBuoy(self.BuoyTypes[i]["buoyancy"])

    def set_paramsA3(self, Line_Table = None, Anchor_Table = None, depth = None, Buoy_Table = [], inflation_scale = 1):
        '''Calculates the mooring system parameters, including unit 
        cost, based on a high level of user inputs. 
        
        Parameters
        ----------
        Line_Table : list
            a list of lists, one for each line type in the system. Values are: Line_Table: a list of lists, one for each line type in the system. Values are: "Num of these lines", "Line material", "Diameter [m]", "Factor of safety", "Length [m]", "Num connections per line"
        Anchor_Table : list
            a list of lists, one for each anchor type in the system. Values are: "anchor type num", "anchor type", "anchor mass [kg]", "soil type"
        depth : float
            the water depth [m]
        BuoyTable : list
            a list of lists containing buoy parameters. Values are: "Num of these buoys", "Buoyancy [kN]"
        inflation_scale : float
            value to scale costs by to account for inflation from 2024$
        '''       

        print("Using FAD level user provided parameters")

        # system values
        self.depth = depth

        # inflation adjustment from 2024$
        self.inflation_scale = inflation_scale # optional

        # Line and connection values
        self.set_nLineTypes(len(Line_Table))
        self.con_cost = 0
        for i,line in enumerate(Line_Table):
            self.LineTypes[i]["id"] = i
            # Load line type data from MoorProps
            self.LineTypes[i]["MP_data"] = self.backend.getLine(material=line[1], diam=line[2], fos=line[3])
            self.LineTypes[i]["FOS"] = line[3]
            self.LineTypes[i]["design_load"] = self.LineTypes[i]["MP_data"]["MBL"] / self.LineTypes[i]["FOS"]
            # user inputs
            self.LineTypes[i]["num"] = line[0]
            self.LineTypes[i]["length"] = line[4]
            self.LineTypes[i]["nCon"] = line[5]

            # Connection values
            self.con_cost += self.backend.getConnect(design_load=self.LineTypes[i]["design_load"]) * self.LineTypes[i]["nCon"]
        
        self.set_nAnchTypes(len(Anchor_Table))
        for i, anchor in enumerate(Anchor_Table):
            self.AnchTypes[i]["id"] = i
            self.AnchTypes[i]["num"] = anchor[0]
            self.AnchTypes[i]["kind"] = anchor[1]
            self.AnchTypes[i]["mass"] = anchor[2]
            self.AnchTypes[i]["soil_type"] = anchor[3]
            self.AnchTypes[i]["cost"], mass, kind = self.backend.getAnchor(self.AnchTypes[i]["soil_type"], a_type = self.AnchTypes[i]["kind"], mass = self.AnchTypes[i]["mass"] )

        # buoy values (optional)
        self.set_nBuoyTypes(len(Buoy_Table))
        for i, buoy in enumerate(Buoy_Table):
            self.BuoyTypes[i]["id"] = i
            self.BuoyTypes[i]["num"] = buoy[0]
            self.BuoyTypes[i]["buoyancy"]= buoy[1] # kN
            self.BuoyTypes[i]["cost"] = self.backend.getBuoy(self.BuoyTypes[i]["buoyancy"])

    # ---------- Outputs ----------

    def calc_cost(self):
        '''Calculates and prints the total cost of the mooring system based on the 
        parameters loaded by the set_params functions
        '''
        Line_cost = 0
        for lType in self.LineTypes:
            Line_cost += self.inflation_scale * lType["num"] * lType["length"] * lType["MP_data"]["cost"]
        
        Anchor_cost = 0
        for aType in self.AnchTypes:
            Anchor_cost += self.inflation_scale * aType["num"] * aType["cost"]
        
        Connection_cost = self.inflation_scale * self.con_cost

        Buoy_cost = 0
        for bType in self.BuoyTypes:
            Buoy_cost += self.inflation_scale * bType["num"] * bType["cost"]

        Total_cost = Line_cost + Anchor_cost + Connection_cost + Buoy_cost # this is the cost of the mooring system

        print("--------- Cost Report (2024$) ---------")
        print(f"System Parameters")
        print(f"    Water Depth: {self.depth:.3f} m")
        print(f"Line Parameters")
        for lType in self.LineTypes:
            print(f"    Material   : {lType['MP_data']['material']}")
            print(f"    Number     : {lType['num']}")
            print(f"    Length     : {lType['length']:.3f} m")
            print(f"    Diameter   : {lType['MP_data']['input_d']:.3f} m")
            print(f"    design load: {lType['design_load']:.3f} N")
        print(f"Anchor Parameters")
        for aType in self.AnchTypes:
            print(f"    Type       : {aType['kind']}")
            print(f"    Number     : {aType['num']}")
            print(f"    Mass       : {aType['mass']:.3f} kg")
            print(f"    Soil type  : {aType['soil_type']}")
        # print(f"Connection Hardware Parameters")
        # print(f"    Mass       : {self.con_mass:.3f} kg")
        print(f"Buoyancy Module Parameters")
        for bType in self.BuoyTypes:
            print(f"    Num Buoys  : {bType['num']}")
            print(f"    Buoyancy   : {bType['buoyancy']:.3f} kN")
        print(f"--------------------------------------")
        print(f"Anchor cost     : $ {Anchor_cost:.2f}  |  {(Anchor_cost/Total_cost)*100:.1f}%")
        print(f"Line cost       : $ {Line_cost:.2f}  |  {(Line_cost/Total_cost)*100:.1f}%")
        print(f"Buoy cost       : $ {Buoy_cost:.2f}  |  {(Buoy_cost/Total_cost)*100:.1f}%")
        print(f"Connection cost : $ {Connection_cost:.2f}  |  {(Connection_cost/Total_cost)*100:.1f}%")
        print(f"Total cost      : $ {Total_cost:.2f}  |  {(Total_cost/Total_cost)*100:.1f}%")
        print("---------------------------------------")

if __name__ == "__main__":
    tool = model()
    # lines = [[1, "chain", 0.2, 100, "horizontal", 1]]
    # tool.set_paramsA2(Line_Table = lines, soil_type = "sand", depth = 100)

    # tool.set_paramsA1(shape = "taut", depth = 100, design_load = 100000, soil_type = "soft clay")

    tool.set_paramsA2(Line_Table = [[3,"polyester",.2,50,"none",0],[3,"chain",.1,20,"horizontal",1]],depth = 100, soil_type = "soft clay")
    tool.calc_cost()