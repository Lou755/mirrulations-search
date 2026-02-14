import os
from flask import Flask, render_template, request, jsonify
from mirrsearch.internalLogic import internalLogic


def create_app():
    # This is needed due to templates being 2 levels up from this file causing flask not to see it.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    templates_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    @app.route("/")
    def home():
        return render_template('index.html')

    @app.route("/search/")
    def search():
        # Get the search query from URL parameters
        search_input = request.args.get('str')
        
        # If no query parameter provided, use default
        if search_input is None:
            search_input = "example_query"
        
        # Use InternalLogic to process the search
        logic = internalLogic("sample_database")
        results = logic.search(search_input)
        return jsonify(results)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(port=80, debug=True)

