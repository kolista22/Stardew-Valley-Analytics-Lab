"""Local-only Streamlit dashboard. Never writes game files."""
import streamlit as st
from analytics import load,query,SHIPPING_SQL,DELTA_SQL,COVERAGE_SQL,DEFAULT_SOURCE
from presentation import readable,changed_activity,SKILL_SQL,HEADERS

st.set_page_config(page_title='Stardew Valley Analytics Lab',page_icon='🌻',layout='wide')
st.markdown('''<style>
.stApp {background:#faf5e7;color:#293a2c}
h1,h2,h3 {color:#36553a !important}
[data-testid="stMetric"] {background:#eee1ba;border:2px solid #987b4c;border-radius:8px;padding:14px}
[data-testid="stSidebar"] {background:#e7edd8}
.stButton>button {border:2px solid #987b4c;background:#f4e2af;color:#293a2c;box-shadow:2px 2px 0 #987b4c}
.block-container {padding-top:2rem}
[data-testid="stMetricValue"] {font-size:1.2rem;white-space:normal;overflow:visible}
[data-testid="stMetricLabel"] p {font-size:.85rem;white-space:normal;overflow:visible}
[data-testid="stCaptionContainer"] p {color:#596653}
</style>''',unsafe_allow_html=True)
st.title('🌻 Stardew Valley Analytics Lab')
st.caption('XML save analysis · Python / pandas / SQLite · transparent metrics')
if DEFAULT_SOURCE is None:
    st.info('SYNTHETIC DEMO — invented fixture values for software demonstration only. Not real player behavior, retention or game results.')
else:
    st.info('PRIVATE LOCAL MODE — real local snapshots; do not publish source data or personal outputs.')
st.caption('🔒 Local gameplay analysis. Do not publish raw saves; review screenshots and exports before sharing.')
if st.button('Reload read-only snapshots'):
    st.rerun()
try:
    conn,data=load()
except Exception as exc:
    st.error('Could not parse local saves: '+str(exc))
    st.stop()
