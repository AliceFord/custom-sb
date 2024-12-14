PORT = 6809  # 6810 for internet connection

TURN_RATE = 2  # deg / sec
TAXI_SPEED = 15  # knots
PUSH_SPEED = 5  # knots
CLIMB_RATE = 2500  # ft / min
DESCENT_RATE = -2000  # ft / min
HIGH_DESCENT_RATE = -3000  # ft / min

timeMultiplier: float = 1
RADAR_UPDATE_RATE = 5 / timeMultiplier  # seconds

CCAMS_SQUAWKS = list(range(201,277)) + list(range(301,377)) + list(range(470,477)) + list(range(501,577)) + list(range(730,767)) + list(range(1070,1077)) + list(range(1140,1176)) + list(range(1410,1477)) + list(range(2001,2077)) + list(range(2150,2177)) + list(range(2201,2277)) + list(range(2701,2737)) + list(range(3201,3277)) + list(range(3370,3377)) + list(range(3401,3477)) + list(range(3510,3537)) + list(range(4215,4247)) + list(range(4430,4477)) + list(range(4701,4777)) + list(range(5013,5017)) + list(range(5201,5270)) + list(range(5401,5477)) + list(range(5660,5664)) + list(range(5565,5676)) + list(range(6201,6257)) + list(range(6301,6377)) + list(range(6460,6467)) + list(range(6470,6477)) + list(range(7014,7017)) + list(range(7020,7027)) + list(range(7201,7267)) + list(range(7270,7277)) + list(range(7301,7327)) + list(range(7501,7507)) + list(range(7536,7537)) + list(range(7570,7577)) + list(range(7601,7617)) + list(range(7620,7677)) + list(range(7701,7775)) + list(range(1250,1257)) + list(range(6001,6037))

# ACTIVE_AERODROMES = ["EGLL", "EGKK", "EGLC", "EGSS", "EGGW"]
# ACTIVE_RUNWAYS = {"EGLL": "27R", "EGKK": "26L", "EGLC": "27", "EGSS": "22", "EGGW": "25"}
# ACTIVE_CONTROLLERS = ["LTC_EJ_CTR", "LTC_ER_CTR", "EGSS_APP", "LON_E_CTR", "LTC_E_CTR"]
# MASTER_CONTROLLER = "EGNT_APP"
# MASTER_CONTROLLER_FREQ = "24380"

ACTIVE_AERODROMES = ["EGPH","EGPF","EGPK"]
ACTIVE_RUNWAYS = {"EGPH" : "24" ,"EGPF" : "23" ,"EGPK" : "30"}
ACTIVE_CONTROLLERS = ["STC_CTR", "STC_E_CTR", "STC_W_CTR"]
MASTER_CONTROLLER = "SCO_D_CTR"
MASTER_CONTROLLER_FREQ = "35855"

# ACTIVE_AERODROMES = ["EGCC"]
# ACTIVE_RUNWAYS = {"EGCC": "23R"}
# ACTIVE_CONTROLLERS = ["EGCC_S_APP", "EGCC_N_APP", "EGCC_F_APP", "MAN_CTR", "MAN_W_CTR", "MAN_SE_CTR", "MAN_E_CTR", "MAN_NE_CTR"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"

# ACTIVE_AERODROMES = ["EGSS","EGGW"]
# ACTIVE_RUNWAYS = {"EGSS": "22","EGGW":"25"}
# ACTIVE_CONTROLLERS = ["ESSEX_APP" ,"EGSS_APP","EGSS_F_APP","EGGW_APP","EGGW_APP"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"


# ACTIVE_AERODROMES = ["EGLL"]
# ACTIVE_RUNWAYS = {"EGLL": "09R"}
# ACTIVE_CONTROLLERS = ["EGLL_N_APP", "EGLL_S_APP", "EGLL_F_APP"]
# MASTER_CONTROLLER = "LON_D_CTR"
# MASTER_CONTROLLER_FREQ = "34905"

