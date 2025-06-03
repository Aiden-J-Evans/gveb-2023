import json
from neo4j import GraphDatabase

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
            if "=" not in line:
                continue
            label, value = line.split("=", 1)
            if not label or not value:
                continue
            
            match label:
                case "NEO4J_URI":
                    uri = value
                case "NEO4J_USERNAME":
                    user = value
                case "NEO4J_PASSWORD":
                    password = value

    if not (uri and user and password):
        return None
    return (uri, user, password)

def upload_line(tx, line_name, coordinates):
    """Creates a TransitLine node and connects it to GeoPoints."""
    tx.run("MERGE (l:TransitLine {name: $line_name})", line_name=line_name)

    for coord in coordinates:
        lon, lat = coord
        tx.run("""
            MATCH (l:TransitLine {name: $line_name})
            CREATE (p:GeoPoint {latitude: $lat, longitude: $lon})
            CREATE (l)-[:HAS_POINT]->(p)
        """, line_name=line_name, lat=lat, lon=lon)

def main():
    db_info = load_db_info(r"dbinfo.txt")
    if not db_info:
        print("db_info not given")
        return

    uri, user, password = db_info
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Load JSON file
    with open(r"rapid-transit-lines.json", "r") as f:
        data = json.load(f)

    # Main logic
    with driver.session() as session:
        for entry in data:
            line_name = entry["line"]
            coordinates = entry["geom"]["geometry"]["coordinates"]
            session.write_transaction(upload_line, line_name, coordinates)

    print("Upload complete.")

if __name__ == "__main__":
    main()
