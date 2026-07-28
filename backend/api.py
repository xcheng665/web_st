from flask import Blueprint, request, jsonify, send_from_directory
from models import db, Specification, Article, Entity, EntityAlias, Relation, Rule, Annotation, Project, ComplianceAssessment, AnnotationJob
from datetime import datetime
import os
import pandas as pd
from io import BytesIO
import re
import json
from uuid import uuid4
from pathlib import Path
from llm_service import extract_clause, configured, LLMExtractionError
from compliance_service import SCHEMA as COMPLIANCE_SCHEMA, run_checks
from document_import_service import DocumentImportError, extract_document_text, ocr_available, split_into_articles

api = Blueprint('api', __name__)


@api.route('/health', methods=['GET'])
def health():
    """Container readiness endpoint; avoids exposing operational details."""
    return jsonify({'status': 'ok'}), 200


@api.route('/compliance/schema', methods=['GET'])
def get_compliance_schema():
    """Expose a versionable project input contract so frontend and APIs stay aligned."""
    return jsonify({'version': 1, 'fields': COMPLIANCE_SCHEMA})


@api.route('/projects', methods=['GET'])
def get_projects():
    projects = Project.query.order_by(Project.updated_at.desc(), Project.id.desc()).all()
    return jsonify([project.to_dict() for project in projects])


@api.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': '项目名称不能为空'}), 400
    parameters = data.get('parameters') or {}
    if not isinstance(parameters, dict):
        return jsonify({'error': 'parameters 必须为对象'}), 400
    project = Project(name=name, parameters=json.dumps(parameters, ensure_ascii=False))
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@api.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    return jsonify(Project.query.get_or_404(project_id).to_dict())


@api.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = str(data['name']).strip()
        if not name:
            return jsonify({'error': '项目名称不能为空'}), 400
        project.name = name
    if 'parameters' in data:
        if not isinstance(data['parameters'], dict):
            return jsonify({'error': 'parameters 必须为对象'}), 400
        project.parameters = json.dumps(data['parameters'], ensure_ascii=False)
    db.session.commit()
    return jsonify(project.to_dict())


def _latest_assessments(project_id):
    latest = ComplianceAssessment.query.filter_by(project_id=project_id).order_by(ComplianceAssessment.created_at.desc(), ComplianceAssessment.id.desc()).first()
    if not latest:
        return []
    return ComplianceAssessment.query.filter_by(project_id=project_id, run_id=latest.run_id).order_by(ComplianceAssessment.category, ComplianceAssessment.id).all()


