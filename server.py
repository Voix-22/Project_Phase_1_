from flask import Flask, request, jsonify

app = Flask(__name__)

data_store = {}

@app.route("/update", methods=["POST"])
def update():
    data = request.json
    name = data["name"]
    data_store[name] = data
    return "OK"

@app.route("/view", methods=["GET"])
def view():
    return jsonify(data_store)

if __name__ == "__main__":
    print("🚀 Host Dashboard Running on http://0.0.0.0:5000/view")
    app.run(host="0.0.0.0", port=5000)