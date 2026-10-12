"""Persistent exact cache of trusted PURE reference comparisons only.

Not a code execution cache. The caller must freshly execute each candidate and
key the full observed bytes, status, checker, runtime, policy and input. HMAC
custody lives outside candidate mounts. Lookup time includes authentication.
"""
import time
from pathlib import Path
from .receipts import ReceiptStore, digest

class PropertyCache:
    def __init__(self,path):
        path=Path(path)
        self.store=ReceiptStore(path/'receipts',path/'authority')

    def check(self,identity,compute):
        start=time.monotonic_ns();key=digest(identity)
        for receipt in self.store.records:
            body=receipt['body']
            if body.get('key')==key and body.get('identity')==identity:
                return body['value'],{'hit':True,'receipt':receipt['sha256'],
                                      'lookup_ns':time.monotonic_ns()-start,'scope':'pure property'}
        lookup=time.monotonic_ns()-start
        value=compute()
        rec=self.store.append({'kind':'pure_property','key':key,'identity':identity,'value':value})
        return value,{'hit':False,'receipt':rec['sha256'],'lookup_ns':lookup,'scope':'pure property'}
