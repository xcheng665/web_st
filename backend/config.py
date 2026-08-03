import os
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
IS_FROZEN = getattr(sys, 'frozen', False)
IS_VERCEL = bool(os.environ.get('VERCEL'))
BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', BASE_DIR))
if IS_FROZEN:
    default_runtime = Path(os.environ.get('LOCALAPPDATA', BASE_DIR)) / 'BuildingCodeKnowledgeModel'
elif IS_VERCEL:
    default_runtime = Path('/tmp') / 'BuildingCodeKnowledgeModel'
else:
    default_runtime = BASE_DIR
RUNTIME_DIR = Path(os.environ.get('APP_DATA_DIR', default_runtime))
load_dotenv(RUNTIME_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # Local/EXE mode keeps SQLite. Deployments can set DATABASE_URL to MySQL.
    # Example: mysql+pymysql://building_code:password@mysql:3306/building_code?charset=utf8mb4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{RUNTIME_DIR}/instance/specifications.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(RUNTIME_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf', 'docx'}
    # Any OpenAI-compatible provider can be used (OpenAI, DeepSeek, DashScope
    # compatible endpoint, private gateway, etc.).  Keep secrets in .env.
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
    LLM_TIMEOUT_SECONDS = int(os.environ.get('LLM_TIMEOUT_SECONDS', '90'))
    
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        instance_dir = RUNTIME_DIR / 'instance'
        instance_dir.mkdir(parents=True, exist_ok=True)
        # The EXE carries a populated seed database.  Copy it only on first run,
        # so later annotations remain persistent under the user's LocalAppData.
        seed = (BUNDLE_DIR / 'seed' / 'specifications.db') if IS_FROZEN else (BASE_DIR / 'instance' / 'specifications.db')
        destination = instance_dir / 'specifications.db'
        if seed.exists() and not destination.exists() and seed != destination:
            shutil.copy2(seed, destination)
