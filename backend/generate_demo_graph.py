"""Build a local, no-API knowledge-graph demonstration from two bundled codes.

The script deliberately labels the output as `local-demo` in descriptions.  It
is intended for visual demonstration when an external LLM key is unavailable;
real LLM annotations remain reviewable through the application's UI.
"""
import re

from models import Article, Entity, Relation, Rule, Specification, db


VOCABULARY = {
    '抗震设计': '性能指标', '抗震设防烈度': '性能指标', '抗震等级': '性能指标',
    '地震作用': '性能指标', '地震影响': '性能指标', '场地类别': '建筑对象',
    '建筑结构': '建筑对象', '结构体系': '建筑对象', '结构构件': '部位',
    '混凝土结构': '建筑对象', '钢结构': '建筑对象', '砌体结构': '建筑对象',
    '框架结构': '建筑对象', '剪力墙': '部位', '基础': '部位',
    '住宅': '建筑对象', '住宅建筑': '建筑对象', '卧室': '部位',
    '起居室': '部位', '厨房': '部位', '卫生间': '部位', '阳台': '部位',
    '电梯': '部位', '楼梯': '部位', '走道': '部位', '层高': '性能指标',
    '净高': '性能指标', '采光': '性能指标', '通风': '性能指标',
    '无障碍': '性能指标', '安全': '性能指标', '防火': '性能指标'
}
CONSTRAINTS = ('不应小于', '不应大于', '不得小于', '不得大于', '不得超过', '不应超过', '必须', '严禁', '应')


def sentences(text):
    return [part.strip() for part in re.split(r'[。；;\n]', text) if part.strip()]


def value_entities(sentence):
    return list(dict.fromkeys(re.findall(r'(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:m²|㎡|mm|cm|m|米|层|%|级|度|人|户|年)', sentence)))


def get_entity(name, entity_type, evidence):
    entity = Entity.query.filter_by(name=name).first()
    if not entity:
        entity = Entity(name=name, entity_type=entity_type, description=f'local-demo｜证据：{evidence}')
        db.session.add(entity)
        db.session.flush()
    return entity


def add_relation(article, source, predicate, target, evidence):
    if source.id == target.id:
        return False
    relation = Relation.query.filter_by(source_id=source.id, target_id=target.id, relation_type=predicate).first()
    if not relation:
        relation = Relation(source_id=source.id, target_id=target.id, relation_type=predicate, description=f'local-demo｜证据：{evidence}')
        db.session.add(relation)
        db.session.flush()
    if relation not in article.relations:
        article.relations.append(relation)
    return True


def extract_article(article):
    created = {'entities': 0, 'relations': 0, 'rules': 0}
    for sentence in sentences(article.content):
        mentions = [name for name in VOCABULARY if name in sentence]
        numeric_values = value_entities(sentence)
        entities = {}
        for name in mentions:
            before = Entity.query.filter_by(name=name).first()
            entity = get_entity(name, VOCABULARY[name], sentence)
            if before is None:
                created['entities'] += 1
            entities[name] = entity
            if entity not in article.entities:
                article.entities.append(entity)
        for value in numeric_values:
            before = Entity.query.filter_by(name=value).first()
            entity = get_entity(value, '数值', sentence)
            if before is None:
                created['entities'] += 1
            entities[value] = entity
            if entity not in article.entities:
                article.entities.append(entity)

        predicate = next((item for item in CONSTRAINTS if item in sentence), None)
        if predicate and entities:
            source = next((entities[name] for name in mentions if VOCABULARY[name] != '数值'), None)
            target = next((entities[value] for value in numeric_values), None)
            if source and target and add_relation(article, source, predicate, target, sentence):
                created['relations'] += 1
            rule_name = f'{article.clause_number} 条文约束'
            if not Rule.query.filter_by(name=rule_name, content=sentence).first():
                db.session.add(Rule(name=rule_name, content=sentence, rule_type='本地示例规则'))
                created['rules'] += 1
        elif len(mentions) >= 2:
            source, target = entities[mentions[0]], entities[mentions[1]]
            if add_relation(article, source, '关联', target, sentence):
                created['relations'] += 1
    if created['entities']:
        article.entity_tagged = True
    if created['relations']:
        article.relation_tagged = True
    if created['rules']:
        article.rule_tagged = True
    return created


def main():
    specs = Specification.query.filter(
        (Specification.code.like('GB50011%')) | (Specification.code.like('GB50096%'))
    ).all()
    if len(specs) != 2:
        raise RuntimeError(f'应找到 2 份演示规范，实际找到 {len(specs)} 份')
    totals = {'articles': 0, 'entities': 0, 'relations': 0, 'rules': 0}
    for spec in specs:
        for article in Article.query.filter_by(spec_id=spec.id).all():
            totals['articles'] += 1
            extracted = extract_article(article)
            for key in ('entities', 'relations', 'rules'):
                totals[key] += extracted[key]
        db.session.commit()
    print(totals)


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        main()