# ACTIVE_AERODROMES = ["EGPF"]
# ACTIVE_RUNWAYS = {"EGPF": "05"}
# ACTIVE_CONTROLLERS = ["EGPF_APP"]
# MASTER_CONTROLLER = "SCO_D_CTR"
# MASTER_CONTROLLER_FREQ = "35855"

# ACTIVE_AERODROME = "EGAA"
# ACTIVE_RUNWAY = "25"
# ACTIVE_CONTROLLERS = ["EGAA_APP", "EGAA_F_APP"]
# MASTER_CONTROLLER = "STC_A_CTR"
# MASTER_CONTROLLER_FREQ = "23775"

# ACTIVE_AERODROMES = ["EGKK"]
# ACTIVE_RUNWAYS = {"EGKK": "26L"}
# ACTIVE_CONTROLLERS = ["EGKK_APP", "EGKK_F_APP"]
# MASTER_CONTROLLER = "LON_D_CTR"
# MASTER_CONTROLLER_FREQ = "34905"

# ACTIVE_AERODROMES = ["EGNM"]
# ACTIVE_RUNWAYS = {"EGNM": "14"}
# ACTIVE_CONTROLLERS = ["EGNM_APP", "EGNM_F_APP"]
# MASTER_CONTROLLER = "MAN_NE_CTR"
# MASTER_CONTROLLER_FREQ = "35715"

# ACTIVE_AERODROME = "EGHI"
# ACTIVE_RUNWAY = "20"
# ACTIVE_CONTROLLERS = ["SOLENT_APP"]
# MASTER_CONTROLLER = "LTC_SW_CTR"
# MASTER_CONTROLLER_FREQ = "33180"

# ACTIVE_AERODROMES = ["EGJJ", "EGJB", "EGJA"]
# ACTIVE_RUNWAYS = {"EGJJ": "08", "EGJB": "09", "EGJA": "08"}
# ACTIVE_CONTROLLERS = ["EGJJ_C_APP", "EGJJ_S_APP"]
# MASTER_CONTROLLER = "LTC_SW_CTR"
# MASTER_CONTROLLER_FREQ = "33180"

# ACTIVE_AERODROMES = ["EGPH", "EGPF", "EGPK"]
# ACTIVE_RUNWAYS = {"EGPH": "24", "EGPF": "23", "EGPK": "12"}
# ACTIVE_CONTROLLERS = ["STC_E_CTR", "STC_W_CTR", "STC_CTR", "EGPH_APP", "EGPF_APP", "EGPK_APP"]
# MASTER_CONTROLLER = "SCO_D_CTR"
# MASTER_CONTROLLER_FREQ = "35855"

# ACTIVE_AERODROMES = ["EGPH"]
# ACTIVE_RUNWAYS = {"EGPH": "24"}
# ACTIVE_CONTROLLERS = ["EGPH_APP","EGPH_F_APP"]
# MASTER_CONTROLLER = "SCO_D_CTR"
# MASTER_CONTROLLER_FREQ = "35855"

# ACTIVE_AERODROMES = ["EGPH", "EGPF", "EGPK", "EGPD", "EGPE"]
# ACTIVE_RUNWAYS = {"EGPH": "24", "EGPF": "23", "EGPK": "12", "EGPD": "34", "EGPE": "05"}
# ACTIVE_CONTROLLERS = ["SCO_E_CTR"]
# MASTER_CONTROLLER = "SCO_D_CTR"
# MASTER_CONTROLLER_FREQ = "35855"

# ACTIVE_AERODROMES = ["EGKK", "EGLL"]
# ACTIVE_RUNWAYS = {"EGKK": "26L", "EGLL": "27R"}
# ACTIVE_CONTROLLERS = ["LTC_SW_CTR", "LTC_CTR", "LTC_S_CTR", "EGSS_APP", "EGGW_APP", "LTC_N_CTR", "LTC_SE_CTR", "EGKK_F_APP", "EGLL_S_APP", "EGLL_F_APP", "EGLL_N_APP", "EGKK_APP"]  # 
# MASTER_CONTROLLER = "LON_S_CTR"
# MASTER_CONTROLLER_FREQ = "29430"

