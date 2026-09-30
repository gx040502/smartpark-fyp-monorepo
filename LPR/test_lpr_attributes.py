import pytest
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from LPR_enter_CAR import parse_car_attributes

def test_standard_format():
    text = "Red - Honda"
    result = parse_car_attributes(text)
    assert result == {"color": "Red", "model": "Honda"}

def test_multi_word_attributes():
    text = "Dark Blue - Mercedes Benz"
    result = parse_car_attributes(text)
    assert result == {"color": "Dark Blue", "model": "Mercedes Benz"}

def test_missing_separator():
    text = "White Toyota"
    result = parse_car_attributes(text)
    assert result == {"color": "Unknown", "model": "White Toyota"}

def test_empty_string():
    text = ""
    result = parse_car_attributes(text)
    assert result == {"color": "Unknown", "model": "Unknown"}
