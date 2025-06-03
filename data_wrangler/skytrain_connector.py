import json
from neo4j import GraphDatabase


# Tolerance for lat/lon matching
EPSILON = 0.0085

def find_station(tx, lat, lon):
    query = """
    MATCH (s:RapidTransit)
    WHERE abs(s.latitude - $lat) < $eps AND abs(s.longitude - $lon) < $eps
    RETURN s.latitude AS lat, s.longitude AS lon
    LIMIT 1
    """
    result = tx.run(query, lat=lat, lon=lon, eps=EPSILON)
    record = result.single()
    if record:
        print(f"Matched station at lat={record['lat']}, lon={record['lon']}")
        return {'lat': record['lat'], 'lon': record['lon']}
    else:
        print(f"No station match for lat={lat}, lon={lon}")
        return None

def create_relationship(tx, start, end, line_name):
    query = """
    MATCH (a:RapidTransit {latitude: $lat1, longitude: $lon1})
    MATCH (b:RapidTransit {latitude: $lat2, longitude: $lon2})
    MERGE (a)-[:CONNECTED_TO {line: $line}]->(b)
    MERGE (b)-[:CONNECTED_TO {line: $line}]->(a)
    """
    tx.run(query, lat1=start['lat'], lon1=start['lon'],
                  lat2=end['lat'], lon2=end['lon'],
                  line=line_name)


def load_db_info(filepath):
    """ Load database access information from a file
    
    The file should be one downloaded from Neo4j when creating a database
    
    Parameters:
        filepath - String: The path to the file

    Returns:
        (uri, username, password): The access information if the file is valid
        None: When the information cannot be loaded
    """
    
    uri, user, password = None, None, None
    with open(filepath, 'r') as dbinfo:
        for line in dbinfo:
            line = line.strip()
            
            # Skip lines that don't have information or where it would be invalid
            if not "=" in line: continue
            label, value = line.split("=")
            if len(label) == 0 or len(value) == 0: continue
            
            # Set the variable that corresponds with the label
            match label:
                case "NEO4J_URI":
                    uri = value
                case "NEO4J_USERNAME":
                    user = value
                case "NEO4J_PASSWORD":
                    password = value
                
    print(uri)    
    if not (uri and user and password): return None
    return (uri, user, password)

def delete_line_relationships(tx, line_name):
    query = """
    MATCH (:RapidTransit)-[r:CONNECTED_TO]->(:RapidTransit)
    WHERE r.line = $line
    DELETE r
    """
    tx.run(query, line=line_name)

def main():
    db_info = load_db_info(r"dbinfo.txt")
    if not db_info: 
        print("db_info not given")
        return
    uri, user, password = db_info
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with open(r'data/original_data/rapid-transit-lines.json') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} lines from JSON")
    with driver.session() as session:
        for line in data:
            line_name = line['line']
            coords = line['geom']['geometry']['coordinates']
            print(f"\nProcessing line: {line_name} with {len(coords)} coordinates")

            session.write_transaction(delete_line_relationships, line_name)

            matched_stations = []
            for coord in coords:
                lon, lat = coord[0], coord[1]
                station = session.read_transaction(find_station, lat, lon)
                matched_stations.append(station)

            created_count = 0
            # Create relationships between consecutive matched stations
            for i in range(len(matched_stations) - 1):
                start = matched_stations[i]
                end = matched_stations[i+1]
                if start is not None and end is not None:
                    # Skip if both points are the same station
                    if start['lat'] == end['lat'] and start['lon'] == end['lon']:
                        continue
                    session.write_transaction(create_relationship, start, end, line_name)
                    created_count += 1
            print(f"Created {created_count} relationships for {line_name}")

    driver.close()
    print("Neo4j session closed.")

if __name__ == "__main__":
    main()