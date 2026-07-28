"""OpenAI-compatible LLM extraction for Chinese building-code clauses."""
import json
import re
from urllib import error, request


SYSTEM_PROMPT = '''你是建筑设计规范知识工程专家。仅根据给定条文抽取可追溯知识，不能补充条文没有表达的事实。
输出严格 JSON，且必须符合以下结构：
{
  "entities": [{"name":"实体名称","type":"建筑对象|部位|性能指标|数值|标准|行为|其他","evidence":"原文片段","confidence":0.0}],
  "relations": [{"source":"实体名称","predicate":"适用范围|具有属性|应满足|不得超过|不应小于|不应大于|必须执行|禁止|包含|其他","target":"实体名称","evidence":"原文片段","confidence":0.0}],
  "rules": [{"name":"简短规则名","rule_type":"强制性条文|约束规则|适用范围","content":"可验证的条件—要求表述","evidence":"原文片段","confidence":0.0}]
}
每个 evidence 必须为条文的连续原文。没有内容则返回空数组。置信度在 0 到 1 之间。'''


class LLMExtractionError(Exception):
    pass


def configured(config):
    return bool(config.get('LLM_API_KEY'))


def _parse_json(content):
    content = content.strip()
    content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.I)
    match = re.search(r'\{[\s\S]*\}', content)
    if not match:
        raise LLMExtractionError('模型未返回 JSON 标注结果')
    try:
        result = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMExtractionError(f'模型返回的 JSON 无法解析：{exc.msg}') from exc
    if not isinstance(result, dict):
        raise LLMExtractionError('模型返回结果必须是 JSON 对象')
    return {key: result.get(key, []) for key in ('entities', 'relations', 'rules')}


def extract_clause(config, clause_number, clause_text):
    if not configured(config):
        raise LLMExtractionError('未配置 LLM_API_KEY。请在 backend/.env 中设置 API 密钥后重启服务。')

    base_url = config['LLM_BASE_URL'].rstrip('/')
    body = {
        'model': config['LLM_MODEL'],
        'temperature': 0,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f'条文号：{clause_number}\n条文：{clause_text}'}
        ]
    }
    req = request.Request(
        f'{base_url}/chat/completions',
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': f"Bearer {config['LLM_API_KEY']}", 'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with request.urlopen(req, timeout=config['LLM_TIMEOUT_SECONDS']) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:500]
        raise LLMExtractionError(f'LLM API 请求失败（HTTP {exc.code}）：{detail}') from exc
    except error.URLError as exc:
        raise LLMExtractionError(f'无法连接 LLM API：{exc.reason}') from exc

    try:
        content = payload['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMExtractionError('LLM API 响应中缺少 choices[0].message.content') from exc
    return _parse_json(content)
