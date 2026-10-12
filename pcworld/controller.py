"""Versioned PCWorld host action adapter: fixed control first, no learned-Q claim.

Uses existing ATTEND and gate on their native meanings (request observation,
allow/block intervention), not relabelled approach/avoid rewards. Typed dispatch
is a host capability selected after the WSP gate. Q is not trained in this slice.
"""
from echoai.core.wsp import pack
from echoai.nexus0.gate import gate
from echoai.nexus0.attend import attend

LIMITS={'tokens':25000,'tools':50,'cpu_us':300000000,'llm_calls':12,'fuel':128,'critic_calls':2}
TOOLS=('read_snapshot','apply_patch','run_python','check_property','submit_counterexample')

def arm_profile(arm):
    if arm not in ('S','I2','F','E'): raise ValueError('unknown arm')
    return {'arm':arm,'tools':list(TOOLS),'limits':dict(LIMITS),'checker':'pcworld-reference-1',
            'permanent_library':'frozen-empty','model':'must be pinned by pilot config'}

def barrier(responses):
    ids=[r['dispatch_id'] for r in responses]
    if any(type(i) is not int or i<0 for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('invalid or duplicate dispatch identity')
    return sorted(responses,key=lambda r:(r['dispatch_id'],r['role']))

def choose(arm,*,has_candidate,property_status,critic_used):
    arm_profile(arm)
    if not has_candidate: return 'propose'
    if arm=='F' and not critic_used: return 'critic'
    if arm=='S' and not critic_used: return 'self_review'
    if arm=='E':
        # A reproduced failure already supplies a repair target. Extra critique
        # is eligible when evidence leaves the candidate plausible but incomplete.
        wake,_=attend(slot_hit=True,extract_ok=property_status!='unknown',E=(0,)*6,
                      kind_novel=False,ham=0,q_confident=property_status=='contradicted',
                      t_known=True,t_conf=2)
        if wake and not critic_used: return 'critic'
    return 'finish' if property_status=='supported' else 'propose'

def authorize(operation,*,eligible=True):
    if operation not in (*TOOLS,'propose','critic','self_review','finish'): raise ValueError('unknown action')
    # n_actions is explicit and retains historical NEXUS-0 default semantics.
    # The gate's inhibit bit is an eligibility restriction, NEVER similarity.
    wsp=pack(src=2,rel=15 if operation in ('propose','critic','self_review') else 14,dst=3,
             domain=9,generator=8,style=223)
    decision,_,flags=gate(wsp,cam_hit=False,extract_ok=False,E=(0,)*6,
                          proposed=2,inhibit=not eligible)
    return {'operation':operation,'wsp':wsp.hex(),'gate':decision,'flags':flags,
            'allowed':decision==0,'policy':'pcworld-fixed-attend-v1'}
