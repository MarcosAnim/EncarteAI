import requests

url = "http://127.0.0.1:5000/produtos/buscar"
params = {
    "q": "carne suina",
    "limit": 10,
    "min_similarity": 0.25
}
r = requests.get(url, params=params, timeout=5)
r.raise_for_status()
data = r.json()
print(data)