# ACTIVE_AERODROMES = ["EGKK", "EGLL", "EGSS", "EGGW"]
# ACTIVE_RUNWAYS = {"EGKK": "26L", "EGLL": "27R", "EGSS": "04", "EGGW": "07"}
# ACTIVE_CONTROLLERS = ["LTC_SW_CTR", "LTC_CTR", "LTC_S_CTR", "EGSS_APP", "EGGW_APP", "LTC_N_CTR", "LTC_SE_CTR", "EGKK_F_APP", "EGLL_S_APP", "EGLL_F_APP", "EGLL_N_APP", "EGKK_APP", "ESSEX_APP", "EGSS_F_APP", "EGGW_F_APP"]  # 
# MASTER_CONTROLLER = "LON_D_CTR"
# MASTER_CONTROLLER_FREQ = "34905"

# ACTIVE_AERODROMES = ["EGNX"]
# ACTIVE_RUNWAYS = {"EGNX": "09"}
# ACTIVE_CONTROLLERS = ["EGNX_APP", "EGNX_F_APP"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"

# ACTIVE_AERODROMES = ["EGLC", "EGMC"]
# ACTIVE_RUNWAYS = {"EGLC": "09", "EGMC": "05"}
# ACTIVE_CONTROLLERS = ["THAMES_APP", "EGMC_APP"]
# MASTER_CONTROLLER = "LON_E_CTR"
# MASTER_CONTROLLER_FREQ = "18480"

# ACTIVE_AERODROMES = ["EGNX", "EGBB"]
# ACTIVE_RUNWAYS = {"EGNX": "09", "EGBB": "33"}
# ACTIVE_CONTROLLERS = ["LTC_M_CTR", "EGNX_APP", "EGBB_APP"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"

# ACTIVE_AERODROMES = ["EGFF", "EGGD"]
# ACTIVE_RUNWAYS = {"EGFF": "12", "EGGD": "09"}
# ACTIVE_CONTROLLERS = ["LON_W_CTR", "LON_WB_CTR", "EGFF_APP", "EGGD_APP"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"

# ACTIVE_AERODROMES = ["EGNT", "EGNV"]
# ACTIVE_RUNWAYS = {"EGNT": "07", "EGNV": "05"}
# ACTIVE_CONTROLLERS = ["MAN_NE_CTR", "EGNT_APP", "EGNT_F_APP"]
# MASTER_CONTROLLER = "LON_NE_CTR"
# MASTER_CONTROLLER_FREQ = "28130"

# ACTIVE_AERODROMES = ["EGCC"]
# ACTIVE_RUNWAYS = {"EGCC": "23R"}
# ACTIVE_CONTROLLERS = ["EGCC_S_APP", "EGCC_N_APP", "EGCC_F_APP"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"
# ACTIVE_CONTROLLERS = ["EGCC_S_APP", "EGCC_N_APP", "EGCC_F_APP", "MAN_CTR", "MAN_W_CTR", "MAN_SE_CTR", "MAN_E_CTR", "MAN_NE_CTR"]
# MASTER_CONTROLLER = "LON_M_CTR"
# MASTER_CONTROLLER_FREQ = "20025"

# TESTING ONLY CC
# ACTIVE_AERODROMES = ["EGCC", "EGGP"]
# ACTIVE_RUNWAYS = {"EGCC": "23R", "EGGP": "27"}
# ACTIVE_CONTROLLERS = ["MAN_WI_CTR", "MAN_WL_CTR", "EGCC_S_APP", "EGGP_APP"]
# MASTER_CONTROLLER = "MAN_SE_CTR"
# MASTER_CONTROLLER_FREQ = "34430"

