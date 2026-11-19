import unittest, itertools, tempfile, math, csv
from unittest.mock import patch
from pathlib import Path
from fractions import Fraction
from dataclasses import replace
import study as s
import analyze_study as a
from integrity import safe_relative

def oracle(trace,capacity,policy,alpha):
    # Independent representation: a list of outstanding packet tokens per frame.
    jobs={f.identifier:{'f':f,'tokens':list(range(f.packets)),'attempts':0,'status':None,'completion':None} for f in trace.frames}
    for t,(available,success) in enumerate(zip(trace.available,trace.success)):
        pending=lambda:[j for j in jobs.values() if j['status']=='active']
        for j in pending():
            if j['f'].deadline<=t:j['status']='expired'
        for f in trace.frames:
            if f.arrival==t:
                j=jobs[f.identifier]
                j['status']='overflow' if sum(len(k['tokens']) for k in pending())+f.packets>capacity else 'active'
        if policy in ('FA','EDF-safe'):
            for j in pending():
                if len(j['tokens'])>j['f'].deadline-t:j['status']='infeasible'
        candidates=pending()
        if not available or not candidates:continue
        if policy=='FA':
            j=sorted(candidates,key=lambda j:(-Fraction(int(j['f'].value)**Fraction(alpha).numerator,(len(j['tokens'])*(j['f'].deadline-t))**Fraction(alpha).denominator),j['f'].deadline,j['f'].identifier))[0]
        else:
            j=sorted(candidates,key=lambda j:((j['f'].arrival if policy=='FIFO' else j['f'].deadline),j['f'].identifier))[0]
        j['attempts']+=1
        if success:
            j['tokens'].pop()
            if not j['tokens']:j['status']='complete';j['completion']=t+1
    for j in jobs.values():
        if j['status']=='active':j['status']='expired'
    return {i:(j['status'],len(j['tokens']),j['attempts'],j['completion']) for i,j in jobs.items()}

class Tests(unittest.TestCase):
    def test_multiframe_oracle(self):
        setups=[[(0,0,0,4,2,4,True),(1,1,0,4,1,1,False),(2,0,2,4,1,1,False)],
                [(0,0,0,4,2,1,False),(1,1,0,4,2,1,False),(2,0,1,3,1,4,True)],
                [(0,0,0,4,3,4,True),(1,1,1,3,1,1,False),(2,0,2,4,2,1,False)]]
        for setup,bits,capacity,pa in itertools.product(setups,itertools.product([False,True],repeat=8),(3,8),(('FIFO',0),('EDF',0),('EDF-safe',0),('FA',0),('FA',.125),('FA',.25),('FA',.5),('FA',1))):
            trace=s.Trace(tuple(s.Frame(*f) for f in setup),s.np.array(bits[:4]),s.np.array(bits[4:]))
            _,out=s.checked_simulate(trace,replace(s.Config(),queue_packets=capacity),*pa)
            actual={f['identifier']:(f['status'],f['remaining'],f['attempts'],f['completion']) for f in out}
            self.assertEqual(actual,oracle(trace,capacity,*pa))

    def test_paths(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(safe_relative(d,'v2\\study.py'),Path(d).resolve()/'v2/study.py')
            for p in ('../x','/x','C:\\x','v2/../../x'):
                with self.assertRaises(ValueError):safe_relative(d,p)

    def test_missing_pairs(self):
        rows=[]
        for seed in range(3):
            for alpha in (0,1):
                rows.append({'scenario':0,'seed':seed,'policy':'FA','alpha':alpha,'family':'main',**{k:float('nan') if seed==2 and alpha==1 else .5+.1*alpha for k in a.METRICS}})
        with tempfile.TemporaryDirectory() as d:
            old=a.OUT;a.OUT=Path(d)
            try:
                means,effects=a.summarize(rows)
                self.assertTrue(all(e['n']==2 and e['n_total']==3 for e in effects))
                self.assertAlmostEqual(effects[0]['mean_delta'],.1)
                for r in rows:r.update({k:float('nan') for k in a.METRICS})
                _,effects=a.summarize(rows)
                self.assertEqual(effects[0]['n'],0)
                self.assertTrue(math.isnan(effects[0]['bootstrap_low']))
            finally:a.OUT=old

    def test_legacy(self):self.assertEqual(s.validate()['passed_groups'],10)

    def test_invalid_is_always_checked(self):
        with self.assertRaises(ValueError):s.check_config(replace(s.Config(),loss=2))
        # Core invariant intentionally violated: a frame outside the supplied horizon.
        trace=s.Trace((s.Frame(0,0,2,4,1,1,False),),s.np.ones(1,bool),s.np.ones(1,bool))
        with self.assertRaises(AssertionError):s.simulate(trace,s.Config(),'FIFO')

    def test_refuses_overwrite(self):
        import run
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'keep';marker.write_text('unchanged')
            with self.assertRaises(FileExistsError):run.run(d,'smoke',3000,2)
            self.assertEqual(marker.read_text(),'unchanged')

    def test_audit_failure_not_published(self):
        import run
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'published'
            tiny=[('main',replace(s.Config(),duration_s=.02),[('FA',0),('FA',1)])]
            with patch.object(s,'validate',return_value={}),patch.object(run,'settings',return_value=tiny),patch.object(a,'audit',side_effect=ValueError('injected audit failure')):
                with self.assertRaisesRegex(ValueError,'injected audit failure'):run.run(dest,'smoke',1,2)
            self.assertFalse(dest.exists())
            self.assertEqual(len(list(Path(d).glob('.published-pending-*'))),1)

    def test_burst_changes_only_failure_process(self):
        import run
        config=s.Config();iid=s.make_trace(config,3000);burst=run.burst_trace(config,3000)
        self.assertEqual(iid.frames,burst.frames)
        self.assertTrue(s.np.array_equal(iid.available,burst.available))
        self.assertFalse(s.np.array_equal(iid.success,burst.success))
        self.assertEqual(burst.fingerprint(),run.burst_trace(config,3000).fingerprint())

if __name__=='__main__':unittest.main(verbosity=2)
