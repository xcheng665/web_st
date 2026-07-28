"""Load the repository's building-code CSV files into the local SQLite database.

Run from backend/:  python import_internal_data.py
"""
from pathlib import Path
from app import create_app
from models import db, Specification, Article
from api import read_tabular_file, guess_column_mapping


DATASET_DIR = Path(__file__).resolve().parent.parent / '规范数据集'


def import_file(path):
    frame = read_tabular_file(path.read_bytes(), path.name)
    mapping = guess_column_mapping(list(frame.columns))
    code_column, clause_column, content_column = mapping['规范'], mapping['条文'], mapping['条文内容']
    if not all((code_column, clause_column, content_column)):
        raise ValueError(f'{path.name} 未找到规范、条文、条文内容三列')
    code = str(frame.iloc[0][code_column]).strip()
    spec = Specification.query.filter_by(code=code).first()
    if not spec:
        spec = Specification(code=code, name=path.stem)
        db.session.add(spec)
        db.session.flush()
    created = 0
    for _, row in frame.iterrows():
        clause = str(row[clause_column]).strip()
        content = str(row[content_column]).strip()
        if clause and content and not Article.query.filter_by(spec_id=spec.id, clause_number=clause).first():
            db.session.add(Article(spec_id=spec.id, clause_number=clause, content=content))
            created += 1
    db.session.commit()
    return path.name, created


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        for csv_file in sorted(DATASET_DIR.glob('*.csv')):
            name, count = import_file(csv_file)
            # Some Windows GBK terminals cannot render the uncommon spacing
            # characters present in official standard filenames.
            print(f'已处理规范文件：新增 {count} 条')
