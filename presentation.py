"""Display-only helpers: original metrics, tables and definitions stay unchanged."""
import re

ACTIVITY = {
    'stepsTaken': ('Steps taken', 'steps'),
    'fishCaught': ('Fish caught', 'fish'),
    'rocksCrushed': ('Rocks crushed', 'rocks'),
    'giftsGiven': ('Gifts given', 'gifts'),
    'questsCompleted': ('Quests completed', 'quests'),
    'itemsShipped': ('Items shipped', 'items'),
    'cropsShipped': ('Crops shipped', 'crop items'),
}
HEADERS = {
 'snapshot':'Snapshot','item_id':'Item ID','item':'Item name','mapping':'Name mapping',
 'shipped_units':'Shipped units','slot':'Backpack slot','name':'Item name','quantity':'Stack quantity',
 'quality':'Quality code','skill':'Skill','level':'Level','xp':'Recorded XP',
 'npc':'Character','points':'Friendship points','gifts_week':'Gifts this week',
 'achievement_id':'Achievement ID','previous':'Previous value','current':'Current value','delta':'Change',
 'previous_level':'Previous level','current_level':'Current level','xp_change':'XP change',
 'detail':'Details','check':'Check','unit':'Unit',
}

def label(raw):
    if raw in ACTIVITY:
        return ACTIVITY[raw][0]
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',str(raw)).replace('_',' ').capitalize()

def readable(frame):
    out=frame.copy()
    if 'metric' in out:
        out.insert(0,'Activity',out.metric.map(label))
        out=out.rename(columns={'metric':'Raw field'})
    if 'check' in out:
        out.insert(0,'Quality check',out['check'].map(label))
        out=out.rename(columns={'check':'Raw check'})
    return out.rename(columns=HEADERS)

def changed_activity(delta):
    out=delta[delta.metric.isin(ACTIVITY) & delta.delta.notna() & delta.delta.ne(0)].copy()
    out['activity']=out.metric.map(lambda x:ACTIVITY[x][0])
    out['unit']=out.metric.map(lambda x:ACTIVITY[x][1])
    out['display']=out.activity+' ('+out.unit+')'
    out['change_label']=out.apply(lambda r:f"{r['delta']:+,.0f} {r['unit']}",axis=1)
    return out.sort_values('delta',ascending=False)

SKILL_SQL = """SELECT c.skill,p.level AS previous_level,c.level AS current_level,
c.xp-p.xp AS xp_change FROM skills c JOIN skills p ON c.skill=p.skill
WHERE c.snapshot='current' AND p.snapshot='previous'"""
