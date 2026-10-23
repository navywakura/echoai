"""Strict transport adapter. The existing WSP16 packet and core are unchanged."""
import hashlib
import json
import math

import navi10_wsp as W

MAX_BYTES=4*1024*1024
MAX_LAYERS=64
FEEDBACK=('state','levels_completed','win_levels','full_reset','available_actions','action_input')
FORMATS=('named','positional','wrapped')
MODES=('raw','rle','delta')


def require(value,message):
    if not value:raise ValueError(message)


def integer(value,low,high):
    require(type(value) is int and low<=value<=high,'integer out of bounds')
    return value


def dumps(value):
    try:return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',', ':'),allow_nan=False)
    except (TypeError,ValueError,RecursionError) as exc:raise ValueError('invalid JSON value') from exc


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def pairs(items):
    out={}
    for key,value in items:
        require(key not in out,'duplicate JSON key')
        out[key]=value
    return out


def constant(_):
    raise ValueError('nonfinite JSON number')


DECODER=json.JSONDecoder(object_pairs_hook=pairs,parse_constant=constant)


def checked_text(text):
    require(type(text) is str,'text required')
    try:require(len(text.encode('utf-8'))<=MAX_BYTES,'message exceeds limit')
    except UnicodeError as exc:raise ValueError('invalid UTF-8 text') from exc
    return text


def loads(text):
    checked_text(text)
    try:
        value,end=DECODER.raw_decode(text.lstrip())
        require(not text.lstrip()[end:].strip(),'trailing JSON data')
        return value
    except (json.JSONDecodeError,RecursionError) as exc:raise ValueError('invalid JSON document') from exc


def json_value(value,depth=0):
    require(depth<=32,'metadata depth limit')
    if value is None or type(value) in (str,bool,int):return
    if type(value) is float:
        require(math.isfinite(value),'nonfinite JSON number');return
    if type(value) is list:
        require(len(value)<=65536,'metadata collection limit')
        for v in value:json_value(v,depth+1)
        return
    if type(value) is dict:
        require(len(value)<=65536 and all(type(k) is str for k in value),'JSON string keys required')
        for v in value.values():json_value(v,depth+1)
        return
    raise ValueError('unsupported metadata value')


def packet_bytes(values):
    require(type(values) is list and len(values)==16,'sixteen packet values required')
    for i,value in enumerate(values):integer(value,-100 if 4<=i<10 else 0,100 if 4<=i<10 else 255)
    return W.pack(src=values[0],rel=values[1],dst=values[2],time=values[3],
        E=dict(zip(W.E_NAMES,values[4:10])),flags=values[10],domain=values[11],
        generator=values[12],style=values[13],slot=values[14],seq=values[15])


def shapes(frame):
    require(type(frame) is list and 1<=len(frame)<=MAX_LAYERS,'one to sixty-four layers required')
    out=[]
    for layer in frame:
        require(type(layer) is list and 1<=len(layer)<=128,'layer height out of bounds')
        require(type(layer[0]) is list and 1<=len(layer[0])<=128,'layer width out of bounds')
        width=len(layer[0])
        for row in layer:
            require(type(row) is list and len(row)==width,'ragged frame')
            for color in row:integer(color,0,255)
        out.append([len(layer),width])
    return out


def validate_metadata(record):
    require(type(record['version']) is int and record['version']==1,'unknown container version')
    packet_bytes(record['packet'])
    require(type(record['game_id']) is str and 1<=len(record['game_id'])<=256,'game context required')
    integer(record['index'],0,2**31-1)
    require(record['packet'][15]==record['index']%256,'packet/context sequence mismatch')
    feedback=record['feedback']
    require(type(feedback) is dict and set(feedback)<=set(FEEDBACK),'unknown feedback namespace')
    if 'action_input' in feedback and feedback['action_input'] is not None:
        require(type(feedback['action_input']) is dict and set(feedback['action_input'])<={'id','data'},'action schema')
    json_value(feedback)


def validate_record(record):
    require(type(record) is dict and set(record)=={'version','packet','game_id','index','feedback','frame'},'record schema')
    validate_metadata(record)
    shapes(record['frame'])
    checked_text(dumps(record))


def feedback_values(feedback):
    mask=sum(1<<i for i,key in enumerate(FEEDBACK) if key in feedback)
    return [mask]+[feedback[key] for key in FEEDBACK if key in feedback]


def feedback_dict(values):
    require(type(values) is list and bool(values),'feedback presence mask required')
    mask=integer(values[0],0,(1<<len(FEEDBACK))-1)
    require(len(values)==1+mask.bit_count(),'feedback presence/value count mismatch')
    return dict(zip([key for i,key in enumerate(FEEDBACK) if mask&(1<<i)],values[1:]))


def flattened(frame):
    return [pixel for layer in frame for row in layer for pixel in row]


def delta_base(record,base):
    if base is None:return False
    validate_record(base)
    return (record['game_id']==base['game_id'] and record['index']==base['index']+1
            and record['feedback'].get('full_reset') is not True
            and shapes(record['frame'])==shapes(base['frame']))


def geometry(record,mode,base):
    require(mode in MODES,'unknown geometry mode')
    ss=shapes(record['frame']);flat=flattened(record['frame'])
    if mode=='delta' and not delta_base(record,base):mode='raw'
    if mode=='raw':payload=flat
    elif mode=='rle':
        payload=[]
        for color in flat:
            if payload and payload[-1][0]==color:payload[-1][1]+=1
            else:payload.append([color,1])
    else:
        payload=[[i,color] for i,(color,old) in enumerate(zip(flat,flattened(base['frame']))) if color!=old]
    out={'mode':mode,'shapes':ss,'payload':payload}
    if mode=='delta':out['base']=digest(base['frame'])
    return out


