import json

with open("output/opinion_graph_10592_Thu Sep  4 16:21:26 2025.json",'r') as f:
    opinion_graph = json.load(f)

with open("output/opinion_graph_10592_Thu Sep  4 16:21:26 2025.json","w") as f:
    json.dump(opinion_graph,f,indent=4,ensure_ascii=False)
