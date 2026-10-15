import argparse, importlib, json
from pathlib import Path

def run(engine='challenge:Engine'):
    module, name = engine.split(':')
    cls = getattr(importlib.import_module(module), name)
    data = json.loads((Path(__file__).parent/'data.json').read_text(encoding='utf-8'))
    instance = cls(); output=[]
    for case in data['cases']:
        if case['reset_before']: instance=cls()
        output.append({'case_id': case['id'], 'input': case,
                       'output': instance.evaluate(case['request'], data['corpus'], case['draft'])})
    return output

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--engine',default='challenge:Engine')
    p.add_argument('--output',default='runs/baseline.json'); a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(run(a.engine),ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(out.resolve()))