# ACTIVE_AERODROMES = ["EGLL", "EGKK", "EGLC", "EGSS", "EGGW"]
# ACTIVE_RUNWAYS = {"EGLL": "27R", "EGKK": "26L", "EGLC": "27", "EGSS": "22", "EGGW": "25"}
# ACTIVE_CONTROLLERS = ["LTC_EJ_CTR", "LTC_ER_CTR", "EGSS_APP", "LON_E_CTR", "LTC_E_CTR"]
# MASTER_CONTROLLER = "EGNT_APP"
# MASTER_CONTROLLER_FREQ = "24380"

# ACTIVE_AERODROMES = ["EGCC", "EGPH"]
# ACTIVE_RUNWAYS = {"EGCC": "23R", "EGPH": "24"}
# ACTIVE_CONTROLLERS = ["LON_ME_CTR", "LON_SC_CTR"]
# MASTER_CONTROLLER = "EGNT_APP"
# MASTER_CONTROLLER_FREQ = "24380"

# ACTIVE_AERODROMES = ["EGSS", "EGGW"]
# ACTIVE_RUNWAYS = {"EGSS": "22", "EGGW": "25"}
# ACTIVE_CONTROLLERS = ["LTC_E_CTR", "LTC_N_CTR", "ESSEX_APP", "EGSS_APP", "EGGW_APP"]
# MASTER_CONTROLLER = "MAN_SE_CTR"
# MASTER_CONTROLLER_FREQ = "34430"


INACTIVE_SECTORS = [
    # "LTC_E_CTR",
    # "LTC_M_CTR",
    # "LTC_NE_CTR",
    # "LTC_NW_CTR",
    # "LTC_SE_CTR",
    # "LTC_SW_CTR",
    # "LON_W_CTR"
]

# OTHER_CONTROLLERS = []
OTHER_CONTROLLERS = [
    # ("EGCC_S_APP","18580"),
    # ("EGCC_N_APP", "35005"),
    # ("EGCC_F_APP", "21355"),
    # ("EGGP_APP", "19855"),
    # ("EGPH_APP", "21205"),
    # ("EGPF_APP", "19100"),
    # ("EGPK_APP", "29450"),
    # ("EGPD_APP", "19055"),
    # ("EGPE_APP", "22605"),
    # ("EGNT_APP", "24380"),
    # ("EGPB_APP", "31300"),
    # ("EGKK_APP", "26825"),
    # ("EGLL_N_APP", "19730"),
    # ("ESSEX_APP", "20625"),
    # ("EGGD_APP", "25650"),
    # ("EGFF_APP", "25855"),

    ("BIRD_S1_CTR", "19700"),
    ("EURN_FSS", "33450"),
    ("EKDK_CTR", "36485"),
    ("EHAA_W_CTR", "25750"),
    ("EISN_CTR", "34260"),

    # ("LON_W_CTR", "26080"),
    # ("LON_E_CTR", "18480"),
    ("LON_M_CTR", "20025"),
    ("LON_D_CTR", "34905"),
    # ("LON_NW_CTR", "35580"),
    # ("LON_NE_CTR", "28130"),
    # ("LON_S_CTR", "29430"),

    # ("LTC_E_CTR", "21230"),
    # # ("LTC_M_CTR", "21030"),
    # ("LTC_NE_CTR", "18825"),
    # ("LTC_NW_CTR", "21280"),
    # ("LTC_SE_CTR", "20530"),
    # ("LTC_SW_CTR", "33180"),

    ("MAN_WU_CTR", "18780"),
    ("MAN_NE_CTR", "35715"),
    ("MAN_SE_CTR", "34430"),
    # ("MAN_W_CTR", "28055"),

    ("SCO_D_CTR", "35855"),
    # ("SCO_N_CTR", "29225"),
    ("SCO_R_CTR", "29100"),
    ("SCO_S_CTR", "34755"),
    ("SCO_W_CTR", "32730"),

    ("STC_A_CTR", "23775"),
    # ("STC_W_CTR", "24825"),
    # ("STC_E_CTR", "30975")
]
# ACTIVE_CONTROLLER = "LON_S_CTR"
# MASTER_CONTROLLER = "EGLL_N_APP"
# MASTER_CONTROLLER_FREQ = "19730"


