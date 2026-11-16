"""Optional Flask JSON endpoint following the existing dashboard API pattern."""

from .scope_check import DEFAULT_BENCHMARKS, check_scope, load_scope_json


def create_app(benchmark_path=DEFAULT_BENCHMARKS):
    """Create a local API; Flask is an existing optional dashboard dependency."""
    from flask import Flask, jsonify, request
    from werkzeug.exceptions import HTTPException

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 65536

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({"error": error.name}), error.code

    @app.route("/api/cost-check", methods=["POST"])
    def cost_check():
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
        try:
            scope = load_scope_json(request.get_data())
            return jsonify(check_scope(scope, benchmark_path))
        except FileNotFoundError as error:
            return jsonify({"error": str(error)}), 503
        except (ValueError, UnicodeError) as error:
            return jsonify({"error": str(error)}), 400
        except OSError:
            return jsonify({"error": "benchmark table could not be read"}), 503

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Local scope cost-check JSON API")
    parser.add_argument("--benchmarks", default=DEFAULT_BENCHMARKS)
    parser.add_argument("--port", type=int, default=8080)
    arguments = parser.parse_args()
    create_app(arguments.benchmarks).run(
        host="127.0.0.1", port=arguments.port, debug=False
    )
