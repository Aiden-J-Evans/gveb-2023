from __future__ import annotations

import csv
from haversine import haversine, Unit

from copy import copy

from itertools import islice

from typing import Callable
from typing import Any
from collections.abc import Sequence

from .conversion_functions import Row
from .conversion_functions import RowFunction
from .conversion_functions import ConversionMap
from .conversion_functions import ConversionFunction

# from deprecated.sphinx import deprecated


class Dataset:
    
    def __init__(self, rows: list[Row], primary_key='id'):
        self.primary_key = primary_key
        
        if len(rows) > 0 and not self.primary_key in rows[0]:
            raise Exception(f"Primary key: {primary_key}, is not a valid key in the dataset")
        
        self._rows = { row[primary_key]: row for row in rows }
        
        
    def __len__(self):
        return len(self._rows)
    
    def __iter__(self):
        return iter(self._rows.values())
    
    def __getitem__(self, index):
        return self._rows[index]
    
    def remove(self, key_value):
        """Remove a row from the dataset

        Args:
            key_value (Any): The primary key of the row to remove
        """
        del self._rows[key_value]
    
    def set_primary_key(self, primary_key: str):
        """Set the primary key of this dataset
        
        If the values of the primary key property are not unique some data will be lost

        Args:
            primary_key (str): The name of the property that will become the primary key
        """
        self.primary_key = primary_key
        self._rows = { row[self.primary_key]: row for row in self._rows.values() }
    
    def add_property(self, name: str, **kwargs):
        """Add a property to each row of the dataset
        
        Either value or func should be set. If neither is set default will be 0.

        Args:
            name (str): The name of the new property
        Kwargs:
            value (Any): The default value of the property
            func (Callable[[Row], Any]): The function to generate values. Is given the row
        """
        
        if name in self.get_column_names():
            raise Exception(f"Cannot add property {name} because it already exists in the dataset.")
            
        if "value" in kwargs:  
            for row in self:
                row[name] = copy(kwargs["value"])
        elif "func" in kwargs:
            for row in self:
                row[name] = kwargs["func"](row)
        else:
            for row in self:
                row[name] = 0
    
    def drop(self, property_name: str):
        """Remove a property from the dataset

        Args:
            property_name (str): The propery to remove
        """
        for row in self:
            del row[property_name]
    
    def get_single_row(self) -> Row | None:
        """Get the first row in the dataset

        Returns:
            Row | None: The first row. None if there are no rows.
        """
        if len(self) == 0: return None
        return next(iter(self))
    
    def get_rows(self, row_count):
        """Get the first [row_count] rows from the dataset
        
        If [row_count] is greater than the number of rows then all the rows in the dataset are returned.

        Args:
            row_count (int): The number of rows to get

        Returns:
            iterator: An iterator over the rows
        """
        return islice(self, row_count)
    
    def rename(self, original_name: str, new_name: str):
        if new_name != original_name and new_name in self.get_column_names():
            raise Exception(f"Cannot rename property {original_name} to {new_name} because {new_name} already exists in the dataset")
        
        # TODO: Make sure this is right
        if original_name == self.primary_key:
            self.primary_key = new_name
        
        for row in self:
            row[new_name] = row[original_name]
            del row[original_name]
            
    def convert_property(self, field_name: str, conversion: ConversionFunction):
        """Apply a conversion function to a property
        
        Useful to change the type of a property
        eg: dataset.convert_property('some_property', int) to convert the type of 'some_property' to int

        Args:
            field_name (str): The name of the property to convert
            conversion (ConversionFunction): The function to apply
        """
        for row in self:
            row[field_name] = conversion(row[field_name])
            
        if field_name == self.primary_key:
            new_rows = { row[self.primary_key]: row for row in self._rows.values() }
            
            if len(new_rows) != len(self._rows):
                raise Exception("Conversion resulted in non unique primary key")
            self._rows = new_rows
            self.convert_properties({})
            
    # @deprecated(reason="Use convert_property for each property instead", version="0.0.1")
    def convert_properties(self, conversions: dict[str, ConversionFunction]):
        for row in self:
            for field_name in conversions:
                row[field_name] = conversions[field_name](row[field_name])
                
        if self.primary_key in conversions:
            self._rows = { row[self.primary_key]: row for row in self._rows.values() }
            
    def match_closest(self, other_data: Dataset, distance_func: Callable[[Row, Row], float], on_match: Callable[[Row, Row, float], None], distance_limit: float=float('inf')):
        """ Pair all the nodes in one data set to the closest node in another dataset
        
        !WARNING: Creates a cross product between the two data sets. May run slowly for large datasets.

        Args:
            other_data (Dataset): The set of nodes to match this dataset to
            distance_func (Callable[[Row, Row], float]): The function to use for calculating distance between two rows
            on_match (Callable[[Row, Row, float], None]): The function to run when a row is matched with its closest row
            distance_limit (float): The maximum distance beyond which a match should not be made
        """
        
        # Match for each node in this dataset
        for i, row_1 in enumerate(self):
            closest = None
            b_dist = distance_limit
            
            # Find the closest node in data set 2
            for row_2 in other_data:
                distance = distance_func(row_1, row_2)
                    
                # Update the closest node
                if distance < b_dist:
                    closest = row_2
                    b_dist = distance
              
            # Write the information about the closest node to [row_1]
            if closest != None:
                on_match(row_1, closest, b_dist)
            
            # Log the progress
            if i % 100 == 0:
                print(f"\r    Matched {i} nodes. {(i / len(self)):.0%} {' ' * 10}", end='')
        print(f"\r    Matched {len(self)} nodes. 100% {' ' * 10}")
        
    def match_closest_p_norm(
        self, other_data: Dataset, match_keys: list[str | tuple[str, str]], on_match: Callable[[Row, Row, float], None], p_norm: float=2, distance_limit: float=float('inf')
    ):
        """ Pair all the nodes in one data set to the closest node in another dataset
        
        match_keys is used to select the properties used for finding the distance. The dimension used is the number of match_keys.
        eg: If there is one match key then one dimensional distance is used. If there are four, then four dimensional distance is used.
        
        !WARNING: Creates a cross product between the two data sets. May run slowly for large datasets.

        Args:
            other_data (Dataset): The set of nodes used for finding the closest node
            match_keys (list[str | tuple(str, str)]): The fieldnames to use for distance. eg: ["latitude", "longitude"]
            on_match (Callable[[Row, Row, float], None]): The function to run when a row is matched with its closest row
            p_norm (float, optional): The p_norm function to use for calculating distance. Defaults to 2 (Euclidean distance)
            distance_limit (float): The maximum distance beyond which a match should not be made
        """
        def distance(row_1: Row, row_2: Row) -> float:
            distance = 0
            for key in match_keys:
                if type(key) == tuple:
                    delta = row_1[key[0]] - row_2[key[1]]
                else:
                    delta = row_1[key] - row_2[key]              # type: ignore  # Ignoring type because it should be str
                distance += pow(abs(delta), p_norm)
            return pow(distance, 1/p_norm)
        
        self.match_closest(other_data, distance, on_match)
        
    def match_lat_lng(self, other_data: Dataset, match_field: str, dst_field:str, count_field: str = '', distance_limit=float('inf'), count_attrib='', reset_count=True):
        """ Pair all the rows in this dataset with the closest row in [other_data] based on latitude and longitude.
        
        The haversine formula is used to calculate distance in meters from latitude and longitude

        Args:
            other_data (Dataset): The data to match to
            match_field (str): The name of the field in which to store the primary key of the other row of the match
            dst_field (str): The name of the field in which to store the distance of the match
            distance_limit (float): The maximum distance beyond which a match should not be made
        """
        
        if count_field:
            for row in other_data:
                if not reset_count:
                    row[count_field] = row.get(count_field, 0)
                else:
                    row[count_field] = 0
                
        for row in self:
            row[match_field] = 0
            row[dst_field] = 0
        
        def on_match(row_1, row_2, dst):
            row_1[match_field] = row_2[other_data.primary_key]
            row_1[dst_field] = dst
            
            increment = 1
            if count_attrib:
                increment = row_1[count_attrib]
            
            if count_field:
                row_2[count_field] = row_2[count_field] + increment
            
        def distance(row_1: Row, row_2: Row):
            p1 = (row_1['latitude'], row_1['longitude'])
            p2 = (row_2['latitude'], row_2['longitude'])
            
            return haversine(p1, p2, unit=Unit.METERS)
        
        self.match_closest(other_data, distance, on_match, distance_limit=distance_limit)
        
    def match_lat_lng_custom(self, other_data: Dataset, on_match, distance_limit=float('inf')):
        def distance(row_1: Row, row_2: Row):
            p1 = (row_1['latitude'], row_1['longitude'])
            p2 = (row_2['latitude'], row_2['longitude'])
            
            return haversine(p1, p2, unit=Unit.METERS)
        
        self.match_closest(other_data, distance, on_match, distance_limit=distance_limit)
        
    def get_column_names(self):
        """Get the names of the columns in the dataset
        
        The primary key is always the virst value

        Returns:
            list[str]: The column names
        """
        if len(self) == 0: return []
        fieldnames =  [key for key in self.get_single_row()]  # type: ignore  # We know it's not None because we checked in the first line
        
        # Make sure the primary key is the first one in the list
        if fieldnames[0] != self.primary_key:
            fieldnames.remove(self.primary_key)
            fieldnames.insert(0, self.primary_key)
        return fieldnames
    
    def merge(self, other: Dataset):
        """Merge two datasets
        
        The two datasets must have the same columns and primary key

        Args:
            other (Dataset): The dataset to merge into this one
        """
        
        if self.primary_key != other.primary_key:
            raise Exception("Cannot merge datasets with different primary keys")
        if self.get_column_names() != other.get_column_names():
            raise Exception("Cannot merge datasets with different columns")
            
        self._rows.update(other._rows)
        
    def filter(self, filter: Callable[[Row], bool]):
        """Filter rows from the dataset
        
        The filter function is run for each of the rows. If it returns False the row is removed from the dataset.

        Args:
            filter (Callable[[Row], bool]): The filter function
        """
        toDelete = []
        for row in self:
            if not filter(row):
                toDelete.append(row)
        for row in toDelete: 
            del self._rows[row[self.primary_key]]
        
    def write_to_file(self, filename: str, delimiter: str = ',', columnnames=None, write_header = True):
        """ Write the dataset to a csv file

        Args:
            filename (str): The name of the csv file
            delimiter (str, optional): The delimiter to use for separating values. Defaults to ','.
            fieldnames (list[str], optional): The fieldnames to write. If not provided then writes all values.
            write_header (bool, optional): Whether or not the header should be written. Defaults to True.
        """
        if len(self) == 0:
            print("No data to write!")
            return
        
        if columnnames == None:
            columnnames = self.get_column_names()
        
        with open(filename, 'w+', newline='', encoding='utf-8-sig') as out_file:
            writer = csv.DictWriter(out_file, fieldnames=columnnames, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
            
            if write_header:
                writer.writeheader()
                
            writer.writerows(self._rows.values())
    
    @staticmethod
    def cross_data(data_1: Dataset, data_2: Dataset, func: Callable[[Row, Row], None]):
        """ Run a function on the cross product of two data sets
        
        !WARNING: Creates a cross product between the two data sets. May run slowly for large datasets.
        
        Useful for computing something based on the combination of two data sets. eg. matching nodes
        [func] will receive every combination of pairs of rows with 1 row from data set 1 and 1 row from data set 2

        Args:
            data_1 (Dataset): The first data set
            data_2 (Dataset): The second data set
            func (Callable[[Row, Row], None]): The function to run on the cross product of the data sets
        """
        for row_1 in data_1:
            for row_2 in data_2:
                func(row_1, row_2)
    
    @staticmethod
    def load_file(filename: str, conversion_map: ConversionMap | None = None, primary_key='id', delimiter: str =',', fieldnames: Sequence[str] | None=None, has_header=True, primary_key_start=0):
        """Load data from a csv file
        
        WARNING: conversion_map is deprecated. Don't use conversion_map instead use conver_property() and rename_property()
        
        [conversion_map] is used to manipulate the read data in order to turn it into more useful formats and types. A ConversionMap is a dictionary
        mapping fieldnames to either a function on one parameter, a tuple containing a function on one parameter and a fieldname, or a RowFunction.
        The result of the function is stored in the data using the first fieldname.
        
        Example::
        
            {
                "id": int,
                "name": (str, "Name"),
                "indexName": RowFunction(lambda row, i: str(i) + str(row["Name"]))
            }
        
        The value matched to "id" in the input is passed to int and stored in "id" in the output.
        The value matched to "Name" in the input is passed to str and stored in "name" in the output.
        The row and an index value is passed to the lambda function which joins the index with the "Name" attribute of the input, and the result is
        stored in "indexName" of the output.

        Args:
            filename (str): The name of the file to load. Should be a csv file.
            conversion_map (ConversionMap, optional): A mapping between fieldnames in the output data and a function on the input data. If not provided then all values are loaded as strings.
            delimiter (str, optional): The delimiter used by the csv file. Defaults to ','.
            fieldnames (Sequence[str] | None): The names to use for the fields. Defaults to None.
            has_header (boolean): Whether or not there is a header row in the file. Must be true if fieldnames is None.

        Returns:
            RowData: The loaded data
        """        
        
        # Make sure there is fieldname information somewhere
        if (fieldnames == None and not has_header):
            raise Exception("If fieldnames is None then has_header must be True")
        
        # Open the file
        with open(filename, 'r', encoding='utf-8-sig') as input_file:
            data = []
            
            # Read each row of the file
            rows = csv.DictReader(input_file, quoting=csv.QUOTE_MINIMAL, delimiter=delimiter, fieldnames=fieldnames)
            # Read the header if necessary
            if(fieldnames != None and has_header):
                next(rows)
            
            if conversion_map != None:
                # Make all conversions using IndexedConversionMap
                conversions, required_fieldnames = Dataset._fix_conversion(conversion_map)
                
                for req_name in required_fieldnames:
                    if req_name not in rows.fieldnames:
                        print(f"{req_name} is not a valid fieldname. The availiable fieldnames are {rows.fieldnames}")
                
                # Read each row
                for i, row in enumerate(rows):
                    # Apply the conversion to the row to get a result
                    result = { key: conversions[key](row, i) for key in conversions }
                    
                    if primary_key not in result:
                        result[primary_key] = i + primary_key_start
                    
                    data.append(result)
            else:
                data = list(rows)
                
                # Generate a primary key if it is not in the data
                if len(data) > 0 and primary_key not in data[0]:
                    for i, row in enumerate(data):
                        row[primary_key] = i + primary_key_start
                
            return Dataset(data, primary_key)
        
    @staticmethod
    def _fix_conversion(conversions: ConversionMap) -> tuple[dict[str, Callable[[Row, int], Any]], list[str]]:
        """Modify a ConversionMap to only use IndexedConversionFunctions   

        Args:
            conversions (ConversionMap): The conversion map to fix

        Returns:
            tuple: 
                dict[str, Callable[[Row, int], Any]]: The fixed conversion map
                list[str]: The required fieldnames
        """
        
        result = {}
        required_fieldnames = []
        
        for key, conv in conversions.items():
            if isinstance(conv, tuple):
                func, fieldname = conv  # Unpack the tuple (function, key_in)
                required_fieldnames.append(fieldname)
                # Wrap func so it uses row[fieldname], avoiding late binding issues
                result[key] = (lambda func, fn: 
                    lambda row, index: func(row[fn]) if fn in row else None
                )(func, fieldname)
            
            elif isinstance(conv, RowFunction):
                # Assuming RowFunction has attribute 'f' that is the function
                result[key] = conv.f  # type: ignore
            
            else:
                # conv is a direct function; key is the fieldname to use
                required_fieldnames.append(key)
                # Wrap conv to use row[key], with a check for existence
                result[key] = (lambda func, fn: 
                    lambda row, index: func(row[fn]) if fn in row else None
                )(conv, key)
        
        return result, required_fieldnames