# DISABLE FEATURES
AUTO_ASSUME = False  # ALL COMMENTED OUT WILL NOT WORK AT ALL


TRANSITION_LEVEL = 6000

KILL_ALL_ON_HANDOFF = True

VREF_TABLE = {
    "B738": range(135, 155),  # Boeing 737-800
    "B38M": range(140, 160),  # Boeing 737 MAX 8
    "A320": range(130, 150),  # Airbus A320
    "A319": range(125, 145),  # Airbus A319
    "A321": range(135, 155),  # Airbus A321
    "A20N": range(130, 150),  # Airbus A320neo
    "A21N": range(135, 155),  # Airbus A321neo
    "A35K": range(150, 170),  # Airbus A350-1000
    "A388": range(155, 175),  # Airbus A380-800
    "B772": range(145, 165),  # Boeing 777-200
    "B788": range(140, 160),  # Boeing 787-8
    "B789": range(145, 165),  # Boeing 787-9
    "B78X": range(150, 170),  # Boeing 787-10
    "A318": range(125, 135),  # Airbus A318
    "A332": range(145, 165),  # Airbus A330-200
    "A333": range(150, 170),  # Airbus A330-300
    "B77W": range(150, 170),  # Boeing 777-300ER
    "B737": range(130, 150),  # Boeing 737-700
    "B739": range(135, 155),  # Boeing 737-900
    "B744": range(155, 175),  # Boeing 747-400
    "B752": range(135, 150),  # Boeing 757-200
    "B763": range(140, 160),  # Boeing 767-300
    "B773": range(150, 170),  # Boeing 777-300
    "E190": range(125, 140),  # Embraer E190
    "E195": range(130, 145),  # Embraer E195
}


FLEET = {
    "RYR" : ["B738", "B38M","A320"],
    "BAW" : ["A319","A320", "A321", "A20N", "A21N", "A35K", "A388", "B772", "B788", "B789", "B78X"],
    "SHT" : ["A320"],
    "EFW" : ["A320"],
    "EZY" : ["A319","A320","A321","A20N","A21N"],
    "EJU" : ["A319","A320","A321","A20N","A21N"],
    "EZS" : ["A319","A320","A321","A20N","A21N"],
    "WZZ" : ["A320","A321","A20N","A21N"],
    "DLH" : ["A320", "A20N"],
    "EIN" : ["A320", "A20N", "A333"],
    "AFR" : ["A318", "A319", "A320", "A321", "A332", "A333", "A388", "B772", "B77W", "B789"],
    "KLM" : ["B737", "B738", "B739", "B744", "B772", "B77W", "B789", "B78X", "A332", "A333"],
    "UAE" : ["A388", "B77W"],
    "AAL" : ["A319", "A320", "A321", "A332", "A333", "B738", "B752", "B763", "B772", "B77W", "B788", "B789"],
    "UAL" : ["A319", "A320", "B738", "B739", "B752", "B763", "B772", "B77W", "B788", "B789", "B78X"],
    "SWA" : ["B737", "B738"],
    "QFA" : ["A332", "A333", "A388", "B738", "B789", "B78X"],
    "ANA" : ["B772", "B773", "B77W", "B788", "B789", "B78X", "A321", "A332", "A333"],
    "JAL" : ["B772", "B773", "B77W", "B788", "B789", "B78X", "A321"],
    "TUI" : ["B737", "B738", "B38M", "E190", "B763", "B788", "E195"],
    "TOM" : ["B738", "B38M", "B763", "B788","B789"]
}

