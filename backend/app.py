from flask import Flask, send_from_directory
from flask_cors import CORS
from config import Config
from models import db
from api import api
from generate_demo_graph import main as seed_demo_graph
import os
import sys
from pathlib import Path


def frontend_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'frontend_dist'
    return Path(__file__).resolve().parent.parent / 'frontend' / 'dist'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    db.init_app(app)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    app.register_blueprint(api, url_prefix='/api')
    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def index():
        return send_from_directory(frontend_directory(), 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        frontend_path = frontend_directory()
        if (frontend_path / path).is_file():
            return send_from_directory(frontend_path, path)
        # BrowserRouter routes must fall back to the SPA entrypoint.
        return send_from_directory(frontend_path, 'index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        # An older EXE may have already copied a database containing clauses
        # but no graph data.  Populate the safe local demonstration graph once
        # instead of requiring the user to delete their local database.
        from models import Entity
        if getattr(sys, 'frozen', False) and Entity.query.count() == 0:
            seed_demo_graph()
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '5000')),
        debug=not getattr(sys, 'frozen', False)
    )