@api.route('/projects/<int:project_id>/compliance-check', methods=['POST'])
def run_project_compliance_check(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json(silent=True) or {}
    if 'parameters' in data:
        if not isinstance(data['parameters'], dict):
            return jsonify({'error': 'parameters 必须为对象'}), 400
        project.parameters = json.dumps(data['parameters'], ensure_ascii=False)
    parameters = json.loads(project.parameters or '{}')
    checks = run_checks(parameters)
    run_id = str(uuid4())
    for check in checks:
        db.session.add(ComplianceAssessment(
            project_id=project.id,
            run_id=run_id,
            category=check.category,
            title=check.title,
            status=check.status,
            parameter_key=check.parameter_key,
            input_value=str(check.input_value) if check.input_value is not None else None,
            expected_value=check.expected_value,
            article_id=check.article.id if check.article else None,
            evidence=check.article.content if check.article else None,
            explanation=check.explanation,
        ))
    db.session.commit()
    results = _latest_assessments(project.id)
    summary = {status: sum(item.status == status for item in results) for status in ('pass', 'fail', 'pending', 'advisory')}
    return jsonify({'project': project.to_dict(), 'run_id': run_id, 'summary': summary, 'results': [item.to_dict() for item in results]})


@api.route('/projects/<int:project_id>/compliance-report', methods=['GET'])
def get_project_compliance_report(project_id):
    project = Project.query.get_or_404(project_id)
    results = _latest_assessments(project.id)
    summary = {status: sum(item.status == status for item in results) for status in ('pass', 'fail', 'pending', 'advisory')}
    return jsonify({'project': project.to_dict(), 'summary': summary, 'results': [item.to_dict() for item in results]})


MODAL_TERMS = ('必须', '严禁', '不应', '不得', '应', '不宜', '宜', '可')
NUMERIC_TOKEN = re.compile(r'\d+(?:\.\d+)?\s*(?:m²|m2|㎡|平方米|mm|cm|m|米|层|%|度|人|户|h)')


def _comparison_sentences(content, keyword):
    sentences = [sentence.strip() for sentence in re.split(r'(?<=[。；;])', content) if sentence.strip()]
    return [sentence for sentence in sentences if keyword in sentence] or [content]


@api.route('/standards/compare', methods=['GET'])
def compare_standards():
    """Compare literal evidence across imported standards without generating unsupported conclusions."""
    keyword = str(request.args.get('keyword', '')).strip()
    if len(keyword) < 2:
        return jsonify({'error': '请输入至少 2 个字符的对比主题'}), 400
    raw_ids = request.args.get('spec_ids', '')
    try:
        selected_ids = [int(value) for value in raw_ids.split(',') if value.strip()]
    except ValueError:
        return jsonify({'error': '规范编号格式无效'}), 400
    query = Article.query.filter(Article.content.contains(keyword))
    if selected_ids:
        query = query.filter(Article.spec_id.in_(selected_ids))
    records = []
    for article in query.order_by(Article.spec_id, Article.clause_number).limit(300).all():
        matching = _comparison_sentences(article.content, keyword)
        evidence = ' '.join(matching)
        records.append({
            'article_id': article.id,
            'spec_id': article.spec_id,
            'specification': article.specification.code,
            'specification_name': article.specification.name,
            'clause_number': article.clause_number,
            'sentences': matching,
            'numeric_values': sorted(set(NUMERIC_TOKEN.findall(evidence))),
            'modal_terms': [term for term in MODAL_TERMS if term in evidence],
        })
    return jsonify({
        'keyword': keyword,
        'records': records,
        'summary': {
            'specifications': len(set(item['spec_id'] for item in records)),
            'clauses': len(records),
            'numeric_values': sorted({value for item in records for value in item['numeric_values']}),
            'modal_terms': sorted({value for item in records for value in item['modal_terms']}),
        },
        'notice': '结果为原文比对，不替代专业人员对适用条件、版本效力与上下文的判断。'
    })


@api.route('/standards/version-readiness', methods=['GET'])
def version_comparison_readiness():
    """Find imported editions that are eligible for a true same-standard version comparison."""
    groups = {}
    for specification in Specification.query.order_by(Specification.code).all():
        family = re.sub(r'-\d{4}.*$', '', specification.code).strip() or specification.code
        groups.setdefault(family, []).append(specification.to_dict())
    ready = [{'family': family, 'versions': versions} for family, versions in groups.items() if len(versions) > 1]
    return jsonify({
        'ready_groups': ready,
        'imported_count': Specification.query.count(),
        'message': '导入同一规范的两个及以上年份版本后，即可按条文号计算新增、删除与正文变化。' if not ready else '已发现可用于版本对比的规范组。'
    })

ENTITY_PATTERNS = [
    (r'[零一二三四五六七八九十百千万]+[米层级类种型]', '概念'),
    (r'[A-Za-z0-9-]+规范', '概念'),
    (r'建筑[结构类型高度面积层数]', '实体'),
    (r'抗震[设防设计等级烈度]', '实体'),
    (r'混凝土[强度等级结构]', '实体'),
    (r'钢筋[混凝土级别]', '实体'),
    (r'耐火[等级极限]', '属性'),
    (r'安全[等级标准]', '属性'),
    (r'设计[规范标准要求]', '概念'),
    (r'标准[编号名称]', '概念'),
    (r'GB[0-9-]+', '概念'),
    (r'[0-9]+[米m层]', '属性'),
    (r'不应小于|不应大于|应大于|应小于', '约束'),
    (r'必须|严禁|应|不应', '约束'),
]

RELATION_TYPES = [
    '属于', '包含', '大于', '小于', '等于', '不应小于', '不应大于',
    '应满足', '必须', '严禁', '遵循', '符合', '适用于', '不适用于'
]

def allowed_file(filename):
    from config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def allowed_tabular_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx', 'xls'}

def guess_column_mapping(columns):
    mapping = {'规范': None, '条文': None, '条文内容': None}
    rules = {
        '规范': ['规范名称', '规范', '标准名称', '标准', 'standard', 'spec', '文件名', '规范编号', 'code'],
        '条文': ['条文号', '条文编号', '章节号', '编号', '条款号', 'article', 'clause', 'section', '序号', '条文', 'clause_number'],
        '条文内容': ['条文内容', '内容', '正文', '条款内容', 'content', 'text', '描述', '说明', '条款']
    }
    columns_lower = [str(c).lower().strip() for c in columns]
    used_columns = set()
    
    for target, keywords in rules.items():
        for keyword in keywords:
            for i, col in enumerate(columns_lower):
                if keyword.lower() in col and columns[i] not in used_columns:
                    mapping[target] = columns[i]
                    used_columns.add(columns[i])
                    break
            if mapping[target]:
                break
    
    unmapped_cols = [c for c in columns if c not in used_columns]
    unmapped_targets = [t for t, v in mapping.items() if v is None]
    for i, target in enumerate(unmapped_targets):
        if i < len(unmapped_cols):
            mapping[target] = unmapped_cols[i]
    
    return mapping


def read_tabular_file(content, filename):
    """Read both headed user uploads and the repository's headerless CSV datasets."""
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']
    last_error = None
    for encoding in encodings:
        try:
            if filename.lower().endswith('.csv'):
                frame = pd.read_csv(BytesIO(content), encoding=encoding, header=None)
                first_row = [str(value).strip().lower() for value in frame.iloc[0].tolist()]
                header_tokens = {'规范名称', '规范', '标准名称', '条文号', '条文编号', '条文内容', '内容', '正文'}
                if any(value in header_tokens for value in first_row):
                    frame.columns = frame.iloc[0].tolist()
                    frame = frame.iloc[1:].reset_index(drop=True)
                else:
                    # Internal datasets use the stable order: code, clause number, content.
                    frame.columns = ['规范', '条文', '条文内容'] + [f'扩展列{i}' for i in range(max(0, len(frame.columns) - 3))]
            else:
                frame = pd.read_excel(BytesIO(content))
            if not frame.empty and len(frame.columns) >= 1:
                return frame
        except Exception as exc:
            last_error = exc
    raise ValueError(f'无法识别文件编码或结构：{last_error}')

@api.route('/specifications', methods=['GET'])
def get_specifications():
    specs = Specification.query.all()
    return jsonify([spec.to_dict() for spec in specs])

@api.route('/specifications/<int:spec_id>', methods=['GET'])
def get_specification(spec_id):
    spec = Specification.query.get_or_404(spec_id)
    return jsonify(spec.to_dict())

@api.route('/specifications', methods=['POST'])
def create_specification():
    data = request.get_json()
    if not data or 'code' not in data or 'name' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    spec = Specification(code=data['code'], name=data['name'])
    db.session.add(spec)
    db.session.commit()
    return jsonify(spec.to_dict()), 201

@api.route('/specifications/<int:spec_id>', methods=['PUT'])
def update_specification(spec_id):
    spec = Specification.query.get_or_404(spec_id)
    data = request.get_json()
    if 'code' in data:
        spec.code = data['code']
    if 'name' in data:
        spec.name = data['name']
    db.session.commit()
    return jsonify(spec.to_dict())

@api.route('/specifications/<int:spec_id>', methods=['DELETE'])
def delete_specification(spec_id):
    spec = Specification.query.get_or_404(spec_id)
    db.session.delete(spec)
    db.session.commit()
    return jsonify({'message': '删除成功'}), 200

@api.route('/specifications/<int:spec_id>/articles', methods=['GET'])
def get_articles(spec_id):
    articles = Article.query.filter_by(spec_id=spec_id).all()
    return jsonify([article.to_dict() for article in articles])

@api.route('/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify(article.to_dict())

@api.route('/articles/<int:article_id>', methods=['PUT'])
def update_article(article_id):
    article = Article.query.get_or_404(article_id)
    data = request.get_json()
    if 'clause_number' in data:
        article.clause_number = data['clause_number']
    if 'content' in data:
        article.content = data['content']
    if 'entity_tagged' in data:
        article.entity_tagged = data['entity_tagged']
    if 'relation_tagged' in data:
        article.relation_tagged = data['relation_tagged']
    if 'rule_tagged' in data:
        article.rule_tagged = data['rule_tagged']
    db.session.commit()
    return jsonify(article.to_dict())

@api.route('/upload', methods=['POST'])
def upload_file():
    from config import Config
    
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if file and allowed_tabular_file(file.filename):
        try:
            df = read_tabular_file(file.read(), file.filename)
            
            columns = list(df.columns)
            mapping = guess_column_mapping(columns)
            
            spec_name = file.filename
            
            spec = Specification.query.filter_by(code=df.iloc[0][mapping['规范']]).first()
            if not spec:
                spec = Specification(
                    code=df.iloc[0][mapping['规范']],
                    name=spec_name
                )
                db.session.add(spec)
                db.session.commit()
            
            for _, row in df.iterrows():
                clause_number = str(row[mapping['条文']]) if mapping['条文'] else ''
                content = str(row[mapping['条文内容']]) if mapping['条文内容'] else ''
                
                existing_article = Article.query.filter_by(
                    spec_id=spec.id,
                    clause_number=clause_number
                ).first()
                
                if not existing_article:
                    article = Article(
                        spec_id=spec.id,
                        clause_number=clause_number,
                        content=content
                    )
                    db.session.add(article)
            
            db.session.commit()
            return jsonify({
                'message': f'成功导入 {len(df)} 条数据',
                'spec_id': spec.id,
                'spec_name': spec.name
            }), 201
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': '此入口仅支持 CSV、Excel；PDF、Word 请使用文档导入入口。'}), 400


@api.route('/document-import', methods=['POST'])
def import_document():
    """Import text-bearing PDF/DOCX clauses while preserving the extraction method."""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '文件名为空'}), 400
    extension = Path(file.filename).suffix.lower()
    if extension not in {'.pdf', '.docx'}:
        return jsonify({'error': '文档导入仅支持 PDF 或 DOCX'}), 400
    code = str(request.form.get('spec_code', '')).strip()
    name = str(request.form.get('spec_name', '')).strip()
    if not code or not name:
        return jsonify({'error': '请填写规范编号和规范名称，以建立可追溯来源。'}), 400
    try:
        extracted = extract_document_text(file.read(), file.filename)
        clauses = split_into_articles(extracted['text'])
    except DocumentImportError as exc:
        return jsonify({'error': str(exc), 'ocr_available': ocr_available()}), 422
    if not clauses:
        return jsonify({'error': '未识别出可导入的条文段落；请检查文档文本结构。'}), 422
    specification = Specification.query.filter_by(code=code).first()
    if not specification:
        specification = Specification(code=code, name=name)
        db.session.add(specification)
        db.session.flush()
    else:
        specification.name = name
    imported, duplicates = 0, 0
    for clause_number, content in clauses:
        existing = Article.query.filter_by(spec_id=specification.id, clause_number=clause_number).first()
        if existing:
            duplicates += 1
            continue
        db.session.add(Article(spec_id=specification.id, clause_number=clause_number, content=content))
        imported += 1
    db.session.commit()
    return jsonify({
        'message': f'成功导入 {imported} 条文段落',
        'spec_id': specification.id,
        'spec_name': specification.name,
        'spec_code': specification.code,
        'imported': imported,
        'duplicates': duplicates,
        'extraction_method': extracted['method'],
        'ocr_pending': extracted['ocr_pending'],
    }), 201

