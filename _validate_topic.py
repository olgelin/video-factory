import sys
sys.path.insert(0, 'core')
from topic_validator import validate_topic

topics = [
    '贷款中介集体删除朋友圈背后：分润被砍到20%，助贷暴利链条被釜底抽薪',
    'AI医生批量带货卖药：60秒广告报价25.8万，责任该由谁承担',
]
for t in topics:
    ok, r = validate_topic(t)
    print(('PASS' if ok else 'FAIL'), r['score'], '|', t)
    print('  reason:', r.get('reason', ''))
    print()
