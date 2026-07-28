from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Specification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    articles = db.relationship('Article', backref='specification', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spec_id = db.Column(db.Integer, db.ForeignKey('specification.id'), nullable=False)
    clause_number = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    entity_tagged = db.Column(db.Boolean, default=False)
    relation_tagged = db.Column(db.Boolean, default=False)
    rule_tagged = db.Column(db.Boolean, default=False)
    
    entities = db.relationship('Entity', secondary='article_entity', backref=db.backref('articles', lazy='dynamic'))
    relations = db.relationship('Relation', secondary='article_relation', backref=db.backref('articles', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'spec_id': self.spec_id,
            'clause_number': self.clause_number,
            'content': self.content,
            'entity_tagged': self.entity_tagged,
            'relation_tagged': self.relation_tagged,
            'rule_tagged': self.rule_tagged
        }

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    entity_type = db.Column(db.String(50), default='实体')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    aliases = db.relationship('EntityAlias', backref='entity', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'description': self.description,
            'aliases': [alias.alias for alias in self.aliases],
            'created_at': self.created_at.isoformat()
        }

class EntityAlias(db.Model):
    """A reviewed alternate surface form mapped to one canonical entity."""
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False, index=True)
    alias = db.Column(db.String(100), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'entity_id': self.entity_id, 'alias': self.alias, 'created_at': self.created_at.isoformat()}


class Relation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('entity.id'), nullable=False)
    relation_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    source = db.relationship('Entity', foreign_keys=[source_id], backref='outgoing_relations')
    target = db.relationship('Entity', foreign_keys=[target_id], backref='incoming_relations')
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'source_name': self.source.name if self.source else '',
            'target_name': self.target.name if self.target else '',
            'relation_type': self.relation_type,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rule_type = db.Column(db.String(50), default='约束规则')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'rule_type': self.rule_type,
            'created_at': self.created_at.isoformat()
        }


class Annotation(db.Model):
    """A reviewable LLM extraction.  It preserves the evidence before graph writes."""
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False, index=True)
    payload = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    model = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied_at = db.Column(db.DateTime)

    article = db.relationship('Article', backref=db.backref('annotations', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'article_id': self.article_id,
            'payload': json.loads(self.payload),
            'status': self.status,
            'model': self.model,
            'created_at': self.created_at.isoformat(),
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'article': {
                'id': self.article.id,
                'spec_id': self.article.spec_id,
                'specification': self.article.specification.code,
                'clause_number': self.article.clause_number,
                'content': self.article.content,
            } if self.article else None,
        }


class Project(db.Model):
    """A reusable design brief. Parameters stay as JSON so the check schema can evolve."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    parameters = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'name': self.name,
            'parameters': json.loads(self.parameters or '{}'),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ComplianceAssessment(db.Model):
    """An immutable assessment item retaining its parameter and clause evidence."""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    run_id = db.Column(db.String(36), nullable=False, index=True)
    category = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # pass / fail / pending / advisory
    parameter_key = db.Column(db.String(80))
    input_value = db.Column(db.String(200))
    expected_value = db.Column(db.String(200))
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
    evidence = db.Column(db.Text)
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('assessments', lazy=True, cascade='all, delete-orphan'))
    article = db.relationship('Article')

    def to_dict(self):
        article = self.article
        return {
            'id': self.id,
            'project_id': self.project_id,
            'run_id': self.run_id,
            'category': self.category,
            'title': self.title,
            'status': self.status,
            'parameter_key': self.parameter_key,
            'input_value': self.input_value,
            'expected_value': self.expected_value,
            'evidence': self.evidence,
            'explanation': self.explanation,
            'created_at': self.created_at.isoformat(),
            'article': {
                'id': article.id,
                'spec_id': article.spec_id,
                'specification': article.specification.code,
                'clause_number': article.clause_number,
                'content': article.content,
            } if article else None,
        }


class AnnotationJob(db.Model):
    """Persistent audit record for a batch extraction request and its retryable failures."""
    id = db.Column(db.Integer, primary_key=True)
    spec_id = db.Column(db.Integer, db.ForeignKey('specification.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='queued')  # queued / running / completed / partial / failed
    requested_article_ids = db.Column(db.Text, nullable=False, default='[]')
    created_annotation_ids = db.Column(db.Text, nullable=False, default='[]')
    failures = db.Column(db.Text, nullable=False, default='[]')
    model = db.Column(db.String(120))
    retry_of_id = db.Column(db.Integer, db.ForeignKey('annotation_job.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    specification = db.relationship('Specification')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'spec_id': self.spec_id,
            'specification': self.specification.code if self.specification else None,
            'status': self.status,
            'requested_article_ids': json.loads(self.requested_article_ids or '[]'),
            'created_annotation_ids': json.loads(self.created_annotation_ids or '[]'),
            'failures': json.loads(self.failures or '[]'),
            'model': self.model,
            'retry_of_id': self.retry_of_id,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

article_entity = db.Table('article_entity',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('entity_id', db.Integer, db.ForeignKey('entity.id'), primary_key=True)
)

article_relation = db.Table('article_relation',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('relation_id', db.Integer, db.ForeignKey('relation.id'), primary_key=True)
)
