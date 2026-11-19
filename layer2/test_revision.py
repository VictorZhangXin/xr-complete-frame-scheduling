import unittest,tempfile,csv,json
from pathlib import Path
from unittest.mock import patch
import loop_analyze
from integrity import hashes
from tests import oracle
import study as s

class RevisionTests(unittest.TestCase):
    def test_readonly_wrapper(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'data';root.mkdir();(root/'keep').write_text('unchanged')
            before=hashes(root)
            def fake(source,dest,source_root):
                self.assertEqual(source,root)
                (dest/'audit.json').write_text('{"ok":true}')
            with patch.object(loop_analyze,'_analyze',side_effect=fake):
                self.assertTrue(loop_analyze.analyze(root)['ok'])
                self.assertEqual(before,hashes(root))
                with self.assertRaises(ValueError):loop_analyze.analyze(root,output=root)
                with self.assertRaises(ValueError):loop_analyze.analyze(root,output=root/'inside')
    def test_fractional_priority_hand(self):
        # 4^(1/8)/2 < 1, so ordinary one-packet frame finishes before high two-packet frame.
        trace=s.Trace((s.Frame(0,0,0,3,2,4,True),s.Frame(1,1,0,3,1,1,False)),s.np.ones(3,bool),s.np.ones(3,bool))
        expected=oracle(trace,100,'FA',.125)
        self.assertEqual(expected[1][3],1)
        self.assertEqual(expected[0][3],3)
        _,out=s.checked_simulate(trace,s.Config(),'FA',.125)
        self.assertEqual({f['identifier']:(f['status'],f['remaining'],f['attempts'],f['completion']) for f in out},expected)
if __name__=='__main__':unittest.main(verbosity=2)
