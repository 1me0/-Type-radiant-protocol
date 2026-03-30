import json

# This acts as the memory for user Presence points
POINT_DB = "user_points.json"

def get_points(user_id):
    try:
        with open(POINT_DB, 'r') as f:
            return json.load(f).get(user_id, 0)
    except FileNotFoundError:
        return 0

def update_points(user_id, new_points):
    data = {}
    try:
        with open(POINT_DB, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass
    data[user_id] = data.get(user_id, 0) + new_points
    with open(POINT_DB, 'w') as f:
        json.dump(data, f)
        
