from squid_log_viewer import get_squid_data
from flask import Flask, request, jsonify
import traceback

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


@app.route("/", defaults = {'path': ""})
@app.route("/<string:path>")
@app.route("/<path:path>")
def root(path):

    try:

        data = get_squid_data(request.args)

        # Don't let the browser cache response
        response_headers: dict = {
           'Access-Control-Allow-Origin': '*',
           'Cache-Control': 'no-cache, no-store',
           'Pragma': 'no-cache'
        }
        return jsonify(data), response_headers

    except:
        return format(traceback.format_exc()), 500,  {'Content-Type': "text/plain"}


if __name__ == '__main__':
    app.run()
