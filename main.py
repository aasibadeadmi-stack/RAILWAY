import os
import time
import logging
import threading
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Simple logger to file
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

progress_data = {}
stop_flags = {}

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
}

# ----------------- Helpers -----------------
def read_tokens_from_form_or_file(form_text, form_file):
    tokens = []
    if form_file and getattr(form_file, "filename", ""):
        tokens = form_file.read().decode("utf-8").splitlines()
    else:
        tokens = form_text.splitlines()
    tokens = [t.strip() for t in tokens if t.strip()]
    if not tokens:
        for fname in ("token.txt", "tokens.txt"):
            if os.path.exists(fname):
                with open(fname, "r", encoding="utf-8") as f:
                    tokens = [l.strip() for l in f.read().splitlines() if l.strip()]
                if tokens:
                    break
    return tokens

def read_messages_from_form_or_file(form_text, form_file):
    msgs = []
    if form_file and getattr(form_file, "filename", ""):
        msgs = form_file.read().decode("utf-8").splitlines()
    else:
        msgs = form_text.splitlines()
    msgs = [m.strip() for m in msgs if m.strip()]
    if not msgs:
        for fname in ("message.txt", "messages.txt", "file.txt"):
            if os.path.exists(fname):
                with open(fname, "r", encoding="utf-8") as f:
                    msgs = [l.strip() for l in f.read().splitlines() if l.strip()]
                if msgs:
                    break
    return msgs

def read_haters_file():
    if os.path.exists("hater.txt"):
        with open("hater.txt", "r", encoding="utf-8") as f:
            return [l.strip().lower() for l in f.read().splitlines() if l.strip()]
    return []

def read_speed_from_timefile():
    # read integer seconds from time.txt; default 60
    try:
        if os.path.exists("time.txt"):
            with open("time.txt", "r", encoding="utf-8") as f:
                txt = f.read().strip()
                return int(txt)
    except:
        pass
    return 60

def contains_hater(msg, haters):
    low = msg.lower()
    return any(bad in low for bad in haters)

# ----------------- Worker (SAFE: prints instead of real API calls) -----------------
def send_messages(task_name, thread_id, auth_list, messages, prefix, speed, mode):
    """
    IMPORTANT: This safe version DOES NOT call Facebook Graph API.
    It simulates sending by printing and logging.
    """
    max_auth = len(auth_list) if auth_list else 1
    idx = 0

    progress_data[task_name] = {"sent": 0, "total": len(messages), "status": "running"}

    while not stop_flags.get(task_name, False):
        for i, msg in enumerate(messages):
            if stop_flags.get(task_name, False):
                progress_data[task_name]["status"] = "stopped"
                return

            auth_index = i % max_auth
            auth_value = auth_list[auth_index] if auth_list else "NO_TOKEN"

            final_text = f"{prefix} {msg}".strip()

            # hater check
            haters = read_haters_file()
            if contains_hater(final_text, haters):
                logging.info(f"[{task_name}] SKIPPED (hater found) -> {final_text}")
                print(f"[{task_name}] SKIPPED (hater) -> {final_text}")
            else:
                # SAFE SEND: print to console + log
                print(f"[{task_name}] (token idx {auth_index}) SEND -> {final_text}")
                logging.info(f"[{task_name}] (token idx {auth_index}) SEND -> {final_text}")
                progress_data[task_name]["sent"] = i + 1

            # wait
            time.sleep(max(1, speed))

        # after completing messages, mark restarting and loop again indefinitely
        progress_data[task_name]["status"] = "restarting"
        print(f"[{task_name}] Completed one cycle — restarting after short pause.")
        time.sleep(2)
        progress_data[task_name]["status"] = "running"