AIRPORTS = {
    "EGLL": ["BAW", "SHT", "DLH", "EIN", "AFR", "KLM", "UAE", "AAL", "UAL", "QFA", "ANA", "JAL"],
    "EGKK": ["RYR", "BAW", "EFW", "EZY", "EZS", "EJU", "WZZ", "DLH", "EIN", "UAE", "TOM"],
    "EGCC": ["RYR", "BAW", "EZY", "EZS", "EJU", "WZZ", "DLH", "EIN", "UAE", "TOM", "SHT"],
    "EGPH": ["RYR", "BAW", "EZY", "EZS", "EJU", "WZZ", "DLH", "EIN", "UAE", "TOM"],
    "EGPF": ["RYR", "BAW", "EZY", "EZS", "EJU", "WZZ", "DLH", "EIN", "UAE", "TOM"],
    "EGGW": ["RYR", "EZY", "WZZ"],
    "EGSS": ["RYR", "EZY", "WZZ", "DLH", "EIN", "UAE", "TOM"],
}

AIRPORT_ELEVATIONS = {
    "EGLL": 83, 
    "EGKK": 202,
    "EGCC": 257,
    "EGPH": 135,
    "EGNX": 306,
    "EGGD": 622,
    "EGGW": 526,
    "EGSS": 348,
    "EGPF": 26, 
    "EGAA": 268,
    "EGNT": 266,
    "EGMC": 49, 
    "EGNM": 681,
}


# Data from https://github.com/vatsimnetwork/euroscope-performance-data
# PERFLINE = FL:climb speed:cruize speed:descent speed:climb Mach:cruize Mach:descent Mach:ROC:ROD

