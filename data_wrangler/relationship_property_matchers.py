from typing import TypeAlias
from typing import Callable
from typing import Union

from .conversion_functions import Row

RelationPropertyMatcher: TypeAlias = Callable[[Row, Row], Row]
Property = Union[str, tuple[str, str]]

def first_set_prop_match(properties: list[Property]) -> RelationPropertyMatcher:
    """Select properties from the first dataset in a relationship

    Args:
        properties (list[str]): The names of the properties

    Returns:
        RelationPropertyMatcher: The property matcher
    """
    return lambda row1, row2: match_props(row1, properties)

def second_set_prop_match(properties: list[Property]) -> RelationPropertyMatcher:
    """Select properties from the seconds dataset in a relationship

    Args:
        properties (list[str]): The names of the properties

    Returns:
        RelationPropertyMatcher: The property matcher
    """
    return lambda row1, row2: match_props(row2, properties)
    
def dual_set_prop_match(set_1_properties: list[Property], set_2_properties: list[Property]) -> RelationPropertyMatcher:
    """Select properties from both datasets in a relationship

    Args:
        set_1_properties (list[str]): The names of the properties to pull from dataset 1
        set_2_properties (list[str]): The names of the properties to pull from dataset 2

    Returns:
        RelationPropertyMatcher: The property matcher
    """
    return lambda row1, row2: match_props(row1, set_1_properties) | match_props(row2, set_2_properties)

def match_props(row: Row, properties: list[Property]) -> Row:
    """Get the properties from a row, supporting remapping.

    Args:
        row (Row): The row to get the properties from
        properties (list[Property]): List of field names or (new_name, existing_name) mappings

    Returns:
        Row: A dictionary of selected properties
    """
    result = {}
    for prop in properties:
        if isinstance(prop, tuple):
            new_key, source_key = prop
            result[new_key] = row[source_key]
        else:
            result[prop] = row[prop]
    return result