# ----------------- HTML UI (same simple interface) -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Multi Convo Sender (SAFE)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function refreshTasks() {
            fetch('/tasks')
            .then(res => res.json())
            .then(data => {
                let table = document.getElementById("taskTable");
                table.innerHTML = `
                    <tr class="bg-gray-200">
                        <th class="p-2">Task Name</th>
                        <th class="p-2">Progress</th>
                        <th class="p-2">Status</th>
                        <th class="p-2">Action</th>
                    </tr>
                `;
                for (const [task, d] of Object.entries(data)) {
                    table.innerHTML += `
                        <tr>
                            <td class="border p-2">${task}</td>
                            <td class="border p-2">${d.sent} / ${d.total}</td>
                            <td class="border p-2">${d.status}</td>
                            <td class="border p-2">
                                <form action="/stop/${task}" method="post">
                                    <button class="bg-red-500 text-white px-3 py-1 rounded">Stop</button>
                                </form>
                            </td>
                        </tr>
                    `;
                }
            });
        }
        setInterval(refreshTasks, 5000);
        window.onload = refreshTasks;
    </script>
</head>
<body class="bg-gray-100 p-6">
    <h1 class="text-2xl font-bold text-center mb-4">🚀 Multi Convo Sender (SAFE Test)</h1>
    <form method="post" enctype="multipart/form-data" class="bg-white p-6 rounded-xl shadow-md max-w-2xl mx-auto space-y-4">
        <input type="text" name="taskName" placeholder="Task Name (unique)" class="w-full p-2 border rounded" required>
        <input type="text" name="threadId" placeholder="Thread ID (any string)" class="w-full p-2 border rounded" required>
        <input type="text" name="prefix" placeholder="Message Prefix" class="w-full p-2 border rounded">
        <input type="number" name="speed" placeholder="Speed (seconds)" value="60" class="w-full p-2 border rounded">
        <div>
            <label class="font-semibold">Mode:</label>
            <select name="mode" class="w-full p-2 border rounded">
                <option value="token">Access Token</option>
                <option value="cookie">Cookie</option>
            </select>
        </div>
        <div>
            <label class="font-semibold">Tokens / Cookies (one per line):</label>
            <textarea name="auth" rows="4" class="w-full p-2 border rounded"></textarea>
            <input type="file" name="auth_file" class="mt-2">
        </div>
        <div>
            <label class="font-semibold">Messages (one per line):</label>
            <textarea name="messages" rows="4" class="w-full p-2 border rounded"></textarea>
            <input type="file" name="messages_file" class="mt-2">
        </div>
        <button type="submit" class="w-full bg-blue-600 text-white p-2 rounded-lg">Start Sending (SAFE)</button>
    </form>
    <h2 class="text-xl font-bold mt-8 mb-2 text-center">📊 Active Tasks</h2>
    <table id="taskTable" class="w-full max-w-3xl mx-auto bg-white rounded-xl shadow-md"></table>
</body>
</html>
"""

# ----------------- Routes -----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task_name = request.form.get('taskName')
        thread_id = request.form.get('threadId')
        prefix = request.form.get('prefix', "")
        speed_input = int(request.form.get('speed', 60))
        mode = request.form.get('mode', "token")

        # Auth list (form/file/fallback token files)
        auth_text = request.form.get('auth', "")
        auth_file = request.files.get('auth_file')
        auth_list = read_tokens_from_form_or_file(auth_text, auth_file)

        # Messages (form/file/fallback message files)
        messages_text = request.form.get('messages', "")
        messages_file = request.files.get('messages_file')
        messages = read_messages_from_form_or_file(messages_text, messages_file)

        if not task_name:
            return "Task name required!"
        if not auth_list:
            return "No tokens/cookies provided!"
        if not messages:
            return "No messages provided!"

        stop_flags[task_name] = False
        t = threading.Thread(
            target=send_messages,
            args=(task_name, thread_id, auth_list, messages, prefix, speed_input, mode),
            daemon=True
        )
        t.start()

    return render_template_string(HTML_TEMPLATE)

@app.route('/tasks')
def tasks():
    return jsonify(progress_data)

@app.route('/stop/<task_name>', methods=['POST'])
def stop_task(task_name):
    stop_flags[task_name] = True
    if task_name in progress_data:
        del progress_data[task_name]
    return f"Task {task_name} stopped and removed."

if __name__ == "__main__":
    port = int(os.getenv("PORT", "20592"))
    app.run(debug=True, host="0.0.0.0", port=port)
