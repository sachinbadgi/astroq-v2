import pytest
from astroq.lk_prediction.tracer import GraphTracer

def test_tracer_captures_hits():
    tracer = GraphTracer()
    
    with tracer:
        tracer.hit("node_1")
        tracer.hit("node_2")
    
    assert tracer.hits == ["node_1", "node_2"]

def test_tracer_nested_hits():
    tracer = GraphTracer()
    
    with tracer:
        tracer.hit("outer")
        with tracer:
            tracer.hit("inner")
        tracer.hit("outer_again")
    
    # Depending on implementation, we might want unique hits or full trace.
    # Let's assume full trace for now.
    assert tracer.hits == ["outer", "inner", "outer_again"]
