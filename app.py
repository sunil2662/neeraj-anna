

from flask import Flask, request

app = Flask(__name__)

@app.route('/api/machine_status', methods=['POST'])
def machine_status():
    data = request.get_json()  # Assumes data is sent as JSON
    print("Received Data:", data)
    return "Data received and printed in the console", 200


if __name__ == '__main__':
    app.run(host='192.168.9.106', port=5000, debug=True)
