"""Public-evidence SharedCAM lessons. No official outcome is an input here."""
import hashlib
from pathlib import Path
from ..pcworld.receipts import ReceiptStore, canonical


class SharedConceptLibrary:
    def __init__(self,directory):
        directory=Path(directory)
        self.receipts=ReceiptStore(directory/'receipts',directory/'authority')

    def publish(self,workspace,*,author,budget):
        for r in self.receipts.records:
            value=r['body']
            if value.get('author_agent_id')==author and value.get('donor_journal_head')==workspace.receipts.head:
                return r['sha256']
        ticket=budget.reserve({'tools':1})
        try:
            rows=workspace.receipts.records
            decisions=[r for r in rows if r['body'].get('event')=='repoworld.public-decision']
            if not decisions or not any(r['body']['status']=='PUBLIC_REGRESSION' for r in decisions):return None
            last=decisions[-1]
            if last['body']['status']!='PUBLIC_CHECKS_PASSED' or last['body']['candidate']!=workspace.current.id:return None
            if len(self.receipts.records)>=16:return None
            patch=workspace.final_diff()
            if not patch:return None
            lesson=dict(event='repoworld.public-lesson',author_agent_id=author,repo=workspace.base.task.repo,
                donor_instance=workspace.base.task.instance_id,base_commit=workspace.base.task.base_commit,
                base_tree_sha256=workspace.base.snapshot.id,candidate_sha256=workspace.current.id,
                runtime_sha256=workspace.base.environment.rootfs_sha256,
                runner_policy_sha256=workspace.base.environment.policy_sha256,
                patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),patch_excerpt=patch.encode()[:1024].decode('utf-8','ignore'),
                evidence_receipts=[r['sha256'] for r in decisions],donor_journal_head=workspace.receipts.head,
                status='PUBLIC_EVIDENCE_SCOPED',requires_recheck=True)
            return self.receipts.append(lesson)['sha256']
        finally:budget.settle(ticket,{'tools':1})

    def retrieve(self,base,*,budget):
        ticket=budget.reserve({'tools':1,'output_tokens':384})
        result=[]
        try:
            for r in reversed(self.receipts.records):
                value=r['body']
                if value.get('event')!='repoworld.public-lesson' or value['repo']!=base.task.repo or value['donor_instance']==base.task.instance_id:continue
                # Matching or similar source is only a search hint. No veto or
                # acceptance is imported; every new candidate executes checks.
                hint=dict(receipt=r['sha256'],donor=value['donor_instance'],requires_recheck=True,
                          hint=value['patch_excerpt'][:100],status='unvalidated-on-current-commit')
                if len(canonical(result+[hint]))>384:break
                result.append(hint)
            return tuple(result)
        finally:budget.settle(ticket,{'tools':1,'output_tokens':len(canonical(result))})
