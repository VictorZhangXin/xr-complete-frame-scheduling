import unittest
from dataclasses import replace
import study as s
import ablation_core as c
from research_loop import select
class TestLoop(unittest.TestCase):
    def test_default_equivalence(self):
        for seed in range(20):
            config=replace(s.Config(),queue_packets=40 if seed%2 else 4096)
            trace=s.make_trace(config,seed)
            for policy,alpha in [('FA',0),('FA',.125),('FA',1),('EDF-safe',0)]:
                self.assertEqual(s.simulate(trace,config,policy,alpha,True),c.simulate(trace,config,policy,alpha,True,True))
    def test_drop_hand_case(self):
        trace=s.Trace((s.Frame(0,0,0,2,3,4,True),s.Frame(1,1,0,2,1,1,False)),s.np.ones(2,bool),s.np.ones(2,bool))
        on=c.simulate(trace,s.Config(),'FA',1,True,True)[1]
        off=c.simulate(trace,s.Config(),'FA',1,True,False)[1]
        self.assertEqual({f['identifier']:f['status'] for f in on},{0:'infeasible',1:'complete'})
        self.assertEqual({f['identifier']:f['status'] for f in off},{0:'expired',1:'expired'})
    def test_selection_fallback(self):
        rows=[dict(scenario=sc,seed=seed,policy=f'FA{alpha:g}',low_completion_fraction=.9-(.1 if alpha else 0),weighted_fraction=.8+alpha*.1) for sc in range(3) for seed in range(3) for alpha in (0,.125,.25,.5,1)]
        self.assertEqual(select(rows)['alpha'],0)
if __name__=='__main__':unittest.main(verbosity=2)