@api.route('/entities', methods=['GET'])
def get_entities():
    entities = Entity.query.all()
    return jsonify([entity.to_dict() for entity in entities])

@api.route('/entities/<int:entity_id>', methods=['GET'])
def get_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    return jsonify(entity.to_dict())


@api.route('/entities/<int:entity_id>/aliases', methods=['GET', 'POST'])
def entity_aliases(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    if request.method == 'GET':
        return jsonify([alias.to_dict() for alias in entity.aliases])
    data = request.get_json(silent=True) or {}
    alias_name = str(data.get('alias', '')).strip()
    if not alias_name:
        return jsonify({'error': '别名不能为空'}), 400
    if alias_name == entity.name:
        return jsonify({'error': '别名不能与标准实体名称相同'}), 400
    if Entity.query.filter_by(name=alias_name).first() or EntityAlias.query.filter_by(alias=alias_name).first():
        return jsonify({'error': '该名称已是实体或已归并的别名'}), 409
    alias = EntityAlias(entity_id=entity.id, alias=alias_name)
    db.session.add(alias)
    db.session.commit()
    return jsonify(alias.to_dict()), 201


@api.route('/entity-aliases/<int:alias_id>', methods=['DELETE'])
def delete_entity_alias(alias_id):
    alias = EntityAlias.query.get_or_404(alias_id)
    db.session.delete(alias)
    db.session.commit()
    return jsonify({'message': '别名已删除'})

@api.route('/entities', methods=['POST'])
def create_entity():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': '缺少名称参数'}), 400
    
    existing = Entity.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': '实体已存在'}), 409
    
    entity = Entity(
        name=data['name'],
        entity_type=data.get('entity_type', '实体'),
        description=data.get('description')
    )
    db.session.add(entity)
    db.session.commit()
    return jsonify(entity.to_dict()), 201

@api.route('/entities/<int:entity_id>', methods=['PUT'])
def update_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    data = request.get_json()
    if 'name' in data:
        entity.name = data['name']
    if 'entity_type' in data:
        entity.entity_type = data['entity_type']
    if 'description' in data:
        entity.description = data['description']
    db.session.commit()
    return jsonify(entity.to_dict())

@api.route('/entities/<int:entity_id>', methods=['DELETE'])
def delete_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    db.session.delete(entity)
    db.session.commit()
    return jsonify({'message': '删除成功'}), 200

@api.route('/relations', methods=['GET'])
def get_relations():
    relations = Relation.query.all()
    return jsonify([relation.to_dict() for relation in relations])

@api.route('/relations/<int:relation_id>', methods=['GET'])
def get_relation(relation_id):
    relation = Relation.query.get_or_404(relation_id)
    return jsonify(relation.to_dict())

@api.route('/relations', methods=['POST'])
def create_relation():
    data = request.get_json()
    required = ['source_id', 'target_id', 'relation_type']
    if not data or any(k not in data for k in required):
        return jsonify({'error': '缺少必要参数'}), 400
    
    if data['source_id'] == data['target_id']:
        return jsonify({'error': '源节点和目标节点不能相同'}), 400
    
    relation = Relation(
        source_id=data['source_id'],
        target_id=data['target_id'],
        relation_type=data['relation_type'],
        description=data.get('description')
    )
    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_dict()), 201

