import json
import os

path = "data/processed/structured_problem.json"
if os.path.exists(path):
    with open(path, "r") as f:
        data = json.load(f)
        genova_cost = data['cost_matrix']['GENOVA']['GENOVA']
        print(f"Cost GENOVA->GENOVA is: {repr(genova_cost)}, Type: {type(genova_cost)}")
else:
    print(f"File {path} does not exist.")
