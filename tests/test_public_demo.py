"""Public tests use wholly synthetic XML; no personal game files required."""
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import analytics
from analytics import query,SHIPPING_SQL,DELTA_SQL,COVERAGE_SQL
from presentation import changed_activity,readable,SKILL_SQL

class DemoTests(unittest.TestCase):
    def setUp(self):
        self.mode=patch.object(analytics,'DEFAULT_SOURCE',None);self.mode.start()
        self.conn,self.data=analytics.load()
    def tearDown(self):
        self.conn.close();self.mode.stop()
    def test_only_demo_paths_are_read(self):
        original=Path.read_bytes;seen=[]
        def read(path):
            seen.append(path);return original(path)
        with patch.object(Path,'read_bytes',read):
            c,_=analytics.load();c.close()
        self.assertEqual({p.name for p in seen},{'current.xml','previous.xml'})
        self.assertTrue(all(p.parent==Path(analytics.__file__).parent/'demo' for p in seen))
    def test_snapshots_and_schema(self):
        self.assertEqual(set(self.data),set(analytics.SCHEMA))
        s=self.data['snapshots'].set_index('snapshot')
        self.assertEqual(s.loc['current','farm'],'Synthetic Demo Farm')
        self.assertEqual(s.loc['current','ordinal']-s.loc['previous','ordinal'],1)
        self.assertEqual(s.loc['current','money']-s.loc['previous','money'],250)
    def test_join_groupby_and_mapping(self):
        shipping=query(self.conn,SHIPPING_SQL,snapshot='current')
        self.assertEqual(shipping.shipped_units.sum(),72)
        self.assertEqual(len(shipping),3)
        coverage=query(self.conn,COVERAGE_SQL,snapshot='current').iloc[0]
        self.assertEqual(coverage.mapped_ids,2)
        self.assertEqual(coverage.mapped_units,65)
    def test_changes_units_and_raw_fields(self):
        delta=query(self.conn,DELTA_SQL)
        chart=changed_activity(delta)
        self.assertEqual(chart.set_index('metric').loc['stepsTaken','delta'],250)
        self.assertEqual(chart.set_index('metric').loc['itemsShipped','change_label'],'+15 items')
        self.assertNotIn('questsCompleted',set(chart.metric))
        self.assertIn('Raw field',readable(delta).columns)
        self.assertEqual(query(self.conn,SKILL_SQL).set_index('skill').loc['Mining','xp_change'],20)
    def test_quality_issues_are_disclosed(self):
        self.assertTrue({'incomplete_item_mapping','shipping_scope_difference','empty_legacy_stat_nodes'}.issubset(set(self.data['quality']['check'])))
        self.assertFalse(self.data['inventory'].duplicated(['snapshot','slot']).any())
    def test_dashboard_demo_and_switch(self):
        app=AppTest.from_file(str(Path(analytics.__file__).parent/'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('SYNTHETIC DEMO' in x.value for x in app.info))
        self.assertTrue(any('6,250' in str(x.value) for x in app.metric))
        app.selectbox[0].select('previous').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('5,900' in str(x.value) for x in app.metric))
