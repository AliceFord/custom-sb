TURN_RATE = 2  # deg / sec
TAXI_SPEED = 15  # knots
PUSH_SPEED = 5  # knots
CLIMB_RATE = 2000  # ft / min
DESCENT_RATE = -2000  # ft / min

CCAMS_SQUAWKS = list(range(1410, 1478)) + list(range(2001, 2078)) + list(range(2201, 2278)) + list(range(2701, 2738))  # realistically way way more

ACTIVE_AERODROME = "EGKK"
ACTIVE_RUNWAY = "26L"
ACTIVE_CONTROLLER = "LON_M_CTR"
MASTER_CONTROLLER = "LON_CTR"
MASTER_CONTROLLER_FREQ = "27830"

INACTIVE_SECTORS = [
    "LTC_M_CTR",
    "MAN_SE_CTR"
]

# OTHER_CONTROLLERS = []
OTHER_CONTROLLERS = [
    ("LON_W_CTR", "26080"),
    ("LON_E_CTR", "18480"),
#    ("LON_M_CTR", "20025")
    ("LON_D_CTR", "34905"),
    ("LON_NW_CTR", "35580"),
    ("LON_NE_CTR", "28130"),
    ("LON_S_CTR", "29430"),

    ("LTC_E_CTR", "21230"),
#    ("LTC_M_CTR", "21030"),
    ("LTC_NE_CTR", "18825"),
    ("LTC_NW_CTR", "21280"),
    ("LTC_SE_CTR", "20530"),
    ("LTC_SW_CTR", "33180"),

    ("MAN_NE_CTR", "35715"),
#    ("MAN_SE_CTR", "34430"),
    ("MAN_W_CTR", "28055"),

    ("SCO_D_CTR", "35855"),
    ("SCO_N_CTR", "29225"),
    ("SCO_R_CTR", "29100"),
    ("SCO_S_CTR", "34755"),
    ("SCO_W_CTR", "32730"),

    ("STC_A_CTR", "23775"),
    ("STC_W_CTR", "24825"),
    ("STC_E_CTR", "30975")
]
# ACTIVE_CONTROLLER = "LON_S_CTR"
# MASTER_CONTROLLER = "EGLL_N_APP"
# MASTER_CONTROLLER_FREQ = "19730"
