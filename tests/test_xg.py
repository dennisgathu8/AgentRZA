import pytest
from src.tools.enrich import XGModel

def test_xg_model_bounds():
    """
    Ensures the Logistic Regression spatial xG model NEVER outputs probabilities 
    below 0.0 or above 1.0, preserving strict zero-trust analytic principles.
    """
    model = XGModel()
    
    # Test tap in
    tap_in = model.predict_xg(118.0, 40.0)
    assert 0.0 <= tap_in <= 1.0, f"Expected 0<=xg<=1, got {tap_in}"
    
    # Test half-way line
    long_shot = model.predict_xg(60.0, 40.0)
    assert 0.0 <= long_shot <= 1.0, f"Expected 0<=xg<=1, got {long_shot}"
    assert tap_in > long_shot, "A tap in should strictly have a higher xG than a half-way line shot."

def test_xg_angle_math():
    model = XGModel()
    # Dead center
    dist, angle = model._calculate_distance_and_angle(110.0, 40.0)
    assert dist == 10.0
    assert angle > 0.0
    
    # Far corner flag (angle to goal should be extremely acute)
    dist2, corner_angle = model._calculate_distance_and_angle(120.0, 0.0)
    assert corner_angle < angle, "Corner flag should have tighter angle than central box."
