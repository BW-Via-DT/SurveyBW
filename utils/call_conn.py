import json
import os

def get_db_connection():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'connections', 'settings.json')
    
    with open(config_path, 'r') as file:
        config = json.load(file)
    
    connection_string = config[0].get('connection_string', '')
    return connection_string