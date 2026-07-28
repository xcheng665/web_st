"""Evidence-first design compliance checks for the currently imported standards.

The module intentionally only emits a passing/failing verdict where the input
and a mandatory clause can be matched deterministically. Everything else stays
pending rather than pretending that a partial local knowledge base is complete.
"""
from dataclasses import dataclass
from typing import Any

from models import Article, Specification


SCHEMA = [
    {'key': 'occupancy', 'label': '建筑用途', 'group': '建筑总体', 'type': 'select', 'options': ['住宅', '公共建筑', '厂房', '仓库']},
    {'key': 'building_height_m', 'label': '建筑高度', 'group': '建筑总体', 'type': 'number', 'unit': 'm'},
    {'key': 'floor_count', 'label': '地上层数', 'group': '建筑总体', 'type': 'number', 'unit': '层'},
    {'key': 'fire_resistance_level', 'label': '耐火等级', 'group': '防火', 'type': 'select', 'options': ['一级', '二级', '三级', '四级']},
    {'key': 'fire_compartment_area_m2', 'label': '最大防火分区面积', 'group': '防火', 'type': 'number', 'unit': '㎡'},
    {'key': 'evacuation_distance_m', 'label': '最大疏散距离', 'group': '空间与疏散', 'type': 'number', 'unit': 'm'},
    {'key': 'stairwell_type', 'label': '疏散楼梯间形式', 'group': '空间与疏散', 'type': 'select', 'options': ['敞开楼梯间', '封闭楼梯间', '防烟楼梯间', '室外楼梯']},
    {'key': 'apartment_usable_area_m2', 'label': '住宅套型使用面积', 'group': '住宅空间', 'type': 'number', 'unit': '㎡'},
    {'key': 'double_bedroom_area_m2', 'label': '双人卧室使用面积', 'group': '住宅空间', 'type': 'number', 'unit': '㎡'},
    {'key': 'bedroom_clear_height_m', 'label': '卧室净高', 'group': '住宅空间', 'type': 'number', 'unit': 'm'},
    {'key': 'living_room_clear_height_m', 'label': '起居室净高', 'group': '住宅空间', 'type': 'number', 'unit': 'm'},
    {'key': 'kitchen_area_m2', 'label': '厨房使用面积', 'group': '住宅空间', 'type': 'number', 'unit': '㎡'},
    {'key': 'kitchen_clear_height_m', 'label': '厨房净高', 'group': '住宅空间', 'type': 'number', 'unit': 'm'},
    {'key': 'bathroom_clear_height_m', 'label': '卫生间净高', 'group': '住宅空间', 'type': 'number', 'unit': 'm'},
    {'key': 'has_elevator', 'label': '已设置电梯', 'group': '无障碍与设施', 'type': 'boolean'},
    {'key': 'accessible_entrance', 'label': '建筑入口已做无障碍设计', 'group': '无障碍与设施', 'type': 'boolean'},
    {'key': 'seismic_intensity', 'label': '抗震设防烈度', 'group': '抗震结构', 'type': 'select', 'options': ['6', '7', '8', '9']},
    {'key': 'seismic_design_confirmed', 'label': '已完成抗震设计', 'group': '抗震结构', 'type': 'boolean'},
    {'key': 'site_class', 'label': '场地类别', 'group': '抗震结构', 'type': 'select', 'options': ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ']},
    {'key': 'structural_system', 'label': '结构体系', 'group': '抗震结构', 'type': 'text'},
    {'key': 'persons_per_floor', 'label': '任一层最大人数', 'group': '厂房补充条件', 'type': 'number', 'unit': '人'},
]


@dataclass
class Check:
    category: str
    title: str
    status: str
    parameter_key: str
    input_value: Any
    expected_value: str
    article: Article | None
    explanation: str

    def to_dict(self):
        article = self.article
        return {
            'category': self.category,
            'title': self.title,
            'status': self.status,
            'parameter_key': self.parameter_key,
            'input_value': self.input_value,
            'expected_value': self.expected_value,
            'explanation': self.explanation,
            'evidence': article.content if article else None,
            'article': {
                'id': article.id,
                'spec_id': article.spec_id,
                'specification': article.specification.code,
                'clause_number': article.clause_number,
                'content': article.content,
            } if article else None,
        }


def _article(code_prefix: str, clause_number: str) -> Article | None:
    spec = Specification.query.filter(Specification.code.like(f'{code_prefix}%')).first()
    return Article.query.filter_by(spec_id=spec.id, clause_number=clause_number).first() if spec else None


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _min_check(parameters, key, minimum, title, article, category='住宅空间'):
    value = _number(parameters.get(key))
    if value is None:
        return Check(category, title, 'pending', key, None, f'不低于 {minimum}', article, '尚未录入该参数，无法自动判定。')
    status = 'pass' if value >= minimum else 'fail'
    return Check(category, title, status, key, value, f'不低于 {minimum}', article, '参数与条文中的明确下限已自动比对。')


def run_checks(parameters: dict) -> list[Check]:
    checks: list[Check] = []
    occupancy = str(parameters.get('occupancy') or '')
    residential = occupancy == '住宅'

    if residential:
        checks.extend([
            _min_check(parameters, 'apartment_usable_area_m2', 30, '住宅套型使用面积', _article('GB50096', '5.1.2')),
            _min_check(parameters, 'double_bedroom_area_m2', 9, '双人卧室使用面积', _article('GB50096', '5.2.1')),
            _min_check(parameters, 'bedroom_clear_height_m', 2.4, '卧室室内净高', _article('GB50096', '5.5.2')),
            _min_check(parameters, 'living_room_clear_height_m', 2.4, '起居室室内净高', _article('GB50096', '5.5.2')),
            _min_check(parameters, 'kitchen_area_m2', 4, '住宅厨房使用面积', _article('GB50096', '5.3.1')),
            _min_check(parameters, 'kitchen_clear_height_m', 2.2, '厨房室内净高', _article('GB50096', '5.5.4')),
            _min_check(parameters, 'bathroom_clear_height_m', 2.2, '卫生间室内净高', _article('GB50096', '5.5.4')),
        ])
        floors = _number(parameters.get('floor_count'))
        if floors is None:
            checks.append(Check('无障碍与设施', '七层及以上住宅电梯', 'pending', 'floor_count', None, '七层及以上必须设置电梯', _article('GB50096', '6.4.1'), '需要先录入住宅层数。'))
            checks.append(Check('无障碍与设施', '七层及以上住宅入口无障碍', 'pending', 'floor_count', None, '七层及以上入口应进行无障碍设计', _article('GB50096', '6.6.1'), '需要先录入住宅层数。'))
        elif floors >= 7:
            elevator = parameters.get('has_elevator')
            entrance = parameters.get('accessible_entrance')
            checks.append(Check('无障碍与设施', '七层及以上住宅电梯', 'pass' if elevator is True else 'fail', 'has_elevator', elevator, '必须设置电梯', _article('GB50096', '6.4.1'), '已按强制性条文自动判定。'))
            checks.append(Check('无障碍与设施', '七层及以上住宅入口无障碍', 'pass' if entrance is True else 'fail', 'accessible_entrance', entrance, '入口应进行无障碍设计', _article('GB50096', '6.6.1'), '已按条文适用条件自动判定。'))
        else:
            checks.append(Check('无障碍与设施', '住宅电梯设置', 'advisory', 'floor_count', floors, '本条仅适用于七层及以上住宅', _article('GB50096', '6.4.1'), '当前层数不触发该条文的强制条件。'))

    intensity = _number(parameters.get('seismic_intensity'))
    if intensity is None:
        checks.append(Check('抗震结构', '6度及以上地区抗震设计', 'pending', 'seismic_intensity', None, '6度及以上必须进行抗震设计', _article('GB50011', '1.0.2'), '未填写设防烈度。'))
    elif intensity >= 6:
        confirmed = parameters.get('seismic_design_confirmed')
        checks.append(Check('抗震结构', '6度及以上地区抗震设计', 'pass' if confirmed is True else 'fail', 'seismic_design_confirmed', confirmed, '必须进行抗震设计', _article('GB50011', '1.0.2'), '已按设防烈度与项目确认状态自动判定。'))

    height = _number(parameters.get('building_height_m'))
    people = _number(parameters.get('persons_per_floor'))
    if occupancy == '厂房' and height is not None and people is not None and height > 32 and people > 10:
        stairs = parameters.get('stairwell_type')
        allowed = {'防烟楼梯间', '室外楼梯'}
        checks.append(Check('空间与疏散', '高层厂房疏散楼梯间', 'pass' if stairs in allowed else 'fail', 'stairwell_type', stairs, '应采用防烟楼梯间或室外楼梯', _article('GB50016', '3.7.6'), '已按厂房高度、人数和楼梯间形式自动判定。'))

    checks.extend([
        Check('防火', '防火分区面积', 'pending', 'fire_compartment_area_m2', parameters.get('fire_compartment_area_m2'), '需要建筑类别、火灾危险性与灭火系统条件', _article('GB50016', '3.3.3'), '当前数据尚不足以确定适用的面积上限。'),
        Check('空间与疏散', '最大疏散距离', 'pending', 'evacuation_distance_m', parameters.get('evacuation_distance_m'), '需要使用功能、出口与疏散条件', None, '当前规范库未抽取到可直接用于该项目的完整距离规则。'),
        Check('抗震结构', '结构体系与场地条件', 'pending', 'structural_system', parameters.get('structural_system'), '需要设防类别、场地条件与结构高度的组合规则', _article('GB50011', '3.3.2'), '已定位相关条文，仍需补充适用前提与人工审核。'),
    ])
    return checks