def restore_geometry(g,record,base):
    require(type(g) is dict and g.get('mode') in MODES,'geometry schema/mode')
    mode=g['mode']
    require(set(g)==({'mode','shapes','payload','base'} if mode=='delta' else {'mode','shapes','payload'}),'geometry fields')
    ss=g['shapes']
    require(type(ss) is list and 1<=len(ss)<=MAX_LAYERS,'geometry layer count')
    total=0
    for s in ss:
        require(type(s) is list and len(s)==2,'shape pair required')
        total+=integer(s[0],1,128)*integer(s[1],1,128)
    payload=g['payload'];require(type(payload) is list,'geometry payload list required')
    if mode=='raw':
        require(len(payload)==total,'raw pixel count')
        flat=[integer(v,0,255) for v in payload]
    elif mode=='rle':
        flat=[]
        for pair in payload:
            require(type(pair) is list and len(pair)==2,'RLE pair required')
            color=integer(pair[0],0,255);count=integer(pair[1],1,total-len(flat))
            flat.extend([color]*count)
        require(len(flat)==total,'RLE pixel count')
    else:
        require(base is not None,'delta base missing');validate_record(base)
        require(record['game_id']==base['game_id'] and record['index']==base['index']+1,'delta context/sequence')
        require(record['feedback'].get('full_reset') is not True,'delta after reset')
        require(ss==shapes(base['frame']) and g['base']==digest(base['frame']),'delta base checksum/shape')
        flat=flattened(base['frame']);last=-1
        for pair in payload:
            require(type(pair) is list and len(pair)==2,'delta pair required')
            index=integer(pair[0],0,total-1);require(index>last,'duplicate or unordered delta index')
            flat[index]=integer(pair[1],0,255);last=index
    frame=[];offset=0
    for height,width in ss:
        frame.append([flat[offset+y*width:offset+(y+1)*width] for y in range(height)])
        offset+=height*width
    return frame


def encode(record,*,mode='raw',base=None):
    validate_record(record)
    packet=','.join(map(str,record['packet']))
    meta=[record['game_id'],record['index'],feedback_values(record['feedback'])]
    return checked_text('W1|'+packet+'|'+dumps(meta)+'|'+dumps(geometry(record,mode,base)))


def decode(text,*,base=None):
    checked_text(text)
    parts=text.split('|',2)
    require(len(parts)==3 and parts[0]=='W1','unknown WSP container namespace')
    pieces=parts[1].split(',');require(len(pieces)==16,'sixteen packet values required')
    try:
        packet=[int(v) for v in pieces]
        require(all(str(n)==s for n,s in zip(packet,pieces)),'noncanonical packet integer')
        meta,end=DECODER.raw_decode(parts[2])
    except (ValueError,RecursionError) as exc:raise ValueError('invalid packet/metadata') from exc
    require(type(meta) is list and len(meta)==3,'WSP metadata schema')
    require(parts[2][end:end+1]=='|','geometry delimiter missing')
    g=loads(parts[2][end+1:])
    record={'version':1,'packet':packet,'game_id':meta[0],'index':meta[1],
            'feedback':feedback_dict(meta[2])}
    validate_metadata(record)
    record['frame']=restore_geometry(g,record,base)
    validate_record(record)
    return record


def encode_json(record,fmt,*,mode='raw',base=None):
    require(fmt in FORMATS,'unknown JSON container namespace');validate_record(record)
    if fmt=='wrapped':return checked_text(dumps(encode(record,mode=mode,base=base)))
    g=geometry(record,mode,base)
    if fmt=='named':doc={key:record[key] for key in record if key!='frame'};doc['geometry']=g
    else:doc=[1,record['packet'],record['game_id'],record['index'],feedback_values(record['feedback']),g]
    return checked_text(dumps(doc))


def decode_json(text,fmt,*,base=None):
    require(fmt in FORMATS,'unknown JSON container namespace');doc=loads(text)
    if fmt=='wrapped':
        require(type(doc) is str,'wrapped WSP string required');return decode(doc,base=base)
    if fmt=='named':
        require(type(doc) is dict and set(doc)=={'version','packet','game_id','index','feedback','geometry'},'named JSON schema')
        record={key:value for key,value in doc.items() if key!='geometry'};g=doc['geometry']
    else:
        require(type(doc) is list and len(doc)==6,'positional JSON schema')
        record={'version':doc[0],'packet':doc[1],'game_id':doc[2],'index':doc[3],
                'feedback':feedback_dict(doc[4])};g=doc[5]
    validate_metadata(record)
    record['frame']=restore_geometry(g,record,base)
    validate_record(record)
    return record


class StreamDecoder:
    """A pinned game stream. Failed input never advances the expected sequence."""
    def __init__(self,game_id):
        require(type(game_id) is str and 1<=len(game_id)<=256,'game context required')
        self.game_id=game_id
        self._last=None
        self._next=0

    def consume(self,text,fmt='wsp'):
        record=decode(text,base=self._last) if fmt=='wsp' else decode_json(text,fmt,base=self._last)
        require(record['game_id']==self.game_id and record['index']==self._next,'replay/context/sequence rejected')
        self._last=loads(dumps(record))
        self._next+=1
        return record
