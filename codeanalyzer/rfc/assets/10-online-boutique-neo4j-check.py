"""Verify Online Boutique identity through one live Neo4j database and SDK backends."""
from __future__ import annotations
import json, logging, os, time, traceback
from pathlib import Path
from neo4j import GraphDatabase
from cldk import CLDK
from cldk.analysis.commons.backend_config import Neo4jConnectionConfig

logging.getLogger('neo4j').setLevel(logging.ERROR)
URI=os.environ.get('NEO4J_URI','bolt://127.0.0.1:17687')
DB=os.environ.get('NEO4J_DATABASE','neo4j')
AUTH=(os.environ.get('NEO4J_USERNAME','neo4j'),os.environ.get('NEO4J_PASSWORD','neo4j'))
SERVICES={'currencyservice':'typescript','paymentservice':'typescript','checkoutservice':'go','frontend':'go','productcatalogservice':'go','shippingservice':'go','emailservice':'python','loadgenerator':'python','recommendationservice':'python','shoppingassistantservice':'python','adservice':'java'}
RESULTS=[]

def attach(name, language, namespace='online-boutique'):
    return getattr(CLDK,language)(backend=Neo4jConnectionConfig(uri=URI,username=AUTH[0],password=AUTH[1],database=DB,application_name=name,namespace=namespace))

def scopes(value):
    yield value
    for attr in ('types','functions','callables','methods'):
        children=getattr(value,attr,{})
        if isinstance(children,dict):
            for child in children.values():
                yield from scopes(child)

with GraphDatabase.driver(URI,auth=AUTH) as driver:
    driver.verify_connectivity()
    with driver.session(database=DB) as session:
        def run(q,**params):return [r.data() for r in session.run(q,**params)]
        def totals():return run('MATCH (n) OPTIONAL MATCH (n)-[r]->() RETURN count(DISTINCT n) AS nodes,count(r) AS relationships')[0]
        anchors=run('MATCH (a) WHERE a.identity_namespace=$ns RETURN a.id AS id,a.application_name AS name,a.identity_namespace AS namespace,a.identity_version AS version',ns='online-boutique')
        assert {a['id'] for a in anchors}=={f'can://online-boutique/{name}' for name in SERVICES},anchors
        assert len(anchors)==11 and all(type(a['version']) is int and a['version']==2 for a in anchors)
        before=totals();attached={}
        for name,language in SERVICES.items():
            root=f'can://online-boutique/{name}';start=time.monotonic()
            try:
                analysis=attach(name,language);attached[name]=analysis
                assert 'neo4j' in type(analysis.backend).__module__,type(analysis.backend)
                view=analysis.get_application_view();assert view.id==root
                modules=list(view.symbol_table.values());ids={m.id for m in modules}
                expected={r['id'] for r in run('MATCH (a {id:$root})-[rel]->(m) WHERE type(rel) IN $types RETURN m.id AS id',root=root,types=['TS_HAS_MODULE','GO_HAS_MODULE','PY_HAS_MODULE','J_HAS_MODULE'])}
                assert ids and ids==expected,(name,ids,expected)
                declared=0
                for module in modules:
                    for value in scopes(module):
                        ident=getattr(value,'id',None)
                        if ident is not None:
                            assert ident and ident.startswith(root+'/'),(name,type(value).__name__,ident)
                            declared+=1
                row=dict(service=name,language=language,status='pass',modules=len(ids),declarations=declared,seconds=round(time.monotonic()-start,3))
            except Exception as exc:
                row=dict(service=name,language=language,status='fail',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
            RESULTS.append(row);print(json.dumps(row),flush=True)
        assert all(r['status']=='pass' for r in RESULTS),RESULTS
        currency=attached['currencyservice'];payment=attached['paymentservice']
        for order in [('currencyservice','paymentservice'),('paymentservice','currencyservice')]:
            backends={name:attached[name] for name in order}
            absent=backends['currencyservice'].locate('server.js',28)
            assert absent.callable is None and absent.node_id is None
            assert any(d.code=='module_scope' for d in absent.diagnostics),absent
            found=backends['paymentservice'].locate('server.js',28)
            assert found.callable and found.callable.name=='constructor',found
            assert found.node_id.startswith('can://online-boutique/paymentservice/javascript/server.js/'),found
        found=currency.locate('server.js',92)
        assert found.callable and found.callable.name=='_loadProto',found
        for reader,foreign in [(currency,'paymentservice'),(payment,'currencyservice')]:
            try:reader.locate(f'can://online-boutique/{foreign}/javascript/server.js',28)
            except ValueError:pass
            else:raise AssertionError('foreign service URI accepted')
        currency_id='can://online-boutique/currencyservice/javascript/server.js'
        payment_id='can://online-boutique/paymentservice/javascript/server.js'
        distinct=run('UNWIND $ids AS id MATCH (m:TSModule {id:id}) RETURN DISTINCT m.id AS id',ids=[currency_id,payment_id,currency_id])
        assert {r['id'] for r in distinct}=={currency_id,payment_id}
        finding=run('WITH {module_id:$id,line:28} AS finding MATCH (m:TSModule {id:finding.module_id}) RETURN m.id AS id',id=currency_id)
        assert finding==[{'id':currency_id}],finding
        duplicates=run('MATCH (n) WHERE n.id STARTS WITH $prefix WITH n.id AS id,count(*) AS n WHERE n>1 RETURN id,n LIMIT 10',prefix='can://online-boutique/')
        assert not duplicates,duplicates
        cross=run('MATCH (a)-[r]->(b) WHERE a.id STARTS WITH $prefix AND b.id STARTS WITH $prefix AND split(a.id,"/")[3] <> split(b.id,"/")[3] RETURN count(r) AS n',prefix='can://online-boutique/')
        assert cross==[{'n':0}],cross
        assert totals()==before,'read-only SDK attachment mutated graph'
        summary=dict(services=len(RESULTS),service_results=RESULTS,graph=before,wrong_service_regression='pass',reverse_backend_order='pass',canonical_dedup='pass',finding_equality_join='pass',cross_service_relationships=0,duplicate_canonical_nodes=0,sdk_read_only='pass')
        target=Path(os.environ.get('ONLINE_BOUTIQUE_RESULT','/private/tmp/online-boutique-namespace-check/live-verification.json'));target.write_text(json.dumps(summary,indent=2)+'\n')
        print('PASS',json.dumps({k:v for k,v in summary.items() if k!='service_results'}),flush=True)
