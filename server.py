from flask import Flask, request, jsonify, render_template_string
import aiohttp, asyncio, json, os

app = Flask(__name__)
DATA_FILE = "apis.json"
PING_INTERVAL = 300
apis_status = {}

def load_apis():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

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
            apis_status[url] = "🔴 DOWN"
        await asyncio.sleep(1)
    apis_status[url] = "🔴 DOWN"

async def ping_loop():
    await asyncio.sleep(3)
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
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>No1.Hub — API Status</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {
          font-family: "Poppins", sans-serif;
          background: linear-gradient(135deg, #000428, #004e92);
          color: #fff;
          text-align: center;
          margin: 0;
          padding: 0;
          min-height: 100vh;
        }
        h1 {
          margin-top: 30px;
          font-size: 2.3em;
          text-shadow: 0 0 10px cyan;
        }
        table {
          width: 70%;
          margin: 40px auto;
          border-collapse: collapse;
          background: rgba(255,255,255,0.05);
          border-radius: 12px;
          overflow: hidden;
        }
        th, td {
          padding: 14px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { background: rgba(255,255,255,0.15); }
        tr:hover { background: rgba(255,255,255,0.08); }
        td:first-child { font-weight: bold; }
        footer {
          margin-top: 50px;
          font-size: 0.9em;
          opacity: 0.7;
        }
      </style>
    </head>
    <body>
      <h1>No1.Hub — API Status</h1>
      <table>
        <thead>
          <tr><th>API Name</th><th>Status</th></tr>
        </thead>
        <tbody id="apiTable">
        </tbody>
      </table>
      <footer>No1.Hub | Api Status</footer>
      <script>
        async function refreshStatus() {
          try {
            const res = await fetch("/status");
            const data = await res.json();
            const table = document.getElementById("apiTable");
            table.innerHTML = "";
            if (data.length === 0) {
              table.innerHTML = "<tr><td colspan='2'>No API Added</td></tr>";
              return;
            }
            data.forEach(api => {
              const row = document.createElement("tr");
              row.innerHTML = `<td>${api.name}</td><td>${api.status}</td>`;
              table.appendChild(row);
            });
          } catch {
            document.getElementById("apiTable").innerHTML = "<tr><td colspan='2'>Error loading status</td></tr>";
          }
        }
        refreshStatus();
        setInterval(refreshStatus, 10000);
      </script>
    </body>
    </html>
    """
    return render_template_string(html)

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
            "status": apis_status.get(api["url"], "Checking...")
        })
    return jsonify(result)

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ping_loop())

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    import threading
    threading.Thread(target=start_background_loop, args=(loop,), daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
