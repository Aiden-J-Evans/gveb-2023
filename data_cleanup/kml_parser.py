import xml.etree.ElementTree as ET
import csv
import re
import sys

sys.path.append("../")
# Define file paths
kml_file = "data/original_data/Skytrain Network Map.kml"
stations_csv = "data/stations.csv"
lines_csv = "data/line_coordinates.csv"

def parse_kml_to_csv(kml_file, stations_csv, lines_csv):
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Detect namespace (if any)
    namespace_match = re.match(r'\{.*\}', root.tag)
    ns = {'kml': namespace_match.group(0)[1:-1]} if namespace_match else {}

    def findall(elem, path):
        return elem.findall(path, ns) if ns else elem.findall(path)

    with open(stations_csv, 'w', newline='', encoding='utf-8') as station_file, \
         open(lines_csv, 'w', newline='', encoding='utf-8') as line_file:

        station_writer = csv.writer(station_file)
        line_writer = csv.writer(line_file)

        station_writer.writerow(['id', 'line_name', 'longitude', 'latitude'])
        line_writer.writerow(['name', 'longitude', 'latitude'])

        for folder in findall(root, './/kml:Folder' if ns else './/Folder'):
            folder_name_elem = folder.find('kml:name', ns) if ns else folder.find('name')
            folder_name = folder_name_elem.text if folder_name_elem is not None else 'Unknown'

            for placemark in findall(folder, 'kml:Placemark' if ns else 'Placemark'):
                name = placemark.findtext('kml:name', default='Unnamed', namespaces=ns)
                description = placemark.findtext('kml:description', default='', namespaces=ns)

                point = placemark.find('kml:Point', ns) if ns else placemark.find('Point')
                linestring = placemark.find('kml:LineString', ns) if ns else placemark.find('LineString')

                if point is not None:
                    coord_text = point.findtext('kml:coordinates', namespaces=ns) if ns else point.findtext('coordinates')
                    if coord_text:
                        lon, lat, *_ = coord_text.strip().split(',')

                        # Clean HTML tags from description
                        clean_desc = re.sub(r'<.*?>', '', description)

                        # Try splitting station name and lines if there's a comma
                        if ',' in clean_desc:
                            try:
                                station_name_part, line_description = clean_desc.split(',', 1)
                            except ValueError:
                                # fallback if split fails
                                line_description = clean_desc
                        else:
                            line_description = clean_desc

                        # Extract line names with regex: grab phrases ending with 'Line' before 'on Platforms' or EOL
                        line_names = re.findall(r'([\w\s\-]+Line)(?=\s+on Platforms|$)', line_description)

                        # Clean whitespace
                        line_names = [ln.strip() for ln in line_names]

                        # Fallback if no line names found
                        if not line_names:
                            line_names = ['Unknown']

                        for line in line_names:
                            station_writer.writerow([name, line, lon, lat])


                elif linestring is not None :
                    coord_text = linestring.findtext('kml:coordinates', namespaces=ns) if ns else linestring.findtext('coordinates')
                    if coord_text:
                        coords = coord_text.strip().split()
                        for coord in coords:
                            lon, lat, *_ = coord.strip().split(',')
                            line_writer.writerow([name, lon, lat])

# Run the conversion
parse_kml_to_csv(kml_file, stations_csv, lines_csv)

