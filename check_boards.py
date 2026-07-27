import sys, os
sys.path.insert(0, r"C:\Users\Lalithaya\Downloads\skylark-bi-agent")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Lalithaya\Downloads\skylark-bi-agent\.env")
from monday_client import _gql
data = _gql("query { boards(ids: [5030218682,5030218615,5030218330,5030218329]) { id name items_count } }")
for b in data["boards"]:
    count = b["items_count"]
    bid   = b["id"]
    name  = b["name"]
    print(str(count).rjust(5) + " items  " + bid + "  " + name)
