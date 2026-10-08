import importlib.util
from pathlib import Path
import signal
import unittest

spec=importlib.util.spec_from_file_location('s6_probe_driver_test',Path(__file__).resolve().parents[1]/'lab/kaggle/s6-final-20260927/probe_driver.py')
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

class CleanupTests(unittest.TestCase):
    def test_identity_and_deadline_cleanup_restore_signal_state(self):
        prior=signal.getsignal(signal.SIGALRM)
        identity,_=driver.guarded_compile('def op(grid):\n    return grid')
        self.assertEqual(identity(((1,),)),((1,),))
        self.assertEqual(signal.getsignal(signal.SIGALRM),prior)
        def escaping(grid):
            signal.signal(signal.SIGALRM,driver.s6._alarm)
            raise driver.s6.ProposalTimeout('cleanup race')
        with self.assertRaises(ValueError):
            driver.cleanup_guard(escaping)(((1,),))
        self.assertEqual(signal.getsignal(signal.SIGALRM),prior)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))

if __name__=='__main__':unittest.main()
