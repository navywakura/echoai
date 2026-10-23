import copy
import importlib
import json
from pathlib import Path
import random
import unittest


class CodecTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/wspstudy/codec.py'
        self.assertTrue(path.exists(), 'W codec not implemented')
        self.c=importlib.import_module('echoai.echo58.wspstudy.codec')

    def record(self, index=0):
        return {'version':1, 'packet':[2,14,4,8,0,0,0,0,0,0,0,0,0,0,0,index%256],
                'game_id':'fixture', 'index':index,
                'feedback':{'state':'NOT_FINISHED','levels_completed':0,'win_levels':2,
                            'full_reset':False,'available_actions':[1,6],
                            'action_input':{'id':6,'data':{'x':0,'y':1}}},
                'frame':[[[0,0,2],[0,3,2]],[[4,4]]]}

    def all_roundtrips(self, record, base=None):
        original=copy.deepcopy(record)
        for mode in ('raw','rle','delta'):
            with self.subTest(mode=mode,format='wsp'):
                wire=self.c.encode(record,mode=mode,base=base)
                self.assertEqual(self.c.decode(wire,base=base),record)
            for fmt in ('named','positional','wrapped'):
                with self.subTest(mode=mode,format=fmt):
                    wire=self.c.encode_json(record,fmt,mode=mode,base=base)
                    self.assertEqual(self.c.decode_json(wire,fmt,base=base),record)
        self.assertEqual(record,original)

    def test_multilayer_feedback_and_legacy_packet_roundtrip(self):
        r=self.record();r['packet'][4:10]=[-100,100,-1,1,0,99]
        r['packet'][10:15]=[255,255,0,255,255]
        self.all_roundtrips(r)
        import navi10_wsp as W
        raw=self.c.packet_bytes(r['packet'])
        self.assertEqual(len(raw),16)
        self.assertEqual(raw,W.pack(src=2,rel=14,dst=4,time=8,
                         E=dict(zip(W.E_NAMES,r['packet'][4:10])),flags=255,domain=255,
                         generator=0,style=255,slot=255,seq=0))

    def test_absent_null_false_and_zero_remain_distinct(self):
        records=[]
        for value in ('absent',None,False,0):
            r=self.record();r['feedback'].pop('state')
            if value!='absent':r['feedback']['state']=value
            self.all_roundtrips(r);records.append(self.c.encode(r))
        self.assertEqual(len(set(records)),4)

    def test_json_pipe_unicode_and_nested_action_data(self):
        r=self.record();r['game_id']='a|b→c';r['feedback']['state']='line|with "quotes"'
        r['feedback']['action_input']['data']={'text':'| ☃','x':None,'nested':[False,0,1.5]}
        self.all_roundtrips(r)

    def test_delta_preserves_pixels_with_valid_base(self):
        base=self.record();r=self.record(1);r['frame'][0][1][1]=255
        self.all_roundtrips(r,base)
        text=self.c.encode_json(r,'named',mode='delta',base=base)
        self.assertEqual(json.loads(text)['geometry']['mode'],'delta')
        for changed in ('pixel','game','index'):
            wrong=copy.deepcopy(base)
            if changed=='pixel':wrong['frame'][0][0][0]=1
            if changed=='game':wrong['game_id']='other'
            if changed=='index':wrong['index']=2;wrong['packet'][-1]=2
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                self.c.decode_json(text,'named',base=wrong)
        with self.assertRaises(ValueError):self.c.decode_json(text,'named')

    def test_delta_escapes_to_full_frame_after_context_or_shape_change(self):
        base=self.record()
        for kind in ('reset','shape','game','missing','sequence'):
            r=self.record(1);provided=base
            if kind=='reset':r['feedback']['full_reset']=True
            if kind=='shape':r['frame']=[[[9]]]
            if kind=='game':r['game_id']='different'
            if kind=='missing':provided=None
            if kind=='sequence':r['index']=4;r['packet'][-1]=4
            wire=self.c.encode_json(r,'named',mode='delta',base=provided)
            self.assertNotEqual(json.loads(wire)['geometry']['mode'],'delta')
            self.assertEqual(self.c.decode_json(wire,'named'),r)

    def test_invalid_packet_values_and_pixel_types_rejected(self):
        for pos,value in ((0,256),(1,-1),(4,-101),(5,101),(15,True)):
            r=self.record();r['packet'][pos]=value
            with self.subTest(pos=pos,value=value),self.assertRaises(ValueError):self.c.encode(r)
        for value in (True,-1,256,None,1.5):
            r=self.record();r['frame'][0][0][0]=value
            with self.subTest(pixel=value),self.assertRaises(ValueError):self.c.encode(r)

    def test_nonfinite_unknown_fields_and_oversize_rejected(self):
        for bad in (float('nan'),float('inf'),float('-inf')):
            r=self.record();r['feedback']['action_input']['data']['x']=bad
            with self.assertRaises(ValueError):self.c.encode(r)
        for mutate in (lambda r:r.update(version=2),lambda r:r.update(version=True),
                       lambda r:r.update(extra=1),lambda r:r['feedback'].update(verified=True),
                       lambda r:r.update(frame=[[[0]]]*65),lambda r:r.update(frame=[[[0]*129]])):
            r=self.record();mutate(r)
            with self.assertRaises(ValueError):self.c.encode(r)
        with self.assertRaises(ValueError):self.c.decode('x'*(4*1024*1024+1))

    def test_corrupt_rle_delta_duplicate_keys_and_trailing_bytes_rejected(self):
        r=self.record()
        for payload in ([[0,0]],[[0,10**12]],[[True,8]],[[0,7]]):
            doc=json.loads(self.c.encode_json(r,'named',mode='rle'));doc['geometry']['payload']=payload
            with self.subTest(payload=payload),self.assertRaises(ValueError):
                self.c.decode_json(json.dumps(doc),'named')
        base=r;r=self.record(1);r['frame'][0][0][0]=3
        doc=json.loads(self.c.encode_json(r,'named',mode='delta',base=base))
        for payload in ([[0,3],[0,4]],[[-1,3]],[[99999,3]]):
            doc['geometry']['payload']=payload
            with self.assertRaises(ValueError):self.c.decode_json(json.dumps(doc),'named',base=base)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.c.decode_json('{"version":1,"version":1}','named')
        with self.assertRaises(ValueError):self.c.decode(self.c.encode(r)+' extra')
        with self.assertRaises(ValueError):self.c.decode(self.c.encode(r).replace('W1|','W2|',1))

    def test_lossless_random_frames_across_all_formats(self):
        rng=random.Random(219271)
        base=None
        for index in range(12):
            r=self.record(index)
            r['frame']=[[[rng.randrange(16) for x in range(9)] for y in range(7)]]
            self.all_roundtrips(r,base);base=r

    def test_self_declared_flag_is_only_preserved_data(self):
        r=self.record();r['packet'][10]=128
        self.all_roundtrips(r)
        out=self.c.decode(self.c.encode(r))
        self.assertEqual(set(out),set(r))
        self.assertNotIn('authorized',out)

    def test_all_images_of_long_public_observation_are_preserved(self):
        r=self.record();r['frame']=[[[i%16,0],[0,1]] for i in range(64)]
        self.all_roundtrips(r)
        r['frame'].append([[0]])
        with self.assertRaises(ValueError):self.c.encode(r)

    def test_stream_rejects_replay_context_change_and_keeps_state_on_failure(self):
        self.assertTrue(hasattr(self.c,'StreamDecoder'),'stateful replay/context guard missing')
        receiver=self.c.StreamDecoder('fixture');base=self.record()
        first=self.c.encode(base);self.assertEqual(receiver.consume(first),base)
        with self.assertRaises(ValueError):receiver.consume(first)
        next_record=self.record(1);next_record['frame'][0][0][0]=5
        wire=self.c.encode(next_record,mode='delta',base=base)
        wrong=copy.deepcopy(next_record);wrong['game_id']='another'
        with self.assertRaises(ValueError):receiver.consume(self.c.encode(wrong))
        returned=receiver.consume(wire);returned['frame'][0][0][0]=99
        third=self.record(2)
        self.assertEqual(receiver.consume(self.c.encode(third,mode='delta',base=next_record)),third)

    def test_malformed_delta_metadata_is_rejected_before_restore(self):
        base=self.record();r=self.record(1)
        for key,value in (('feedback',[]),('packet',None),('index',True),('game_id',None)):
            doc=json.loads(self.c.encode_json(r,'named',mode='delta',base=base));doc[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.c.decode_json(json.dumps(doc),'named',base=base)


class CorpusTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/wspstudy/corpus.py'
        self.assertTrue(path.exists(),'public corpus extractor missing')
        self.m=importlib.import_module('echoai.echo58.wspstudy.corpus')

    def source(self):
        return {'timestamp':'excluded','data':{'game_id':'g','guid':'excluded',
            'state':None,'levels_completed':0,'full_reset':False,'frame':[[[0,2]]],
            'action_input':{'id':6,'data':{'x':0},'reasoning':'excluded'}}}

    def test_observation_fields_and_presence_survive_without_model_prose(self):
        src=self.source();original=copy.deepcopy(src);r=self.m.normalise(src,0)
        self.assertEqual(r['frame'],src['data']['frame'])
        self.assertEqual(r['feedback'],{'state':None,'levels_completed':0,'full_reset':False,
                                       'action_input':{'id':6,'data':{'x':0}}})
        self.assertNotIn('excluded',json.dumps(r));self.assertEqual(src,original)
        src['data']['action_input']=None;r=self.m.normalise(src,1)
        self.assertIsNone(r['feedback']['action_input'])
        src['data'].pop('state');r=self.m.normalise(src,2)
        self.assertNotIn('state',r['feedback'])

    def test_manifest_pins_sources_splits_and_exact_selected_records(self):
        import tempfile,hashlib
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'public';source.mkdir();out=p/'corpus'
            for name in ('bp35','s5i5','sp80'):
                with (source/f'{name}-recording.jsonl').open('w') as f:
                    for _ in range(3):f.write(json.dumps(self.source())+'\n')
            manifest=self.m.build(source,out,count=2)
            self.assertEqual({k:v['split'] for k,v in manifest['games'].items()},
                             {'bp35':'calibration','s5i5':'evaluation','sp80':'evaluation'})
            for game,row in manifest['games'].items():
                self.assertEqual(row['records'],2)
                self.assertEqual(row['source_sha256'],hashlib.sha256((source/f'{game}-recording.jsonl').read_bytes()).hexdigest())
                records=[json.loads(x) for x in (out/row['file']).read_text().splitlines()]
                self.assertEqual(records,[self.m.normalise(self.source(),i) for i in range(2)])
            with self.assertRaises(FileExistsError):self.m.build(source,out,count=2)


class GateTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/wspstudy/metrics.py'
        self.assertTrue(path.exists(),'exact token saving gate missing')
        self.m=importlib.import_module('echoai.echo58.wspstudy.metrics')

    def game(self,w=85,j=100,wl=0,jl=0):
        return {'wsp':{'tokens':[w]*64,'legend_tokens':wl},
                'json':{'named':{'tokens':[j]*64,'legend_tokens':jl}}}

    def test_exact_fifteen_percent_boundary(self):
        self.assertTrue(self.m.verdict({'a':self.game(),'b':self.game()})['green'])
        self.assertFalse(self.m.verdict({'a':self.game(86),'b':self.game(86)})['green'])

    def test_median_of_relative_savings_not_ratio_of_medians(self):
        result=self.m.verdict({'a':self.game(88,100),'b':self.game(8400,10000)})
        self.assertEqual(result['median_saving'],{'numerator':7,'denominator':50})
        self.assertTrue(result['total_saving_at_least_15pct'])
        self.assertFalse(result['green'])

    def test_legends_and_per_game_regression_count(self):
        self.assertFalse(self.m.verdict({'a':self.game(80,100,640),'b':self.game(80,100,640)})['green'])
        result=self.m.verdict({'a':self.game(105),'b':self.game(60)})
        self.assertFalse(result['no_game_regression']);self.assertFalse(result['green'])

    def test_best_registered_json_and_compatibility_are_required(self):
        a=self.game();a['json']['wrapped']={'tokens':[98]*64,'legend_tokens':0}
        result=self.m.verdict({'a':a,'b':copy.deepcopy(a)})
        self.assertEqual(result['baseline_by_game'],{'a':'wrapped','b':'wrapped'})
        self.assertFalse(result['green'])
        self.assertFalse(self.m.verdict({'a':self.game(),'b':self.game()},compatibility_green=False)['green'])

    def test_missing_records_or_noninteger_tokens_cannot_pass(self):
        a=self.game();a['wsp']['tokens'].pop()
        with self.assertRaises(ValueError):self.m.verdict({'a':a,'b':self.game()})
        a=self.game();a['json']['named']['tokens'][0]=True
        with self.assertRaises(ValueError):self.m.verdict({'a':a,'b':self.game()})


class PipelineTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/wspstudy/bench.py'
        self.assertTrue(path.exists(),'benchmark pipeline missing')
        self.b=importlib.import_module('echoai.echo58.wspstudy.bench')

    def test_wrong_tokenizer_is_rejected_before_loading(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tokenizer.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'tokenizer hash'):
                self.b.load_tokenizer(p)

    def test_oversized_losing_mode_does_not_discard_valid_message(self):
        record={'version':1,'packet':[2,14,4,8]+[0]*12,'game_id':'boundary','index':0,
            'feedback':{'state':'x'*3650000},'frame':[[[i%2 for i in range(128)] for _ in range(128)] for _ in range(8)]}
        class Tokenizer:
            def encode(self,text,**kw):
                class Encoding:ids=(1,)
                return Encoding()
        codec=importlib.import_module('echoai.echo58.wspstudy.codec')
        self.assertLess(len(codec.dumps(record)),codec.MAX_BYTES)
        row=self.b.best_encoding(record,'wsp',Tokenizer(),None)
        self.assertEqual(row['mode'],'raw')
        self.assertIsNone(row['candidate_tokens']['rle'])

    def test_synthetic_complete_pipeline_and_tamper_detection(self):
        import tempfile
        self.assertTrue((Path(self.b.__file__).parent/'verify.py').exists(),'independent verifier missing')
        audit=importlib.import_module('echoai.echo58.wspstudy.verify')
        tokenizer=Path('/home/user/.local/share/echoai-tools/echo55-tokenizer-v3/data/tokenizer.json')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'public';source.mkdir()
            for game in ('bp35','s5i5','sp80'):
                with (source/f'{game}-recording.jsonl').open('w') as f:
                    for i in range(64):
                        f.write(json.dumps({'data':{'game_id':game,'state':None,
                            'frame':[[[i%2,0],[0,0]]],'action_input':{'id':1,'reasoning':'exclude'}}})+'\n')
            contract=root/'contract.md';contract.write_text('Synthetic plumbing fixture; not an experiment.')
            run=root/'run';self.b.prepare(run,source,tokenizer,contract,fixture=True)
            report=self.b.run(run)
            self.assertTrue(report['fixture']);self.assertFalse(report['exam_run'])
            checked=audit.verify(run)
            self.assertTrue(checked['audit_green'])
            self.assertEqual(checked['records'],192)
            self.assertEqual(checked['messages'],768)
            result_file=run/'results.json'
            for path in [('games','s5i5','wsp','tokens_median_with_legend'),
                         ('games','s5i5','wsp','first_message_with_legend'),
                         ('games','s5i5','wsp','bytes_total_with_legend'),
                         ('verdict','wsp_tokens_total'),('verdict','best_json_tokens_total'),
                         ('verdict','median_saving_at_least_15pct'),
                         ('verdict','total_saving_at_least_15pct'),('records',),('messages',)]:
                changed=copy.deepcopy(report);parent=changed
                for key in path[:-1]:parent=parent[key]
                parent[path[-1]]='invented'
                result_file.write_text(json.dumps(changed))
                with self.assertRaises(ValueError,msg=str(path)):audit.verify(run)
            result_file.write_text(json.dumps(report))
            with self.assertRaises(FileExistsError):self.b.prepare(run,source,tokenizer,contract,fixture=True)
            message=run/'messages/s5i5/wsp.jsonl'
            rows=[json.loads(x) for x in message.read_text().splitlines()]
            rows[0]['message']+='corruption'
            message.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
            with self.assertRaises(ValueError):audit.verify(run)


if __name__=='__main__':unittest.main()
