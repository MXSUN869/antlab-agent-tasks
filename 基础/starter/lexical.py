"""Public, frozen lexical comparator K. It uses only the current question and R0 passage content."""
import re
def select(question, passages):
    terms=re.findall(r'[\u4e00-\u9fff]{2}项目|R\d+|\d{4}-\d{2}',question)
    grams={question[i:i+2] for i in range(len(question)-1)}
    def score(p):
        body=p['text']
        return sum(t in body for t in terms),sum(g in body for g in grams)
    return sorted(passages,key=score,reverse=True)[:2]
