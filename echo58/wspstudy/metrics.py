"""Exact, preregistered relative-saving gate. No model or environment imports."""
from fractions import Fraction


def require(value,message):
    if not value:raise ValueError(message)


def fraction(value):
    return {'numerator':value.numerator,'denominator':value.denominator}


def median(values):
    values=sorted(values);require(bool(values),'empty median')
    n=len(values)
    return Fraction(values[n//2]) if n%2 else (Fraction(values[n//2-1])+values[n//2])/2


def check_counts(row):
    require(type(row) is dict and set(row)=={'tokens','legend_tokens'},'count schema')
    require(type(row['legend_tokens']) is int and row['legend_tokens']>=0,'legend count')
    require(type(row['tokens']) is list and len(row['tokens'])==64,'64 records required')
    require(all(type(t) is int and t>0 for t in row['tokens']),'positive integer token counts')


def verdict(games,*,compatibility_green=True):
    require(type(games) is dict and len(games)==2,'two evaluation games required')
    require(type(compatibility_green) is bool,'compatibility verdict must be boolean')
    savings=[];wt=jt=0;baselines={};by_game={}
    for game,row in games.items():
        require(type(row) is dict and set(row)=={'wsp','json'},'game count schema')
        check_counts(row['wsp'])
        require(type(row['json']) is dict and bool(row['json']),'registered JSON controls required')
        for control in row['json'].values():check_counts(control)
        best=min(row['json'],key=lambda k:(sum(row['json'][k]['tokens'])+row['json'][k]['legend_tokens'],k))
        w=row['wsp'];j=row['json'][best];baselines[game]=best
        w_total=sum(w['tokens'])+w['legend_tokens'];j_total=sum(j['tokens'])+j['legend_tokens']
        wt+=w_total;jt+=j_total
        local=[]
        for wc,jc in zip(w['tokens'],j['tokens']):
            denominator=64*jc+j['legend_tokens']
            local.append(Fraction(denominator-(64*wc+w['legend_tokens']),denominator))
        savings.extend(local)
        by_game[game]={'wsp_tokens':w_total,'best_json_tokens':j_total,
                       'median_saving':fraction(median(local)),
                       'total_saving':fraction(Fraction(j_total-w_total,j_total))}
    med=median(savings);total=Fraction(jt-wt,jt)
    no_regression=all(v['wsp_tokens']<=v['best_json_tokens'] for v in by_game.values())
    return {'green':compatibility_green and med>=Fraction(3,20) and total>=Fraction(3,20) and no_regression,
        'compatibility_green':compatibility_green,'median_saving':fraction(med),
        'total_saving':fraction(total),'median_saving_at_least_15pct':med>=Fraction(3,20),
        'total_saving_at_least_15pct':total>=Fraction(3,20),'no_game_regression':no_regression,
        'wsp_tokens_total':wt,'best_json_tokens_total':jt,'baseline_by_game':baselines,'games':by_game}
