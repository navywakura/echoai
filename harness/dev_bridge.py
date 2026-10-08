"""Private developer adapter. Uses installed ECHO code; never ship in harness wheels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from local_bridge import ROOT, ARC_PYTHON, emit, new_run
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
ED4 = 'echo-4.0-cognitive-agentic'
ED45 = 'echo-4.5-adaptative-agentic'
SETTINGS = ROOT / 'lab/echo-nexus/live-agent.json'
HIST = ROOT / 'lab/final/echo45-20260928'


def read(path):
    return json.loads(Path(path).read_text())


def settings():
    return read(SETTINGS)


def receipt(agent, test):
    cfg = settings()
    paths = ['echo_arc/agent.py', 'seed/refinement.py', 'seed/learn.py', 'harness/dev_bridge.py']
    evidence = {'agent': agent, 'test': test, 'development': True,
                'arc_policy': 'v2' if agent == ED4 else cfg['arc_policy'],
                'sources': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
    out = new_run(test)
    (out / 'source-receipt.json').write_text(json.dumps(evidence, indent=2))
    emit({'kind': 'start', 'text': f"{agent} · código local · ARC policy {evidence['arc_policy']} · "
          f"{evidence['sources']['echo_arc/agent.py'][:12]} · desarrollo; S6 no se certifica aquí"})
    return cfg, out, evidence['arc_policy']


class DeveloperWorld:
    """A pixel-only navigation environment; viewer metadata is emitted separately."""
    def __init__(self, path):
        self.spec = read(path)
        self.w, self.h = self.spec['size']
        if not (3 <= self.w <= 14 and 3 <= self.h <= 14):
            raise ValueError('El mundo debe medir entre 3 y 14 celdas por eje')
        self.walls = {tuple(p) for p in self.spec['walls']}
        self.goal = tuple(self.spec['goal'])
        if any(not (0 <= x < self.w and 0 <= y < self.h) for x, y in self.walls | {self.goal, tuple(self.spec['start'])}):
            raise ValueError('Coordenada fuera del mundo')
        if self.goal in self.walls or tuple(self.spec['start']) in self.walls:
            raise ValueError('Inicio o meta dentro de un obstáculo')
        if not 1 <= self.spec['episode_limit'] <= 2000:
            raise ValueError('El límite del episodio debe estar entre 1 y 2000')
        self.pos, self.direction, self.steps = tuple(self.spec['start']), (1, 0), 0
    def observation(self, state):
        import numpy as np
        from seed.arc3gym import Obs
        f = np.zeros((64, 64), dtype=np.int8)
        for y in range(self.h):
            for x in range(self.w):
                color = 5 if (x, y) in self.walls else 1
                if (x, y) == self.goal: color = 3
                if (x, y) == self.pos: color = 9
                f[2+y*4:6+y*4, 2+x*4:6+x*4] = color
        return Obs(f, [1, 2, 3, 4], int(self.pos == self.goal), state, 1)
    def reset(self):
        from arcengine import GameState
        self.pos, self.direction, self.steps = tuple(self.spec['start']), (1, 0), 0
        return self.observation(GameState.NOT_FINISHED)
    def step(self, ga, data=None):
        from arcengine import GameState
        delta = {1:(0,-1), 2:(0,1), 3:(-1,0), 4:(1,0)}.get(int(ga.value), (0,0))
        if delta != (0,0): self.direction = delta
        x, y = self.pos[0]+delta[0], self.pos[1]+delta[1]
        if 0 <= x < self.w and 0 <= y < self.h and (x,y) not in self.walls:
            self.pos = (x,y)
        self.steps += 1
        state = GameState.WIN if self.pos == self.goal else GameState.GAME_OVER if self.steps >= self.spec['episode_limit'] else GameState.NOT_FINISHED
        return self.observation(state)
    def observer(self):
        return {'position': [4+self.pos[0]*4, 4+self.pos[1]*4], 'direction': list(self.direction),
                'direction_kind': 'mirada real del cuerpo', 'world_position': list(self.pos),
                'world_direction': list(self.direction), 'label': 'Píxel del cuerpo'}


def play_world(agent, custom=False):
    from echo_arc import runner
    from echo_arc.observe import Journal, observed_play
    from seed import arc3gym as gym
    cfg, out, policy = receipt(agent, 'dev-world' if custom else 'arc-gym')
    budget = int(cfg['world_budget'] if custom else cfg['gym_budget'])
    if not 1 <= budget <= 2000: raise ValueError('Presupuesto fuera de 1..2000')
    gym.VERSION = 3
    seeds = [0] if custom else cfg['gym_seeds']
    if any(seed not in range(40) for seed in seeds): raise ValueError('Solo semillas de desarrollo 0..39')
    wins = 0
    for case, seed in enumerate(seeds):
        env = DeveloperWorld(cfg['world_file']) if custom else gym.GymEnv(seed)
        label = 'CUSTOM / desarrollo' if custom else f'ARC3-GYM v3 / desarrollo / semilla {seed}'
        counts = {'cases_done':case, 'cases_total':len(seeds), 'solved':wins, 'resets':0, 'step':0, 'budget':budget}
        class Visible:
            previous = None
            last_direction = None
            def show(self, obs):
                if obs is None: return None
                extra = env.observer() if custom else {}
                if not custom and env.s is not None and env.game.levels[min(env.level,4)].fam != 'C1':
                    pos = list(env.s[0]); px,py = env.game._rect(pos)
                    extra = {'position':[px+env.game.cs//2, py+env.game.cs//2], 'world_position':pos,
                             'label':'Posición real en el entorno', 'direction_kind':'último desplazamiento, no mirada'}
                    if self.previous and self.previous != pos:
                        dx,dy = pos[0]-self.previous[0], pos[1]-self.previous[1]
                        self.last_direction = [int(dx>0)-int(dx<0),int(dy>0)-int(dy<0)]
                    if self.last_direction:
                        extra['direction'] = self.last_direction
                    self.previous = pos
                grid = obs.frame[-1].tolist()
                if custom:
                    grid = [[9 if (x,y)==env.pos else 3 if (x,y)==env.goal else 5 if (x,y) in env.walls else 1 for x in range(env.w)] for y in range(env.h)]
                    extra['position'] = list(env.pos)
                    extra['label'] = 'Celda del cuerpo · visor humano'
                emit({'kind':'frame','grid':grid,'origin':label,'observer':extra})
                counts.update(levels=int(obs.levels_completed),levels_total=int(obs.win_levels))
                emit(dict(counts,kind='progress'))
                return obs
            def reset(self):
                if counts['step']: counts['resets'] += 1
                self.previous = self.last_direction = None
                return self.show(env.reset())
            def step(self,*a,**kw):
                counts['step'] += 1
                return self.show(env.step(*a,**kw))
        journal=Journal(out/f'{seed}-decisions.jsonl')
        original=journal.write
        def observe(**event):
            original(**event)
            emit(dict(event,origin=label))
        journal.write=observe
        try:
            result=observed_play(Visible(),budget,runner.seed_for(f'nexus-dev-{seed}'),journal,agent_name=policy,delay=0.025)
        finally:
            journal.close()
        wins += int(result['levels_completed'] == result['win_levels'])
        counts.update(cases_done=case+1,solved=wins,stop_reason='Todos los niveles resueltos' if wins > counts['solved'] else 'Presupuesto de desarrollo agotado')
        emit(dict(counts,kind='progress'))
        emit({'kind':'result','origin':label,'text':f"{result['levels_completed']}/{result['win_levels']} niveles; {result['resets']} reinicios; {counts['stop_reason']}"})
        (out/f'{seed}-result.json').write_text(json.dumps(result))


def grid_development(agent, corpus=None, limit=3):
    from seed import arc_capabilities as a
    from seed.final_eval import solver_input, judge
    from echoai.seed import sandbox
    from echoai.seed.learn import Library, solve
    from echo_arc.observe import Journal
    cfg, out, _ = receipt(agent, corpus or 'arc-capabilities')
    state = read(ROOT / cfg['grid_state'])['learned']
    tasks = a.suite() if corpus is None else [dict(id=p.stem,task=read(p)) for p in sorted((ROOT / cfg[corpus] / 'data/training').glob('*.json'))[:limit]]
    solved=0
    for i,t in enumerate(tasks):
        label=f"{corpus or 'SINTÉTICO'} / desarrollo / {t['id']}"
        emit({'kind':'frame','origin':label+' · ejemplo de entrenamiento','grid':t['task']['train'][0]['input']})
        emit({'kind':'progress','cases_done':i,'cases_total':len(tasks),'solved':solved})
        journal=Journal(out/(t['id']+'.jsonl'))
        try:
            public=solver_input(t['task'])
            if agent == ED45:
                result=a.solve_public(public,'full',state,journal)
            else:
                sandbox._set_level(0)
                result=solve(public,Library(),max_expansions=400,max_depth=4)
        finally:
            journal.close()
        if result['test_ok'] is not None: raise ValueError('Filtración de etiquetas al solver')
        correct=judge(t['task'],result);solved+=int(correct)
        for pred in result['predictions']:
            if pred: emit({'kind':'frame','origin':label+' · predicción del agente','grid':pred})
        emit({'kind':'result','origin':label,'text':f"Exacta={correct}; no es un score oficial ni cierre de S6"})
        emit({'kind':'progress','cases_done':i+1,'cases_total':len(tasks),'solved':solved})
        (out/(t['id']+'-result.json')).write_text(json.dumps({'correct':correct,'result':result}))


def session_world(agent, limit=0):
    """Development driver: one real ARC actor across episodes, existing journal."""
    import shutil
    import signal
    import numpy as np
    from arcengine import GameState
    from echo_arc import runner
    from echo_arc.observe import Journal, ObservedAgent
    cfg, out, policy = receipt(agent, 'world-session')
    env = DeveloperWorld(cfg['world_file'])
    journal = Journal(out/'decisions.jsonl')
    write = journal.write
    def record(**event):
        write(**event)
        emit(dict(event, origin='CUSTOM / sesión continua / desarrollo'))
    journal.write = record
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    obs = env.reset()
    actor = ObservedAgent(runner.agent_class(policy)(obs.available_actions,
        runner.seed_for('nexus-session'), boundary=True), journal, delay=0.08)
    state = actor.observe_state(np.array(obs.frame[-1]))
    actor.level_start = state
    steps = episodes = wins = resets = 0
    def show():
        view = env.observer()
        view.update(position=list(env.pos), label='Celda del cuerpo · visor humano')
        grid = [[9 if (x,y)==env.pos else 3 if (x,y)==env.goal else 5 if (x,y) in env.walls else 1
                 for x in range(env.w)] for y in range(env.h)]
        emit({'kind':'frame','grid':grid,'observer':view,'origin':'CUSTOM / sesión continua / visor humano'})
        emit({'kind':'progress','step':steps,'budget':'sesión','cases_done':episodes,
              'cases_total':'continuo','solved':wins,'resets':resets,
              'levels':int(obs.levels_completed),'levels_total':1})
    try:
        journal.write(kind='start',text='Una instancia real del actor; memoria retenida entre episodios; cero LLM.')
        show()
        while running and (not limit or steps < limit):
            if steps % 100 == 0 and shutil.disk_usage(out).free < 1024**3:
                raise RuntimeError('Menos de 1 GiB libre; sesión detenida para conservar los registros')
            act = actor.choose(state)
            obs = runner._act(env, act)
            steps += 1
            actor.level_actions.append(act)
            nxt = actor.observe_state(np.array(obs.frame[-1]))
            win, failed = obs.state is GameState.WIN, obs.state is GameState.GAME_OVER
            actor.learn(state, act, nxt, failed, win)
            state = nxt
            show()
            if win or failed:
                episodes += 1
                wins += int(win)
                resets += int(failed)
                journal.write(kind='result',text=f'Episodio {episodes}: meta={win}; instancia y memoria conservadas')
                obs = env.reset()
                state = actor.observe_state(np.array(obs.frame[-1]))
                actor.level_start, actor.level_actions = state, []
                show()
    finally:
        journal.write(kind='end',text='Sesión cerrada; diario conservado',steps=steps,episodes=episodes,wins=wins)
        journal.close()


def replay_grids(agent, domain, limit=0):
    cfg=settings(); arm='semilla' if agent==ED4 else 'sin_s6'
    corpus=ROOT/cfg['arc1' if domain=='R1' else 'arc2']
    files=sorted((HIST/'grid'/domain/arm).glob('*.json'))
    if limit: files=files[:limit]
    if not files: raise ValueError('No hay resultados archivados para este perfil')
    solved=0
    for i,path in enumerate(files):
        record=read(path);task=read(corpus/'data/evaluation'/path.name)
        label=f'REPLAY / ARC oficial {domain} / {path.stem} / archivo 2026-09-28'
        predictions=record['result']['predictions']
        for j,sample in enumerate(task['test']):
            for title,grid in [('Entrada',sample['input']),('Predicción archivada',predictions[j] if j<len(predictions) else None),('Solución publicada',sample.get('output'))]:
                if grid:
                    emit({'kind':'frame','origin':label+' / '+title,'grid':grid})
                    time.sleep(0.3)
        solved+=int(record['correct'])
        emit({'kind':'result','origin':label,'text':f"Resultado archivado: exacta={record['correct']}. No se ejecutó el agente."})
        emit({'kind':'progress','cases_done':i+1,'cases_total':len(files),'solved':solved,'stop_reason':'Reproducción archivada'})


def replay_arc(agent, limit=0):
    import arc_agi
    from echo_arc import runner
    arcade=arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,environments_dir=str(ROOT/'lab/arc3/environment_files'))
    files=sorted((HIST/'arc'/('semilla' if agent==ED4 else 'con_s6')).glob('*.json'))
    if limit:files=files[:limit]
    if not files: raise ValueError('No hay partidas archivadas para este perfil')
    solved=0
    for case,path in enumerate(files):
        rec=read(path);env=arcade.make(rec['game']);obs=env.reset()
        label='REPLAY / ARC-AGI-3 oficial / '+rec['game']+' / archivo 2026-09-28'
        for i in range(len(rec['actions'])+1):
            if i:obs=runner._act(env,rec['actions'][i-1])
            if obs is None or runner.frame_hash(obs.frame[-1]) != rec['frames'][i]:
                raise ValueError('Replay no coincide con el frame archivado; se detiene')
            emit({'kind':'frame','origin':label,'grid':obs.frame[-1].tolist()})
            emit({'kind':'progress','cases_done':case,'cases_total':len(files),'solved':solved,'step':i,'budget':len(rec['actions']),
                  'levels':int(obs.levels_completed),'levels_total':rec['win_levels'],'stop_reason':'Reproducción de acciones archivadas'})
            time.sleep(0.02)
        solved+=int(rec['levels_completed']==rec['win_levels'])
        emit({'kind':'progress','cases_done':case+1,'cases_total':len(files),'solved':solved})
        emit({'kind':'result','origin':label,'text':f"Reproducidos {len(rec['actions'])} eventos. Sin decisiones nuevas ni nueva puntuación."})


def setup():
    path=ROOT/'lab/echo-nexus/backend.json';manifest=read(path)
    config={'arc_policy':'v5.7','gym_budget':600,'gym_seeds':[0,1,2],'world_budget':240,
            'world_file':str(ROOT/'lab/echo-nexus/dev-world.json'),
            'grid_state':'lab/final/echo45-20260928/profile.json','arc1':'lab/seed/ARC-AGI','arc2':'lab/arc2/ARC-AGI-2'}
    if not SETTINGS.exists():SETTINGS.write_text(json.dumps(config,indent=2))
    world=ROOT/'lab/echo-nexus/dev-world.json'
    if not world.exists():world.write_text(json.dumps({'size':[8,7],'start':[1,1],'goal':[6,5],'walls':[[3,1],[3,2],[3,3],[5,4]],'episode_limit':80},indent=2))
    profiles=[]
    for agent in [ED4,ED45]:
        tests=[]
        for ident,title,default in [('arc-gym','ARC3-GYM · 3 semillas · 600 pasos por semilla',True),
                ('dev-world','Mundo editable del desarrollador · observación por píxeles',False),
                ('arc-capabilities','Diagnóstico sintético · objetos, relaciones, composición',False),
                ('arc1-train','ARC-AGI-1 público · 3 tareas de entrenamiento',False),
                ('arc2-train','ARC-AGI-2 público · 3 tareas de entrenamiento',False),
                ('arc1-replay','Visor ARC-AGI-1 · examen archivado completo',False),
                ('arc2-replay','Visor ARC-AGI-2 · examen archivado completo',False),
                ('arc3-replay','Visor ARC-AGI-3 · acciones archivadas, sin agente',False)]:
            tests.append({'id':ident,'title':title,'kind':'development','default':default,'argv':[str(ARC_PYTHON),str(Path(__file__).resolve()),ident,'--agent',agent],'cwd':str(ROOT),'timeout':3600})
        world_entry = {'id':'dev-world','title':'Mundo editable · una instancia continua del agente',
                       'kind':'development','argv':[str(ARC_PYTHON),str(Path(__file__).resolve()),'world-session','--agent',agent],
                       'cwd':str(ROOT),'timeout':3600}
        profiles.append({'id':agent,'description':('Referencia histórica: ARC v2 y biblioteca inicial; adaptador local' if agent==ED4 else 'Código local en desarrollo: ARC v5.7 y refinamiento de rejillas; transferencia S6/EGO pendiente'),'tests':tests,'worlds':[world_entry]})
    manifest['agents']=profiles;manifest['default_agent']=ED45
    path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    print(json.dumps({'agents':[p['id'] for p in profiles],'config':str(SETTINGS),'custom_world':str(world)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('test');parser.add_argument('--agent',default=ED45,choices=[ED4,ED45]);parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    if args.test=='setup':setup()
    elif args.test=='world-session':session_world(args.agent,args.limit)
    elif args.test in ('arc-gym','dev-world'):play_world(args.agent,args.test=='dev-world')
    elif args.test=='arc-capabilities':grid_development(args.agent)
    elif args.test in ('arc1-train','arc2-train'):grid_development(args.agent,args.test[:4],args.limit or 3)
    elif args.test in ('arc1-replay','arc2-replay'):replay_grids(args.agent,'R1' if args.test.startswith('arc1') else 'R2',args.limit)
    elif args.test=='arc3-replay':replay_arc(args.agent,args.limit)
    else:raise ValueError('Prueba desconocida')