@api.route('/relations/<int:relation_id>', methods=['PUT'])
def update_relation(relation_id):
    relation = Relation.query.get_or_404(relation_id)
    data = request.get_json()
    if 'source_id' in data:
        relation.source_id = data['source_id']
    if 'target_id' in data:
        relation.target_id = data['target_id']
    if 'relation_type' in data:
        relation.relation_type = data['relation_type']
    if 'description' in data:
        relation.description = data['description']
    db.session.commit()
    return jsonify(relation.to_dict())

@api.route('/relations/<int:relation_id>', methods=['DELETE'])
def delete_relation(relation_id):
    relation = Relation.query.get_or_404(relation_id)
    db.session.delete(relation)
    db.session.commit()
    return jsonify({'message': '删除成功'}), 200

@api.route('/rules', methods=['GET'])
def get_rules():
    rules = Rule.query.all()
    return jsonify([rule.to_dict() for rule in rules])

@api.route('/rules/<int:rule_id>', methods=['GET'])
def get_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    return jsonify(rule.to_dict())

@api.route('/rules', methods=['POST'])
def create_rule():
    data = request.get_json()
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'error': '缺少名称或内容参数'}), 400
    
    rule = Rule(
        name=data['name'],
        content=data['content'],
        rule_type=data.get('rule_type', '约束规则')
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify(rule.to_dict()), 201

@api.route('/rules/<int:rule_id>', methods=['PUT'])
def update_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    data = request.get_json()
    if 'name' in data:
        rule.name = data['name']
    if 'content' in data:
        rule.content = data['content']
    if 'rule_type' in data:
        rule.type = data['rule_type']
    db.session.commit()
    return jsonify(rule.to_dict())

@api.route('/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'message': '删除成功'}), 200

@api.route('/knowledge_graph', methods=['GET'])
def get_knowledge_graph():
    entities = Entity.query.all()
    relations = Relation.query.all()
    rules = Rule.query.all()
    
    nodes = []
    for entity in entities:
        node = entity.to_dict()
        all_evidence_articles = entity.articles.order_by(Article.id).all()
        evidence_articles = all_evidence_articles[:3]
        annotations = Annotation.query.filter(Annotation.article_id.in_([article.id for article in all_evidence_articles]), Annotation.status == 'applied').all() if all_evidence_articles else []
        confidence_values = []
        for annotation in annotations:
            try:
                for item in json.loads(annotation.payload).get('entities', []):
                    if item.get('name') == entity.name and isinstance(item.get('confidence'), (int, float)):
                        confidence_values.append(item['confidence'])
            except (json.JSONDecodeError, TypeError):
                continue
        reviewed = bool(annotations)
        evidence_count = len(all_evidence_articles)
        score = min(100, 25 + min(evidence_count, 3) * 15 + (25 if reviewed else 0) + (round(sum(confidence_values) / len(confidence_values) * 20) if confidence_values else 0))
        node['evidence'] = [{
            'article_id': article.id,
            'clause_number': article.clause_number,
            'content': article.content
        } for article in evidence_articles]
        node['spec_ids'] = sorted({article.spec_id for article in all_evidence_articles})
        node['evidence_strength'] = {
            'score': score,
            'article_count': evidence_count,
            'reviewed': reviewed,
            'llm_confidence': round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
            'status': '已审核入图' if reviewed else ('本地示例，待复核' if str(entity.description or '').startswith('local-demo') else '有原文关联，待审核'),
        }
        nodes.append(node)
    edges = []
    for relation in relations:
        edge = relation.to_dict()
        articles = relation.articles.all()
        edge['article_ids'] = [article.id for article in articles]
        edge['spec_ids'] = sorted({article.spec_id for article in articles})
        annotations = Annotation.query.filter(Annotation.article_id.in_(edge['article_ids']), Annotation.status == 'applied').all() if articles else []
        confidence_values = []
        for annotation in annotations:
            try:
                for item in json.loads(annotation.payload).get('relations', []):
                    if item.get('source') == relation.source.name and item.get('target') == relation.target.name and item.get('predicate') == relation.relation_type and isinstance(item.get('confidence'), (int, float)):
                        confidence_values.append(item['confidence'])
            except (json.JSONDecodeError, TypeError):
                continue
        edge['evidence_strength'] = {
            'score': min(100, 25 + min(len(articles), 3) * 15 + (25 if annotations else 0) + (round(sum(confidence_values) / len(confidence_values) * 20) if confidence_values else 0)),
            'article_count': len(articles),
            'reviewed': bool(annotations),
            'llm_confidence': round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
            'status': '已审核入图' if annotations else '有原文关联，待审核',
        }
        edges.append(edge)
    kg = {
        'nodes': nodes,
        'edges': edges,
        'rules': [rule.to_dict() for rule in rules]
    }
    return jsonify(kg)

@api.route('/stats', methods=['GET'])
def get_stats():
    spec_count = Specification.query.count()
    article_count = Article.query.count()
    entity_count = Entity.query.count()
    relation_count = Relation.query.count()
    rule_count = Rule.query.count()
    
    return jsonify({
        'specifications': spec_count,
        'articles': article_count,
        'entities': entity_count,
        'relations': relation_count,
        'rules': rule_count
    })


@api.route('/llm/status', methods=['GET'])
def llm_status():
    """Expose configuration availability without exposing a secret."""
    from flask import current_app
    return jsonify({
        'configured': configured(current_app.config),
        'model': current_app.config['LLM_MODEL'],
        'base_url': current_app.config['LLM_BASE_URL']
    })


def _masked_key(value):
    if not value:
        return ''
    return f'{value[:4]}••••••••{value[-4:]}' if len(value) > 8 else '••••••••'


@api.route('/settings/llm', methods=['GET', 'PUT'])
def llm_settings():
    """Read/update provider settings without ever returning the secret itself."""
    from flask import current_app
    if request.method == 'GET':
        return jsonify({
            'configured': configured(current_app.config),
            'api_key_masked': _masked_key(current_app.config.get('LLM_API_KEY', '')),
            'base_url': current_app.config['LLM_BASE_URL'],
            'model': current_app.config['LLM_MODEL']
        })
    payload = request.get_json(silent=True) or {}
    base_url = str(payload.get('base_url', '')).strip().rstrip('/')
    model = str(payload.get('model', '')).strip()
    api_key = str(payload.get('api_key', '')).strip()
    if not base_url or not model:
        return jsonify({'error': 'Base URL 和模型名称不能为空'}), 400
    # Empty API key preserves an already configured key; the browser never reads it.
    if api_key:
        current_app.config['LLM_API_KEY'] = api_key
    current_app.config['LLM_BASE_URL'] = base_url
    current_app.config['LLM_MODEL'] = model
    from config import RUNTIME_DIR
    env_path = Path(RUNTIME_DIR) / '.env'
    env_path.parent.mkdir(parents=True, exist_ok=True)
    saved_key = current_app.config.get('LLM_API_KEY', '')
    env_path.write_text(
        f'LLM_API_KEY={saved_key}\nLLM_BASE_URL={base_url}\nLLM_MODEL={model}\n',
        encoding='utf-8'
    )
    return jsonify({'message': '模型配置已保存', 'configured': bool(saved_key), 'api_key_masked': _masked_key(saved_key)})


@api.route('/settings/llm/test', methods=['POST'])
def test_llm_settings():
    from flask import current_app
    if not configured(current_app.config):
        return jsonify({'error': '请先保存 API Key'}), 400
    try:
        extract_clause(current_app.config, '连接测试', '建筑设计应满足安全、适用和耐久的基本要求。')
        return jsonify({'message': '连接成功，模型可用于条文抽取'})
    except LLMExtractionError as exc:
        return jsonify({'error': str(exc)}), 503


@api.route('/dashboard', methods=['GET'])
def dashboard():
    from flask import current_app
    specs = Specification.query.order_by(Specification.created_at.desc()).all()
    return jsonify({
        'metrics': {
            'specifications': len(specs), 'articles': Article.query.count(),
            'entities': Entity.query.count(), 'relations': Relation.query.count(),
            'pending_annotations': Annotation.query.filter_by(status='pending').count()
        },
        'specifications': [{
            **spec.to_dict(),
            'articles': Article.query.filter_by(spec_id=spec.id).count(),
            'tagged_articles': Article.query.filter_by(spec_id=spec.id, entity_tagged=True).count()
        } for spec in specs[:6]],
        'recent_entities': [entity.to_dict() for entity in Entity.query.order_by(Entity.created_at.desc()).limit(6).all()],
          'pending': [annotation.to_dict() for annotation in Annotation.query.filter_by(status='pending').order_by(Annotation.created_at.desc()).limit(6).all()],
          'recent_projects': [project.to_dict() for project in Project.query.order_by(Project.updated_at.desc(), Project.id.desc()).limit(4).all()],
          'llm': {'configured': configured(current_app.config), 'model': current_app.config['LLM_MODEL']}
    })


@api.route('/articles/<int:article_id>/annotations', methods=['GET'])
def get_article_annotations(article_id):
    Article.query.get_or_404(article_id)
    annotations = Annotation.query.filter_by(article_id=article_id).order_by(Annotation.created_at.desc()).all()
    return jsonify([annotation.to_dict() for annotation in annotations])


@api.route('/annotations', methods=['GET'])
def list_annotations():
    status = request.args.get('status')
    spec_id = request.args.get('spec_id', type=int)
    query = Annotation.query.join(Article)
    if status:
        query = query.filter(Annotation.status == status)
    if spec_id:
        query = query.filter(Article.spec_id == spec_id)
    annotations = query.order_by(Annotation.created_at.desc(), Annotation.id.desc()).limit(500).all()
    return jsonify([annotation.to_dict() for annotation in annotations])


@api.route('/annotations/<int:annotation_id>', methods=['PUT'])
def update_annotation(annotation_id):
    """Reviewers can correct structured extraction before approving it into the graph."""
    annotation = Annotation.query.get_or_404(annotation_id)
    if annotation.status != 'pending':
        return jsonify({'error': '只有待审核标注可以修改'}), 409
    data = request.get_json(silent=True) or {}
    payload = data.get('payload')
    if not isinstance(payload, dict) or any(not isinstance(payload.get(key, []), list) for key in ('entities', 'relations', 'rules')):
        return jsonify({'error': 'payload 必须包含 entities、relations、rules 三个数组'}), 400
    annotation.payload = json.dumps({key: payload.get(key, []) for key in ('entities', 'relations', 'rules')}, ensure_ascii=False)
    db.session.commit()
    return jsonify(annotation.to_dict())


@api.route('/articles/<int:article_id>/llm-annotations', methods=['POST'])
def create_llm_annotation(article_id):
    """Extract a reviewable annotation; nothing enters the graph until applied."""
    from flask import current_app
    article = Article.query.get_or_404(article_id)
    try:
        payload = extract_clause(current_app.config, article.clause_number, article.content)
    except LLMExtractionError as exc:
        return jsonify({'error': str(exc)}), 503
    annotation = Annotation(
        article_id=article.id,
        payload=json.dumps(payload, ensure_ascii=False),
        model=current_app.config['LLM_MODEL']
    )
    db.session.add(annotation)
    db.session.commit()
    return jsonify(annotation.to_dict()), 201


def _execute_annotation_job(job, articles):
    """Synchronous development runner with the same durable job contract as a future queue worker."""
    from flask import current_app
    job.status = 'running'
    db.session.commit()
    created, failures = [], []
    for article in articles:
        try:
            payload = extract_clause(current_app.config, article.clause_number, article.content)
            annotation = Annotation(article_id=article.id, payload=json.dumps(payload, ensure_ascii=False), model=current_app.config['LLM_MODEL'])
            db.session.add(annotation)
            db.session.flush()
            created.append(annotation.id)
        except (LLMExtractionError, Exception) as exc:
            failures.append({'article_id': article.id, 'error': str(exc)})
    job.created_annotation_ids = json.dumps(created)
    job.failures = json.dumps(failures, ensure_ascii=False)
    job.status = 'completed' if not failures else ('partial' if created else 'failed')
    job.completed_at = datetime.utcnow()
    db.session.commit()
    return job


@api.route('/annotation-jobs', methods=['GET'])
def get_annotation_jobs():
    limit = min(max(int(request.args.get('limit', 20)), 1), 100)
    jobs = AnnotationJob.query.order_by(AnnotationJob.created_at.desc(), AnnotationJob.id.desc()).limit(limit).all()
    return jsonify([job.to_dict() for job in jobs])


@api.route('/specifications/<int:spec_id>/llm-annotations', methods=['POST'])
def create_specification_llm_annotations(spec_id):
    """Batch extraction writes a durable, retryable job and keeps all outputs pending review."""
    from flask import current_app
    Specification.query.get_or_404(spec_id)
    if not configured(current_app.config):
        return jsonify({'error': '未配置 LLM_API_KEY。请在 backend/.env 中设置 API 密钥后重启服务。'}), 503
    data = request.get_json(silent=True) or {}
    limit = min(max(int(data.get('limit', 20)), 1), 100)
    articles = Article.query.filter_by(spec_id=spec_id).order_by(Article.id).limit(limit).all()
    job = AnnotationJob(
        spec_id=spec_id,
        status='queued',
        requested_article_ids=json.dumps([article.id for article in articles]),
        model=current_app.config['LLM_MODEL'],
    )
    db.session.add(job)
    db.session.commit()
    job = _execute_annotation_job(job, articles)
    response = job.to_dict()
    response['requested'] = len(articles)
    return jsonify(response)


@api.route('/annotation-jobs/<int:job_id>/retry', methods=['POST'])
def retry_annotation_job(job_id):
    from flask import current_app
    original = AnnotationJob.query.get_or_404(job_id)
    if not configured(current_app.config):
        return jsonify({'error': '未配置 LLM_API_KEY。请先在模型配置中保存密钥。'}), 503
    failures = json.loads(original.failures or '[]')
    article_ids = [item.get('article_id') for item in failures if item.get('article_id')]
    if not article_ids:
        return jsonify({'error': '该任务没有可重试的失败条文'}), 400
    articles = Article.query.filter(Article.id.in_(article_ids)).order_by(Article.id).all()
    job = AnnotationJob(
        spec_id=original.spec_id,
        status='queued',
        requested_article_ids=json.dumps([article.id for article in articles]),
        model=current_app.config['LLM_MODEL'],
        retry_of_id=original.id,
    )
    db.session.add(job)
    db.session.commit()
    job = _execute_annotation_job(job, articles)
    response = job.to_dict()
    response['requested'] = len(articles)
    return jsonify(response)


@api.route('/annotations/<int:annotation_id>/apply', methods=['POST'])
def apply_annotation(annotation_id):
    """Persist approved entities, relations and rules while retaining clause evidence."""
    annotation = Annotation.query.get_or_404(annotation_id)
    if annotation.status == 'applied':
        return jsonify({'error': '该标注已经入图'}), 409
    payload = json.loads(annotation.payload)
    entity_by_name = {}
    saved_entities = 0
    for item in payload.get('entities', []):
        name = str(item.get('name', '')).strip()
        if not name:
            continue
        alias = EntityAlias.query.filter_by(alias=name).first()
        entity = alias.entity if alias else Entity.query.filter_by(name=name).first()
        if not entity:
            entity = Entity(name=name, entity_type=item.get('type', '其他'), description=item.get('evidence', ''))
            db.session.add(entity)
            db.session.flush()
            saved_entities += 1
        entity_by_name[name] = entity
        if entity not in annotation.article.entities:
            annotation.article.entities.append(entity)

    saved_relations = 0
    for item in payload.get('relations', []):
        source_name, target_name = str(item.get('source', '')).strip(), str(item.get('target', '')).strip()
        source, target = entity_by_name.get(source_name), entity_by_name.get(target_name)
        if not source or not target or source.id == target.id:
            continue
        relation_type = str(item.get('predicate', '其他')).strip() or '其他'
        relation = Relation.query.filter_by(source_id=source.id, target_id=target.id, relation_type=relation_type).first()
        if not relation:
            relation = Relation(source_id=source.id, target_id=target.id, relation_type=relation_type, description=item.get('evidence', ''))
            db.session.add(relation)
            db.session.flush()
            saved_relations += 1
        if relation not in annotation.article.relations:
            annotation.article.relations.append(relation)

    saved_rules = 0
    for item in payload.get('rules', []):
        name, content = str(item.get('name', '')).strip(), str(item.get('content', '')).strip()
        if name and content and not Rule.query.filter_by(name=name, content=content).first():
            db.session.add(Rule(name=name, content=content, rule_type=item.get('rule_type', '约束规则')))
            saved_rules += 1
    annotation.status = 'applied'
    annotation.applied_at = datetime.utcnow()
    annotation.article.entity_tagged = bool(payload.get('entities'))
    annotation.article.relation_tagged = bool(payload.get('relations'))
    annotation.article.rule_tagged = bool(payload.get('rules'))
    db.session.commit()
    return jsonify({'annotation_id': annotation.id, 'saved_entities': saved_entities, 'saved_relations': saved_relations, 'saved_rules': saved_rules})


@api.route('/annotations/<int:annotation_id>/reject', methods=['POST'])
def reject_annotation(annotation_id):
    """Retain an audit trail for reviewed but rejected model output."""
    annotation = Annotation.query.get_or_404(annotation_id)
    if annotation.status == 'applied':
        return jsonify({'error': '已入图的标注不能直接拒绝'}), 409
    annotation.status = 'rejected'
    db.session.commit()
    return jsonify({'annotation_id': annotation.id, 'status': annotation.status})

def extract_entities_from_text(text):
    entities = []
    seen = set()
    
    for pattern, entity_type in ENTITY_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in seen and len(match) >= 2:
                seen.add(match)
                entities.append({
                    'name': match,
                    'entity_type': entity_type
                })
    
    keywords = ['建筑高度', '抗震设防', '混凝土', '钢筋', '耐火等级', '安全等级', 
                '设计规范', '结构体系', '地基基础', '钢结构', '框架结构',
                '抗震墙', '砌体结构', '剪力墙', '高层建筑', '多层建筑']
    
    for keyword in keywords:
        if keyword in text and keyword not in seen:
            seen.add(keyword)
            entities.append({
                'name': keyword,
                'entity_type': '实体' if keyword in ['建筑高度', '混凝土', '钢筋', '钢结构', '框架结构', '抗震墙', '砌体结构', '剪力墙'] else '概念'
            })
    
    return entities

def extract_relations_from_text(text):
    relations = []
    
    patterns = [
        (r'([\u4e00-\u9fa5]+)[大于小于等于]+([0-9]+[米m层])', '大于'),
        (r'([\u4e00-\u9fa5]+)不应小于([0-9]+[米m层%])', '不应小于'),
        (r'([\u4e00-\u9fa5]+)不应大于([0-9]+[米m层%])', '不应大于'),
        (r'([\u4e00-\u9fa5]+)应满足([\u4e00-\u9fa5]+)', '应满足'),
        (r'([\u4e00-\u9fa5]+)属于([\u4e00-\u9fa5]+)', '属于'),
        (r'([\u4e00-\u9fa5]+)适用于([\u4e00-\u9fa5]+)', '适用于'),
        (r'必须([\u4e00-\u9fa5]+)', '必须'),
        (r'严禁([\u4e00-\u9fa5]+)', '严禁'),
    ]
    
    for pattern, relation_type in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 2:
                source, target = match
                if len(source) >= 2 and len(target) >= 2:
                    relations.append({
                        'source': source.strip(),
                        'target': target.strip(),
                        'relation_type': relation_type
                    })
    
    return relations

@api.route('/extract/entities', methods=['POST'])
def extract_entities():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': '缺少text参数'}), 400
    
    text = data['text']
    entities = extract_entities_from_text(text)
    
    return jsonify({
        'count': len(entities),
        'entities': entities
    })

@api.route('/extract/relations', methods=['POST'])
def extract_relations():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': '缺少text参数'}), 400
    
    text = data['text']
    relations = extract_relations_from_text(text)
    
    return jsonify({
        'count': len(relations),
        'relations': relations
    })

@api.route('/extract/article/<int:article_id>', methods=['POST'])
def extract_from_article(article_id):
    article = Article.query.get_or_404(article_id)
    
    entities = extract_entities_from_text(article.content)
    relations = extract_relations_from_text(article.content)
    
    saved_entities = []
    saved_relations = []
    
    for entity in entities:
        existing = Entity.query.filter_by(name=entity['name']).first()
        if not existing:
            new_entity = Entity(
                name=entity['name'],
                entity_type=entity['entity_type']
            )
            db.session.add(new_entity)
            saved_entities.append(entity)
    
    db.session.commit()
    
    for relation in relations:
        source = Entity.query.filter_by(name=relation['source']).first()
        target = Entity.query.filter_by(name=relation['target']).first()
        
        if source and target and source.id != target.id:
            existing_relation = Relation.query.filter_by(
                source_id=source.id,
                target_id=target.id,
                relation_type=relation['relation_type']
            ).first()
            if not existing_relation:
                new_relation = Relation(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=relation['relation_type']
                )
                db.session.add(new_relation)
                saved_relations.append(relation)
    
    db.session.commit()
    
    return jsonify({
        'article_id': article_id,
        'clause_number': article.clause_number,
        'extracted_entities': len(entities),
        'saved_entities': len(saved_entities),
        'extracted_relations': len(relations),
        'saved_relations': len(saved_relations),
        'entities': saved_entities,
        'relations': saved_relations
    })

@api.route('/extract/specification/<int:spec_id>', methods=['POST'])
def extract_from_specification(spec_id):
    articles = Article.query.filter_by(spec_id=spec_id).all()
    
    total_extracted_entities = 0
    total_saved_entities = 0
    total_extracted_relations = 0
    total_saved_relations = 0
    
    for article in articles:
        entities = extract_entities_from_text(article.content)
        relations = extract_relations_from_text(article.content)
        
        for entity in entities:
            existing = Entity.query.filter_by(name=entity['name']).first()
            if not existing:
                new_entity = Entity(
                    name=entity['name'],
                    entity_type=entity['entity_type']
                )
                db.session.add(new_entity)
                total_saved_entities += 1
        
        total_extracted_entities += len(entities)
    
    db.session.commit()
    
    for article in articles:
        relations = extract_relations_from_text(article.content)
        for relation in relations:
            source = Entity.query.filter_by(name=relation['source']).first()
            target = Entity.query.filter_by(name=relation['target']).first()
            
            if source and target and source.id != target.id:
                existing_relation = Relation.query.filter_by(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=relation['relation_type']
                ).first()
                if not existing_relation:
                    new_relation = Relation(
                        source_id=source.id,
                        target_id=target.id,
                        relation_type=relation['relation_type']
                    )
                    db.session.add(new_relation)
                    total_saved_relations += 1
        
        total_extracted_relations += len(relations)
    
    db.session.commit()
    
    return jsonify({
        'spec_id': spec_id,
        'articles_count': len(articles),
        'total_extracted_entities': total_extracted_entities,
        'total_saved_entities': total_saved_entities,
        'total_extracted_relations': total_extracted_relations,
        'total_saved_relations': total_saved_relations
    })

@api.route('/extract/all', methods=['POST'])
def extract_all_specifications():
    specifications = Specification.query.all()
    
    results = []
    for spec in specifications:
        result = extract_from_specification_internal(spec.id)
        results.append(result)
    
    return jsonify({
        'specifications_count': len(specifications),
        'results': results
    })

def extract_from_specification_internal(spec_id):
    articles = Article.query.filter_by(spec_id=spec_id).all()
    
    total_extracted_entities = 0
    total_saved_entities = 0
    total_extracted_relations = 0
    total_saved_relations = 0
    
    for article in articles:
        entities = extract_entities_from_text(article.content)
        relations = extract_relations_from_text(article.content)
        
        for entity in entities:
            existing = Entity.query.filter_by(name=entity['name']).first()
            if not existing:
                new_entity = Entity(
                    name=entity['name'],
                    entity_type=entity['entity_type']
                )
                db.session.add(new_entity)
                total_saved_entities += 1
        
        total_extracted_entities += len(entities)
    
    db.session.commit()
    
    for article in articles:
        relations = extract_relations_from_text(article.content)
        for relation in relations:
            source = Entity.query.filter_by(name=relation['source']).first()
            target = Entity.query.filter_by(name=relation['target']).first()
            
            if source and target and source.id != target.id:
                existing_relation = Relation.query.filter_by(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=relation['relation_type']
                ).first()
                if not existing_relation:
                    new_relation = Relation(
                        source_id=source.id,
                        target_id=target.id,
                        relation_type=relation['relation_type']
                    )
                    db.session.add(new_relation)
                    total_saved_relations += 1
        
        total_extracted_relations += len(relations)
    
    db.session.commit()
    
    return {
        'spec_id': spec_id,
        'articles_count': len(articles),
        'total_extracted_entities': total_extracted_entities,
        'total_saved_entities': total_saved_entities,
        'total_extracted_relations': total_extracted_relations,
        'total_saved_relations': total_saved_relations
    }
