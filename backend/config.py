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


def _database_url():
    """Return an explicit database URL, normalizing common shorthand schemes."""
    value = os.environ.get('DATABASE_URL', '').strip()
    if value.startswith('mysql://'):
        return f'mysql+pymysql://{value[len("mysql://"):]}'
    return value


DATABASE_URL = _database_url()
SQLITE_URL = f'sqlite:///{RUNTIME_DIR}/instance/specifications.db'
REQUIRE_PERSISTENT_DB_ENV = os.environ.get('REQUIRE_PERSISTENT_DB', '').lower() in {'1', 'true', 'yes', 'on'}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    # Local/EXE mode keeps SQLite. Production must set DATABASE_URL to a managed
    # or volume-backed database such as MySQL.
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or SQLITE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    } if DATABASE_URL else {}
    if DATABASE_URL:
        SQLALCHEMY_ENGINE_OPTIONS.update({
            'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '280')),
            'pool_size': int(os.environ.get('DB_POOL_SIZE', '2')),
            'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '1')),
        })
    PERSISTENCE_BACKEND = 'sqlite' if SQLALCHEMY_DATABASE_URI.startswith('sqlite') else SQLALCHEMY_DATABASE_URI.split(':', 1)[0]
    PERSISTENCE_CONFIGURED = bool(DATABASE_URL)
    PERSISTENCE_EPHEMERAL = IS_VERCEL and not DATABASE_URL
    REQUIRE_PERSISTENT_DB = REQUIRE_PERSISTENT_DB_ENV
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
        if IS_VERCEL and REQUIRE_PERSISTENT_DB_ENV and not DATABASE_URL:
            raise RuntimeError('REQUIRE_PERSISTENT_DB is enabled, but DATABASE_URL is not configured.')
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        instance_dir = RUNTIME_DIR / 'instance'
        instance_dir.mkdir(parents=True, exist_ok=True)
        # The EXE carries a populated seed database.  Copy it only on first run,
        # so later annotations remain persistent under the user's LocalAppData.
        seed = (BUNDLE_DIR / 'seed' / 'specifications.db') if IS_FROZEN else (BASE_DIR / 'instance' / 'specifications.db')
        destination = instance_dir / 'specifications.db'
        if seed.exists() and not destination.exists() and seed != destination:
            shutil.copy2(seed, destination)
