import os
from flask import Flask, render_template, request, jsonify
from mirrsearch.internal_logic import InternalLogic


def create_app():
    # This is needed due to templates being 2 levels up from this file causing flask not to see it.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    templates_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    flask_app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    @flask_app.route("/")
    def home():
        return render_template('index.html')

    @flask_app.route("/search/")
    def search():
        search_input = request.args.get('str')
        filter_param = request.args.get('filter')  # e.g. /search/?str=renal&filter=Proposed Rule

        if search_input is None:
           search_input = "example_query"

        logic = InternalLogic("sample_database")
        results = logic.search(search_input, filter_param)
        return jsonify(results)

    return flask_app

app = create_app()

if __name__ == '__main__':
    app.run(port=80, debug=True)
