"""Passive transition-prediction witnesses in the existing development journal."""
from echo_arc.repair_diagnostics import DiagnosticRecorder


class TransitionRecorder(DiagnosticRecorder):
    def __init__(self, journal):
        super().__init__(journal)
        self.prediction = None
        self.noop_witnesses = []
        self.revision_count = 0

    def write(self, **event):
        if event['kind']=='decision':
            a=event['action']
            action=(a[0],a[1],tuple(a[2]) if isinstance(a[2],list) else a[2])
            self.prediction={'state':event['state'],'action':a,
                             'predicted_next':self.actor.T.get((event['state'],action))}
            event['transition_prediction']=self.prediction['predicted_next']
        elif event['kind']=='result' and self.prediction is not None:
            prediction=self.prediction
            contradiction=(not event['changed'] and not event['game_over'] and not event['level_up']
                           and prediction['predicted_next'] not in (None,prediction['state']))
            event['contradictory_noop']=contradiction
            if contradiction:
                self.counts['contradictory_noop']+=1
                if len(self.noop_witnesses)<3:
                    self.noop_witnesses.append(dict(prediction,features=self.last_features,observed_change=False))
            revisions=getattr(self.actor,'noop_revisions',[])
            if len(revisions)>self.revision_count:
                event['transition_revisions']=revisions[self.revision_count:]
                self.revision_count=len(revisions)
        super().write(**event)

    def summary(self):
        return dict(super().summary(),contradictory_noop_examples=self.noop_witnesses,
                    transition_revisions=self.revision_count)
