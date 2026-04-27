import pytest
from astroq.lk_prediction.incident_resolver import IncidentResolver

def test_detect_incidents_takkar():
    resolver = IncidentResolver()
    # Takkar: H1 hits H8 (as per HOUSE_ASPECT_DATA[1])
    ppos = {"Sun": 1, "Saturn": 8}
    incidents = resolver.detect_incidents(ppos)
    
    # Expecting a Takkar incident for Saturn from Sun
    saturn_incidents = [i for i in incidents if i.target == "Saturn" and i.type == "Takkar"]
    assert len(saturn_incidents) > 0
    assert saturn_incidents[0].source == "Sun"

def test_detect_incidents_sanctuary():
    resolver = IncidentResolver()
    # Sanctuary (Foundation): H1 supports H9
    ppos = {"Sun": 1, "Jupiter": 9}
    incidents = resolver.detect_incidents(ppos)
    
    # Expecting a Sanctuary incident for Jupiter from Sun
    jupiter_incidents = [i for i in incidents if i.target == "Jupiter" and i.type == "Sanctuary"]
    assert len(jupiter_incidents) > 0
    assert jupiter_incidents[0].source == "Sun"
