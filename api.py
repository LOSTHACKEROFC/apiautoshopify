from flask import Flask, request, jsonify
from autoshopify import main as autoshopify_main  # uses your real logic

app = Flask(__name__)

@app.route('/check', methods=['GET'])
def check_card():
    domain = request.args.get('domain')
    fullz = request.args.get('fullz')

    if not domain or not fullz:
        return jsonify({"error": "Missing ?domain= and/or ?fullz="}), 400

    try:
        result = autoshopify_main(domain, fullz)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
