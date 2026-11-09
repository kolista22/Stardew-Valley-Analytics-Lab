"""Read-only save extraction. SQLite is in-memory; no game files are written."""
from pathlib import Path
import hashlib
import os
import sqlite3
import xml.etree.ElementTree as ET
import pandas as pd

DEFAULT_SOURCE = Path(os.environ['STARDEW_SAVE_DIR']).expanduser() if os.environ.get('STARDEW_SAVE_DIR') else None
FARM = DEFAULT_SOURCE.name if DEFAULT_SOURCE is not None else 'PRIVATE_SAVE_NOT_CONFIGURED'
SEASONS = {'spring': 0, 'summer': 1, 'fall': 2, 'winter': 3}
SKILLS = [('Farming', 'farmingLevel'), ('Mining', 'miningLevel'), ('Foraging', 'foragingLevel'), ('Fishing', 'fishingLevel'), ('Combat', 'combatLevel')]
SCHEMA = {
 'snapshots': ['snapshot','farm','year','season','day','ordinal','money','earned','hours','mine_level','sha256'],
 'stats': ['snapshot','metric','value'],
 'skills': ['snapshot','skill','level','xp'],
 'shipments': ['snapshot','item_id','quantity'],
 'inventory': ['snapshot','slot','item_id','name','quantity','quality'],
 'items': ['item_id','name'],
 'social': ['snapshot','npc','points','gifts_week'],
 'achievements': ['snapshot','achievement_id'],
 'crops': ['snapshot','crop_id','phase','dead'],
 'quality': ['snapshot','check','detail'],
}

def normalize_id(value):
    if not value:
        return None
    return value if value.startswith('(') else '(O)' + value

def extract(path, snapshot):
    raw = Path(path).read_bytes()
    root = ET.fromstring(raw)
    p = root.find('player')
    if p is None:
        raise ValueError('Missing player node; unsupported save.')
    rows = {k: [] for k in SCHEMA}
    def issue(check, detail):
        rows['quality'].append([snapshot, check, detail])
    def number(node, key, required=False):
        text = node.findtext(key) if node is not None else None
        if text is None or not text.strip():
            issue('missing_or_empty', key)
            if required:
                raise ValueError('Missing required numeric field: ' + key)
            return None
        try:
            value = int(text)
        except ValueError:
            issue('invalid_number', key)
            if required:
                raise ValueError('Invalid required numeric field: ' + key)
            return None
        if value < 0:
            issue('negative_count', key)
        return value
    year, day = number(root, 'year', True), number(root, 'dayOfMonth', True)
    season = root.findtext('currentSeason')
    if season not in SEASONS or not 1 <= day <= 28:
        raise ValueError('Invalid game date')
    ms = number(p, 'millisecondsPlayed', True)
    rows['snapshots'].append([snapshot, p.findtext('farmName'), year, season, day,
        (year-1)*112+SEASONS[season]*28+day, number(p,'money',True),
        number(p,'totalMoneyEarned',True), ms/3600000, number(p,'deepestMineLevel'), hashlib.sha256(raw).hexdigest()])
    legacy=p.find('stats')
    empty_legacy=sum(1 for e in legacy if e.tag != 'Values' and len(e)==0 and not (e.text or '').strip()) if legacy is not None else 0
    if empty_legacy:
        issue('empty_legacy_stat_nodes',str(empty_legacy)+' empty legacy placeholders; actual Values dictionary used')
    # Actual values live in Values, not the empty legacy stats placeholders.
    for e in p.findall('stats/Values/item'):
        rows['stats'].append([snapshot,e.findtext('key/string'),number(e,'value/unsignedInt')])
    xp = p.findall('experiencePoints/int')
    for i, (name,key) in enumerate(SKILLS):
        level = number(p,key)
        if level is not None and level > 10:
            issue('unusual_skill_level', name)
        rows['skills'].append([snapshot,name,level,number(xp[i],'.') if i < len(xp) else None])
    for e in p.findall('basicShipped/item'):
        rows['shipments'].append([snapshot,normalize_id(e.findtext('key/string')),number(e,'value/int')])
    # Scope is the player's backpack only: nil slots, tools and equipment are not saleable stock.
    for slot,e in enumerate(p.findall('items/Item')):
        if e.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true':
            continue
        kind=e.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type','Object')
        item=e.findtext('itemId')
        key=normalize_id(item) if kind == 'Object' else kind + ':' + str(item)
        rows['inventory'].append([snapshot,slot,key,e.findtext('name'),number(e,'stack'),number(e,'quality')])
    # Names are inferred only from explicitly serialized Object instances, not an invented catalog.
    names={}
    for e in root.iter():
        kind=e.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type')
        if e.tag != 'Object' and not (e.tag == 'Item' and kind in (None,'Object')):
            continue
        item,name=e.findtext('itemId'),e.findtext('name')
        big=e.findtext('bigCraftable') == 'true'
        if item and name and not big:
            names.setdefault(normalize_id(item),set()).add(name)
    for item,values in names.items():
        if len(values)==1:
            rows['items'].append([item,next(iter(values))])
        else:
            issue('ambiguous_item_mapping', item)
    for e in p.findall('friendshipData/item'):
        rows['social'].append([snapshot,e.findtext('key/string'),number(e,'value/Friendship/Points'),number(e,'value/Friendship/GiftsThisWeek')])
    for e in p.findall('achievements/int'):
        rows['achievements'].append([snapshot,number(e,'.')])
    # Crop nodes across all saved locations; no assumption that every node is an outdoor farm tile.
    for e in root.findall('.//crop'):
        if len(e) == 0 or e.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true':
            continue
        rows['crops'].append([snapshot,e.findtext('indexOfHarvest'),number(e,'currentPhase'),e.findtext('dead')])
    for key,paths in {'stats':'stats/Values','shipments':'basicShipped','social':'friendshipData','achievements':'achievements','inventory':'items'}.items():
        node=p.find(paths)
        if node is None or len(node)==0:
            issue('missing_or_empty_collection',key)
    for table,col in [('stats',1),('shipments',1),('social',1),('achievements',1)]:
        seen=set()
        for row in rows[table]:
            if row[col] is None:
                issue('missing_id',table)
            if row[col] in seen:
                issue('duplicate_id',table+':'+str(row[col]))
            seen.add(row[col])
    return rows

