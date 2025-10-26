from flask import Flask, request, jsonify, render_template
import aiohttp, asyncio, json, os

app = Flask(__name__)
DATA_FILE = "apis.json"
PING_INTERVAL = 300
apis_status = {}

def load_apis():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_apis(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

APIS = load_apis()

async def ping_once(session, api):
    url = api["url"]
    for _ in range(2):
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    apis_status[url] = "🟢 OK"
                    return
                else:
                    apis_status[url] = f"🟡 STATUS {resp.status}"
        except:
            apis_status[url] = "🔴 FAIL"
        await asyncio.sleep(1)
    apis_status[url] = "🔴 FAIL"

async def ping_loop():
    while True:
        if not APIS:
            await asyncio.sleep(60)
            continue
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[ping_once(session, api) for api in APIS])
        save_apis(APIS)
        await asyncio.sleep(PING_INTERVAL)

@app.route("/")
def index():
    data = []
    for api in APIS:
        url = api["url"]
        name = api["name"]
        status = apis_status.get(url, "Checking...")
        data.append({"name": name, "status": status})
    return render_template("index.html", apis=data)

@app.route("/addapi", methods=["POST"])
def addapi():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        url = data.get("url", "").strip()
        if not name or not url.startswith("http"):
            return jsonify({"error": "Invalid data"}), 400
        for api in APIS:
            if api["url"] == url:
                return jsonify({"error": "Already exists"}), 400
        APIS.append({"name": name, "url": url})
        save_apis(APIS)
        return jsonify({"success": True, "message": f"Added {name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/status")
def status():
    result = []
    for api in APIS:
        result.append({
            "name": api["name"],
            "status": apis_status.get(api["url"], "⌛ Checking...")
        })
    return jsonify(result)

loop = asyncio.get_event_loop()
loop.create_task(ping_loop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