AIRCRAFT_PERFORMACE : dict[str:dict[str:list[str]]]= {
    "A20N": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2600",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2600",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2300",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1900",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1600",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "1300",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "1100",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "1000",
            "1500"
        ]
    },
    "A21N": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2500",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2400",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2100",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1500",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "1200",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "1000",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "078",
            "078",
            "800",
            "1500"
        ]
    },
    "A318": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2000",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2000",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "076",
            "079",
            "076",
            "1600",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "076",
            "079",
            "076",
            "1500",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "076",
            "079",
            "076",
            "1100",
            "1500"
        ]
    },
    "A319": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2500",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1500",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "1500"
        ]
    },
    "A320": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2500",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1500",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "1500"
        ]
    },
    "A321": {
        "030": [
            "200",
            "220",
            "170",
            "0",
            "0",
            "0",
            "2500",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1500",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "2000"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1000",
            "1500"
        ]
    },
    "A332": {
        "030": [
            "190",
            "250",
            "170",
            "0",
            "0",
            "0",
            "2000",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "1800"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2500",
            "2200"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "2500"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "1800"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "080",
            "1800",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "080",
            "1500",
            "2300"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "080",
            "1200",
            "2500"
        ]
    },
    "A333": {
        "030": [
            "190",
            "250",
            "170",
            "0",
            "0",
            "0",
            "2000",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2000",
            "2000"
        ],
        "150": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2500"
        ],
        "200": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1400",
            "2200"
        ],
        "250": [
            "290",
            "300",
            "290",
            "0",
            "0",
            "0",
            "1300",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "081",
            "1000",
            "2100"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "081",
            "1000",
            "2200"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "081",
            "081",
            "1000",
            "2300"
        ]
    },
    "A35K": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2900",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2400",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "1500"
        ],
        "150": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "2200",
            "1600"
        ],
        "200": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "2100",
            "1800"
        ],
        "250": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "1700",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "1450",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "900",
            "2500"
        ]
    },
    "A388": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2000",
            "900"
        ],
        "050": [
            "230",
            "250",
            "230",
            "0",
            "0",
            "0",
            "2200",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "1500"
        ],
        "150": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "2100",
            "1600"
        ],
        "200": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "1800",
            "1800"
        ],
        "250": [
            "300",
            "350",
            "300",
            "0",
            "0",
            "0",
            "1400",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "083",
            "085",
            "083",
            "1300",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "083",
            "085",
            "083",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "083",
            "085",
            "083",
            "900",
            "2500"
        ]
    },
    "B737": {
        "030": [
            "180",
            "230",
            "210",
            "0",
            "0",
            "0",
            "3200",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1800"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2800",
            "2000"
        ],
        "150": [
            "275",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2600",
            "2500"
        ],
        "200": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2600",
            "2400"
        ],
        "250": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2300",
            "2400"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1500",
            "2400"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1100",
            "2900"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "800",
            "2800"
        ]
    },
    "B738": {
        "030": [
            "190",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "200",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2600",
            "1500"
        ],
        "150": [
            "275",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2200",
            "1800"
        ],
        "200": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2000",
            "2200"
        ],
        "250": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2000",
            "2400"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1300",
            "2400"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1050",
            "2900"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "700",
            "2800"
        ]
    },
    "B38M": {
        "030": [
            "190",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2900",
            "900"
        ],
        "050": [
            "200",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3100",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2700",
            "1500"
        ],
        "150": [
            "275",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2300",
            "1800"
        ],
        "200": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2200",
            "2200"
        ],
        "250": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2100",
            "2400"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1400",
            "2400"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1150",
            "2900"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "900",
            "2800"
        ]
    },
    "B739": {
        "030": [
            "190",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "200",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2600",
            "1500"
        ],
        "150": [
            "270",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2200",
            "1800"
        ],
        "200": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2000",
            "2200"
        ],
        "250": [
            "280",
            "280",
            "280",
            "0",
            "0",
            "0",
            "2000",
            "2400"
        ],
        "300": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1300",
            "2400"
        ],
        "350": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "1050",
            "2900"
        ],
        "400": [
            "0",
            "0",
            "0",
            "078",
            "079",
            "078",
            "700",
            "2800"
        ]
    },
    "B744": {
        "030": [
            "220",
            "220",
            "210",
            "0",
            "0",
            "0",
            "1700",
            "900"
        ],
        "050": [
            "250",
            "250",
            "220",
            "0",
            "0",
            "0",
            "1500",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "1500",
            "1300"
        ],
        "150": [
            "275",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1500",
            "1500"
        ],
        "200": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1500",
            "1800"
        ],
        "250": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1500",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "1200",
            "2100"
        ],
        "350": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "1100",
            "2200"
        ],
        "400": [
            "0",
            "0",
            "0",
            "082",
            "085",
            "085",
            "900",
            "2700"
        ]
    },
    "B752": {
        "030": [
            "190",
            "230",
            "210",
            "0",
            "0",
            "0",
            "3500",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3200",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "3200",
            "1800"
        ],
        "150": [
            "280",
            "310",
            "280",
            "0",
            "0",
            "0",
            "3000",
            "2000"
        ],
        "200": [
            "300",
            "310",
            "280",
            "0",
            "0",
            "0",
            "2500",
            "2200"
        ],
        "250": [
            "300",
            "310",
            "280",
            "0",
            "0",
            "0",
            "2500",
            "2500"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "2200",
            "2500"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "1900",
            "2600"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "1000",
            "2400"
        ]
    },
    "B763": {
        "030": [
            "190",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "900"
        ],
        "050": [
            "220",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "1800"
        ],
        "150": [
            "275",
            "310",
            "290",
            "0",
            "0",
            "0",
            "2400",
            "2000"
        ],
        "200": [
            "300",
            "310",
            "290",
            "0",
            "0",
            "0",
            "2200",
            "2000"
        ],
        "250": [
            "300",
            "310",
            "290",
            "0",
            "0",
            "0",
            "1800",
            "2200"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "1500",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "1100",
            "2500"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "080",
            "080",
            "1000",
            "2800"
        ]
    },
    "B772": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2500",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2400",
            "1500"
        ],
        "150": [
            "275",
            "330",
            "310",
            "0",
            "0",
            "0",
            "2200",
            "1600"
        ],
        "200": [
            "300",
            "330",
            "310",
            "0",
            "0",
            "0",
            "2000",
            "1800"
        ],
        "250": [
            "300",
            "330",
            "310",
            "0",
            "0",
            "0",
            "1700",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1450",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "B773": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2400",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "1500"
        ],
        "150": [
            "275",
            "330",
            "310",
            "0",
            "0",
            "0",
            "2200",
            "1600"
        ],
        "200": [
            "300",
            "330",
            "310",
            "0",
            "0",
            "0",
            "2000",
            "1800"
        ],
        "250": [
            "300",
            "330",
            "310",
            "0",
            "0",
            "0",
            "1700",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1450",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "B77W": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "2800",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2400",
            "1200"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2300",
            "1500"
        ],
        "150": [
            "275",
            "350",
            "310",
            "0",
            "0",
            "0",
            "2200",
            "1600"
        ],
        "200": [
            "300",
            "350",
            "310",
            "0",
            "0",
            "0",
            "2000",
            "1800"
        ],
        "250": [
            "300",
            "350",
            "310",
            "0",
            "0",
            "0",
            "1700",
            "2000"
        ],
        "300": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1450",
            "2200"
        ],
        "350": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "084",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "B788": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2700",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "1700"
        ],
        "150": [
            "275",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2300",
            "1900"
        ],
        "200": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2100",
            "2100"
        ],
        "250": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1700",
            "2200"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1450",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "B789": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2700",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "1700"
        ],
        "150": [
            "275",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2300",
            "1900"
        ],
        "200": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2100",
            "2100"
        ],
        "250": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1700",
            "2200"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1450",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "B78X": {
        "030": [
            "200",
            "230",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "900"
        ],
        "050": [
            "230",
            "250",
            "210",
            "0",
            "0",
            "0",
            "2700",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2500",
            "1700"
        ],
        "150": [
            "275",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2300",
            "1900"
        ],
        "200": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "2100",
            "2100"
        ],
        "250": [
            "300",
            "330",
            "300",
            "0",
            "0",
            "0",
            "1700",
            "2200"
        ],
        "300": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1450",
            "2300"
        ],
        "350": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "1100",
            "2400"
        ],
        "400": [
            "0",
            "0",
            "0",
            "080",
            "084",
            "084",
            "900",
            "2500"
        ]
    },
    "E190": {
        "030": [
            "210",
            "240",
            "160",
            "0",
            "0",
            "0",
            "2800",
            "1000"
        ],
        "050": [
            "250",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2700",
            "1900"
        ],
        "150": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2500",
            "2200"
        ],
        "200": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2000",
            "2600"
        ],
        "300": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1600",
            "2800"
        ],
        "350": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1400",
            "2800"
        ],
        "400": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1000",
            "2800"
        ]
    },
    "E195": {
        "030": [
            "210",
            "240",
            "160",
            "0",
            "0",
            "0",
            "2800",
            "1000"
        ],
        "050": [
            "250",
            "250",
            "210",
            "0",
            "0",
            "0",
            "3000",
            "1500"
        ],
        "100": [
            "250",
            "250",
            "250",
            "0",
            "0",
            "0",
            "2700",
            "1900"
        ],
        "150": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2500",
            "2200"
        ],
        "200": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2200",
            "2400"
        ],
        "250": [
            "290",
            "300",
            "270",
            "0",
            "0",
            "0",
            "2000",
            "2600"
        ],
        "300": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1600",
            "2800"
        ],
        "350": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1400",
            "2800"
        ],
        "400": [
            "0",
            "0",
            "0",
            "072",
            "072",
            "070",
            "1000",
            "2800"
        ]
    }
}