def load(source=None):
    # Public default never probes the user's game directory.
    if source is None:
        if DEFAULT_SOURCE is not None:
            source=DEFAULT_SOURCE
        else:
            demo=Path(__file__).parent/'demo'
            bundles=[extract(demo/'current.xml','current'),extract(demo/'previous.xml','previous')]
    if source is not None:
        source=Path(source)
        name=source.name
        bundles=[extract(source/name,'current'),extract(source/(name+'_old'),'previous')]
    data={k:pd.DataFrame([r for b in bundles for r in b[k]],columns=cols) for k,cols in SCHEMA.items()}
    # Use names from both snapshots, excluding conflicting mappings.
    mapping=data['items'].drop_duplicates()
    conflicts=mapping.groupby('item_id')['name'].nunique()
    bad=set(conflicts[conflicts>1].index)
    data['items']=mapping[~mapping.item_id.isin(bad)].drop_duplicates('item_id')
    extra=[['both','ambiguous_item_mapping',x] for x in sorted(bad)]
    if extra:
        data['quality']=pd.concat([data['quality'],pd.DataFrame(extra,columns=SCHEMA['quality'])],ignore_index=True)
    # Reconciliation is a scope warning, never an instruction to force totals to match.
    checks=[]
    for snapshot in ['current','previous']:
        shipped=data['shipments'].query('snapshot == @snapshot')
        known=set(data['items'].item_id)
        unmapped=shipped[~shipped.item_id.isin(known)]
        if len(unmapped):
            checks.append([snapshot,'incomplete_item_mapping',str(len(unmapped))+' shipping IDs have no unambiguous save-derived name'])
        stat=data['stats'].query('snapshot == @snapshot and metric == "itemsShipped"')
        if len(stat)==1 and stat.iloc[0]['value'] != shipped.quantity.sum():
            checks.append([snapshot,'shipping_scope_difference','itemsShipped='+str(stat.iloc[0]['value'])+'; basicShipped sum='+str(shipped.quantity.sum())+'; scopes not assumed identical'])
    if checks:
        data['quality']=pd.concat([data['quality'],pd.DataFrame(checks,columns=SCHEMA['quality'])],ignore_index=True)
    conn=sqlite3.connect(':memory:')
    for name,frame in data.items():
        frame.to_sql(name,conn,index=False,if_exists='replace')
    return conn,data

SHIPPING_SQL = '''WITH named AS (
 SELECT s.item_id, COALESCE(i.name, 'Unmapped ' || s.item_id) AS item,
        s.quantity, CASE WHEN i.name IS NULL THEN 'Unmapped' ELSE 'XML-derived name' END AS mapping
 FROM shipments s LEFT JOIN items i ON s.item_id=i.item_id
 WHERE s.snapshot=:snapshot
)
SELECT item_id,item,mapping,SUM(quantity) AS shipped_units
FROM named GROUP BY item_id,item,mapping ORDER BY shipped_units DESC'''
DELTA_SQL = '''WITH paired AS (
 SELECT c.metric,p.value AS previous,c.value AS current,c.value-p.value AS delta
 FROM stats c JOIN stats p ON c.metric=p.metric
 WHERE c.snapshot='current' AND p.snapshot='previous'
)
SELECT * FROM paired ORDER BY metric'''
COVERAGE_SQL = '''SELECT COUNT(*) AS shipment_ids,
 SUM(CASE WHEN i.name IS NOT NULL THEN 1 ELSE 0 END) AS mapped_ids,
 SUM(s.quantity) AS shipped_units,
 SUM(CASE WHEN i.name IS NOT NULL THEN s.quantity ELSE 0 END) AS mapped_units
 FROM shipments s LEFT JOIN items i ON s.item_id=i.item_id WHERE s.snapshot=:snapshot'''

def query(conn,sql,**params):
    return pd.read_sql_query(sql,conn,params=params)