try:
    with st.sidebar:
        st.header('Save explorer')
        selected=st.selectbox('Snapshot',['current','previous'])
        st.caption('Two endpoint snapshots. Dates and values below are read from the selected XML source.')
        st.info('One farm, two snapshots — not two users or a player cohort.')
        st.caption('Read-only XML → pandas → in-memory SQLite. No save upload or database file.')
    snap=data['snapshots'].set_index('snapshot').loc[selected]
    st.subheader(f"{snap['farm']} · Year {snap['year']} / {snap['season'].title()} / Day {snap['day']}")
    st.caption(f"Recorded playtime: {snap['hours']:.2f} hours. This is the save field, not verified Steam playtime.")
    economy,activity,comparison,quality=st.tabs(['🌾 Farm Economy','⛏ Player Activity & Progression','📊 Snapshot Comparison','🔎 Data Quality & SQL'])
    with economy:
        a,b,c=st.columns(3)
        a.metric('Current gold balance',f"{snap['money']:,.0f} g")
        b.metric('Recorded lifetime earnings',f"{snap['earned']:,.0f} g")
        shipped=query(conn,SHIPPING_SQL,snapshot=selected)
        c.metric('Item-level shipped units',f"{shipped.shipped_units.sum():,.0f}")
        st.caption('The shipping-mix total sums basicShipped records; it is not assumed equal to the broader itemsShipped activity counter. See Data Quality for reconciliation.')
        st.caption('Balance ≠ revenue ≠ profit. Lifetime earnings and shipping quantities are cumulative save fields, not a transaction ledger. No price-based revenue estimate is invented.')
        st.markdown('**Data Insights**')
        if len(shipped) and shipped.shipped_units.sum()>0:
            top=shipped.iloc[0]
            st.write(f"• The largest recorded shipping entry, {top['item']}, accounts for {top['shipped_units']/shipped.shipped_units.sum():.1%} of item-level shipped units. This is volume concentration, not a revenue or profit share.")
        st.write(f"• Current gold is {snap['money']:,.0f} g versus {snap['earned']:,.0f} g recorded lifetime earnings. The gap cannot be treated as spending: a complete cash-flow ledger is unavailable.")
        st.subheader('Recorded shipping mix · top 15 item IDs')
        chart=shipped.head(15).copy()
        chart['label']=chart['item']+' ['+chart['item_id']+']'
        st.bar_chart(chart.rename(columns={'label':'Item','shipped_units':'Shipped units'}),x='Item',y='Shipped units',color='#547b4c',horizontal=True)
        st.caption('Names are matched only where explicitly serialized Object names provide an unambiguous ID mapping; other IDs remain Unmapped.')
        with st.expander('All shipping records and mapping status'):
            st.dataframe(readable(shipped),hide_index=True)
        st.subheader('Verified backpack contents')
        inv=data['inventory'].query('snapshot == @selected').drop(columns='snapshot')
        st.dataframe(readable(inv),hide_index=True)
        st.caption('Backpack slots only. Includes tools/equipment; stack counts are not saleable inventory valuation. Chests, refrigerators, machines and all-world stock are outside this MVP inventory scope.')
        crops=data['crops'].query('snapshot == @selected')
        st.write(f'Non-empty saved crop nodes across saved locations: **{len(crops):,}**. These describe current state, not harvest history.')
    with activity:
        st.subheader('Recorded skill XP change · previous → current snapshot')
        skills=data['skills'].query('snapshot == @selected').drop(columns='snapshot')
        skill_changes=query(conn,SKILL_SQL)
        st.dataframe(readable(skill_changes[['skill','xp_change']]),hide_index=True)
        st.caption('XP changes always compare the two endpoints, regardless of the snapshot selected in the sidebar. Levels and recorded XP totals below follow that selection.')
        with st.expander('Skill levels and recorded XP totals'):
            st.dataframe(readable(skills),hide_index=True)
        st.markdown('**Data Insights**')
        level_count=int((skills.level==10).sum())
        st.write(f'• {level_count} of {len(skills)} displayed skills are level 10 in this snapshot. Compare XP changes alongside levels: unchanged levels can coexist with incremental progress.')
        if skill_changes.xp_change.notna().all() and skill_changes.xp_change.eq(0).all():
            st.write('• All five recorded skill XP differences are zero between these endpoints. This does not establish inactivity: other saved activity counters can still change, and these XP fields are not a full progression history.')
        else:
            st.write(f'• {(skill_changes.xp_change.fillna(0)!=0).sum()} skills have a non-zero recorded XP difference; missing values remain unknown, and endpoint differences do not reveal when progression occurred.')
        stats=data['stats'].query('snapshot == @selected').set_index('metric')['value']
        keys=[('fishCaught','Fish caught'),('rocksCrushed','Rocks crushed'),('giftsGiven','Gifts given'),('questsCompleted','Quests completed')]
        for col,(key,label) in zip(st.columns(4),keys):
            value=stats.get(key)
            col.metric(label,'Not recorded' if value is None else f'{value:,.0f}')
        st.write(f"Saved deepest-mine-level field: **{snap['mine_level']}**. Interpretation across mine areas is not expanded here.")
        st.caption('Counts measure recorded activity, not motivation, retention, success rate or independently timestamped events. Different actions are not comparable units of engagement.')
        social=data['social'].query('snapshot == @selected').drop(columns='snapshot')
        st.subheader('Social relationship state')
        st.dataframe(readable(social.sort_values('points',ascending=False)),hide_index=True)
        achievements=data['achievements'].query('snapshot == @selected')
        st.write(f'**{len(achievements)}** recorded achievement IDs. Names and a completion percentage are not inferred without a verified catalog.')
        with st.expander('Achievement IDs and cumulative activity counters'):
            st.dataframe(readable(achievements.drop(columns='snapshot')),hide_index=True)
            st.dataframe(readable(stats.rename('value').reset_index()).rename(columns={'value':'Recorded count'}),hide_index=True)
    with comparison:
        st.subheader('Two XML snapshots — a limited progression comparison')
        snaps=data['snapshots'].set_index('snapshot')
        cur,prev=snaps.loc['current'],snaps.loc['previous']
        gap=int(cur['ordinal']-prev['ordinal'])
        st.write(f"Year {prev['year']} {prev['season']} {prev['day']} → Year {cur['year']} {cur['season']} {cur['day']} · **{gap} game-day boundary**")
        if gap<=0 or cur['farm'] != prev['farm']:
            st.error('Snapshot identity/date ordering failed. Do not interpret these as forward progression.')
        a,b,c=st.columns(3)
        a.metric('Gold balance change',f"{cur['money']-prev['money']:+,.0f} g")
        b.metric('Lifetime earnings change',f"{cur['earned']-prev['earned']:+,.0f} g")
        c.metric('Recorded time change',f"{(cur['hours']-prev['hours'])*60:.1f} min")
        st.warning('Differences are endpoint changes, not a full transaction/event log. They do not reveal gross spending, the timing of actions or causality. No daily series, cohort, retention or LTV is reconstructed.')
        delta=query(conn,DELTA_SQL)
        selected_metrics=['stepsTaken','fishCaught','rocksCrushed','giftsGiven','questsCompleted','itemsShipped','cropsShipped']
        changed=changed_activity(delta)
        st.subheader('Changed activity counters · raw counts')
        if not changed.empty:
            st.vega_lite_chart(changed,{
                'height':max(160,len(changed)*45),
                'encoding':{
                    'y':{'field':'display','type':'nominal','sort':None,'title':None,'axis':{'labelLimit':260}},
                    'x':{'field':'delta','type':'quantitative','title':'Count change — units differ by activity','scale':{'zero':True,'domainMax':float(changed.delta.abs().max())*1.35}},
                    'tooltip':[{'field':'activity','title':'Activity'},{'field':'metric','title':'Raw field'},{'field':'delta','title':'Change'},{'field':'unit','title':'Unit'}]
                },
                'layer':[{'mark':{'type':'bar','color':'#547b4c'}},
                         {'mark':{'type':'text','align':'left','dx':5,'color':'#293a2c'},'encoding':{'text':{'field':'change_label'}}}]
            },width='stretch')
        else:
            st.info('No non-zero changes were recorded in the selected activity counters.')
        st.caption('Shared linear count axis; exact labels preserve small changes. Steps, fish, gifts and shipped items are different units: do not sum them or interpret longer bars as greater engagement. Zero-change and missing counters are omitted from the chart, retained in the table.')
        st.markdown('**Data Insights**')
        values=delta.set_index('metric')['delta']
        if all(k in values for k in ['stepsTaken','itemsShipped','giftsGiven','fishCaught']):
            st.write(f"• The endpoints show {values['stepsTaken']:,.0f} additional steps, {values['itemsShipped']:,.0f} shipped items, {values['giftsGiven']:,.0f} gifts and {values['fishCaught']:,.0f} fish caught. Several activity types changed; their differing units prevent a combined engagement score.")
        st.write(f"• Balance and lifetime earnings changed by {cur['money']-prev['money']:+,.0f} g and {cur['earned']-prev['earned']:+,.0f} g respectively. Even matching changes do not prove no spending occurred or identify which activity generated income.")
        st.dataframe(readable(delta[delta.metric.isin(selected_metrics)]),hide_index=True)
        st.caption('Only counters present in both snapshots are differenced. Missing counters are not silently filled with zero.')
        st.subheader('Skill XP change between endpoints')
        skill_changes=query(conn,SKILL_SQL)
        st.dataframe(readable(skill_changes[['skill','xp_change']]),hide_index=True)
        with st.expander('Endpoint skill levels'):
            st.dataframe(readable(skill_changes[['skill','previous_level','current_level']]),hide_index=True)
        with st.expander('All comparable counter deltas'):
            st.dataframe(readable(delta),hide_index=True)
    with quality:
        st.subheader('Data quality and lineage')
        coverage=query(conn,COVERAGE_SQL,snapshot=selected).iloc[0]
        st.write(f"Shipping-name coverage: **{int(coverage.mapped_ids)}/{int(coverage.shipment_ids)} item IDs**; **{int(coverage.mapped_units):,}/{int(coverage.shipped_units):,} shipped units**. Unknown names remain visible.")
        st.markdown('**Data Insights**')
        if coverage.shipment_ids and coverage.shipped_units:
            st.write(f"• Names cover {coverage.mapped_ids/coverage.shipment_ids:.1%} of shipping IDs but only {coverage.mapped_units/coverage.shipped_units:.1%} of shipped units. ID coverage and unit coverage answer different questions; report both rather than treating one as the other.")
        raw_count=data['stats'].query('snapshot == @selected and metric == "itemsShipped"')
        if len(raw_count)==1:
            st.write(f"• The activity counter exceeds item-level shipping records by {raw_count.iloc[0]['value']-coverage.shipped_units:,.0f} units in this snapshot. Keep the two scopes separate; their semantic difference remains unresolved.")
        st.dataframe(readable(data['quality']),hide_index=True)
        st.caption('An empty issue table means the implemented checks found no issues; it is not a certification that all game semantics are known. Missing/empty numeric fields, collections, duplicates, negative counts and ambiguous mappings are checked. Repeated inventory item IDs are valid stacks, not automatically duplicates.')
        legacy='Legacy player/stats scalar nodes can be empty. This app reads stats/Values/item values instead; absent data is not converted to zero.'
        st.info(legacy)
        st.subheader('Counter checks across snapshots')
        delta=query(conn,DELTA_SQL)
        # averageBedtime is a clock-style measure, not a monotonic event counter.
        negatives=delta[(delta.delta<0)&(~delta.metric.isin(['averageBedtime']))]
        st.dataframe(readable(negatives),hide_index=True)
        st.caption('Negative changes are review flags, not proof of corruption; some stats can be non-monotonic or version-specific.')
        with st.expander('Snapshot provenance and SHA-256'):
            st.dataframe(data['snapshots'],hide_index=True)
        with st.expander('Display labels → original table columns'):
            st.dataframe([{'Display label':v,'Raw column':k} for k,v in HEADERS.items()],hide_index=True)
        for title,sql in [('Shipping composition: meaningful CTE + LEFT JOIN + GROUP BY',SHIPPING_SQL),('Matched cumulative counter changes: CTE + JOIN',DELTA_SQL),('Mapping completeness: LEFT JOIN',COVERAGE_SQL)]:
            with st.expander(title):
                st.code(sql,language='sql')
        st.caption('No real player cohort, long-term event history, retention, LTV or causal experiment data is available.')
finally:
    conn.close()
