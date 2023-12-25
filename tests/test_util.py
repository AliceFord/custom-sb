
import regex as re


def test_callsignGen():
    from util import callsignGen
    assert callsignGen() != callsignGen()
    assert re.match(r"[A-Z]{3}[0-9]{2}[A-Z]{2}", callsignGen()) is not None


def test_squawkGen():
    from util import squawkGen
    from Constants import CCAMS_SQUAWKS
    assert squawkGen() != squawkGen()
    assert squawkGen() in CCAMS_SQUAWKS


def test_modeConverter():
    from PlaneMode import PlaneMode
    from util import modeConverter
    assert modeConverter(PlaneMode.GROUND_STATIONARY) == "Stationary"
    assert modeConverter(PlaneMode.GROUND_READY) == "Ready"
    assert modeConverter(PlaneMode.GROUND_TAXI) == "Taxiing"
    assert modeConverter(PlaneMode.FLIGHTPLAN) == "Flightplan"
    assert modeConverter(PlaneMode.HEADING) == "Heading"
    assert modeConverter(PlaneMode.ILS) == "ILS"
    assert modeConverter(PlaneMode.NONE) == "Error"
    assert modeConverter("hi") == "hi"
