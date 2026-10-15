"""导出运行清单，不替代候选人的判分。每次失败/重试保留独立行。"""
import argparse,json,csv
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('runs');p.add_argument('output');a=p.parse_args()
    fields=['run_id','case_id','condition','variant','mode','status','model','utc','elapsed_seconds','input_characters','prompt_tokens','completion_tokens','content']
    with open(a.output,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for path in sorted(Path(a.runs).glob('*.json')):
            r=json.loads(path.read_text(encoding='utf-8')); row={k:r.get(k,'') for k in fields}
            row['model']=r.get('config',{}).get('model','');u=r.get('usage') or {}
            row['prompt_tokens']=u.get('prompt_tokens','');row['completion_tokens']=u.get('completion_tokens','')
            try:row['content']=r['response']['choices'][0]['message']['content']
            except (KeyError,TypeError,IndexError):row['content']=''
            w.writerow(row)
if __name__=='__main__':main()
