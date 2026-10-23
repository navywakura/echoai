"""Existing WSP16 postcards; authenticated author is supplied by the controller."""
import copy
import json

from ..enjambre.team import ACTS,L1,L2,RM,Board as LegacyBoard,read
from ..memx.memory import OUTCOMES

ATTACKS=('false_safe','false_alarm','false_remote')
BAD=frozenset(('NOOP','HURT'))


def require(value,message):
    if not value:raise ValueError(message)


def token(layer,key):return json.dumps([layer,list(key)],separators=(',',':'))


def decode(raw,author=None):
    require(type(raw) is bytes and len(raw)==16,'WSP16 bytes required')
    require(raw[11] in (L1,L2,RM),'postcard namespace')
    if raw[11]!=RM:require(raw[1]<len(ACTS) and raw[2]<len(OUTCOMES),'action/outcome bounds')
    layer,sender,key,o,n,total=read(raw)
    require(sender in range(4),'author bounds')
    if author is not None:require(type(author) is int and author==sender,'author mismatch')
    require(n<=total,'count exceeds denominator')
    if layer in (L1,RM):require(key[0]!=0,'identity zero')
    if layer==RM:require(key[1]!=0,'remote identity zero')
    return layer,sender,key,o,n,total


def eligible(claim):
    _outcome,n,total=claim
    return n>=3 and n*100>=85*total


class Board(LegacyBoard):
    def __init__(self):
        super().__init__();self.records=[];self.provenance={}

    def post(self,raw,*,author,round,original):
        layer,sender,key,*_=decode(raw,author);decode(original,author)
        require(type(round) is int and 1<=round<=30,'round bounds')
        super().post(raw)
        index=len(self.records)
        self.records.append({'index':index,'author':author,'round':round,
            'original':original.hex(),'sent':raw.hex(),'altered':raw!=original})
        self.provenance.setdefault((layer,key),{})[sender]=index

    def snapshot(self):return copy.deepcopy(self.latest),copy.deepcopy(self.provenance)


class Attacker:
    def __init__(self,author,attack):
        require(type(author) is int and author in range(4),'author bounds')
        require(attack in ATTACKS,'unknown attack')
        self.author=author;self.attack=attack;self.ids=set()

    def transform(self,cards,round):
        parsed=[decode(raw,self.author) for raw in cards]
        for layer,_sender,key,*_ in parsed:
            if layer==L1:self.ids.update(i for i in (key[0],key[3]) if i)
            elif layer==RM:self.ids.update(i for i in key if i)
        out=[]
        for raw,(layer,_sender,key,o,n,total) in zip(cards,parsed):
            sent=bytearray(raw)
            if layer!=RM:
                outcome=OUTCOMES[o]
                if (self.attack=='false_safe' and outcome in BAD) or (self.attack=='false_alarm' and outcome not in BAD):
                    sent[2]=OUTCOMES.index('PASS' if self.attack=='false_safe' else 'HURT')
                    sent[14]=sent[15]=255
            elif self.attack=='false_remote':
                choices=sorted(self.ids-set(key))
                if choices:sent[2]=choices[0];sent[14]=sent[15]=255
            sent=bytes(sent);decode(sent,self.author);out.append((raw,sent))
        return out
