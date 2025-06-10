from flask import Flask, request, jsonify
import asyncio
from apisites.autoshop import find_product, autoshopify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/auto.php')
def auto_checkout():
    domain = request.args.get('domain')
    fullz = request.args.get('fullz')

    if not domain or not fullz:
        return jsonify({"error": "Missing ?domain= and ?fullz="}), 400

    try:
        cc_parts = fullz.strip().split('|')
        if len(cc_parts) != 4:
            return jsonify({"error": "Invalid card format. Use CC|MM|YYYY|CVV"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid card input: {str(e)}"}), 400

    async def runner():
        max_retries = 3
        attempt = 0
        while attempt < max_retries:
            try:
                logging.info(f"Attempt {attempt + 1} to fetch product and checkout.")
                product = await find_product(domain)
                if not product:
                    return {"error": "No valid product found."}

                p_id, link = product
                result = await autoshopify(None, link, fullz)
                return {
                    "card": fullz,
                    "domain": domain,
                    "status": "Success" if "charged" in str(result).lower() or "order" in str(result).lower() else "Failed",
                    "response": result or "No response"
                }
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1
                await asyncio.sleep(2)

        return {"error": "All attempts failed. Try another site or card."}

    output = asyncio.run(runner())
    return jsonify(output)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
