"""Run with the SDK venv and reviewed local producer overrides; no database writes."""
import json
from pathlib import Path
import tempfile
from cldk import CLDK
from cldk.analysis import AnalysisLevel
from cldk.analysis.commons.backend_config import CodeAnalyzerConfig, PyCodeAnalyzerConfig
from cldk.analysis.commons.identity import resolve_identity

SOURCES = [('python','main.py','def helper():\n    return 1\ndef main():\n    return helper()\n'),('typescript','server.ts','export function helper() { return 1; }\nexport function main() { return helper(); }\n'),('typescript','server.js','export function helper() { return 1; }\nexport function main() { return helper(); }\n'),('java','Main.java','public class Main { public static int helper() { return 1; } public static int main() { return helper(); } }'),('go','main.go','package main\nfunc helper() int { return 1 }\nfunc main() { helper() }\n')]

def walk(value):
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)

def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='namespace-smoke-') as directory:
        base=Path(directory)
        for language, filename, source in SOURCES:
            for case, app, namespace in [('explicit', 'currencyservice', 'online-boutique'),('sibling','paymentservice','online-boutique'),('encoded', "-svc !'()*~%雪", "team !'()*~%"),('default',None,None)]:
                project=base/f'{language}-{filename}-{case}'/'inventory'
                project.mkdir(parents=True)
                (project/filename).write_text(source)
                if language=='go':
                    (project/'go.mod').write_text('module smoke\n\ngo 1.21\n')
                config_type=PyCodeAnalyzerConfig if language=='python' else CodeAnalyzerConfig
                config=config_type(cache_dir=project.parent/'cache',application_name=app,namespace=namespace)
                analysis=getattr(CLDK,language)(project_path=project,analysis_level=AnalysisLevel.call_graph,backend=config)
                envelope=analysis.backend.analysis
                payload=json.loads(envelope.model_dump_json())
                application=analysis.get_application_view()
                root=resolve_identity(app or 'inventory',namespace).application_id
                assert type(payload['identity_version']) is int and payload['identity_version']==2
                assert application.id==root
                assert application.application_name==(app or 'inventory')
                assert application.identity_namespace==(namespace or app or 'inventory')
                strings={v for v in walk(payload) if isinstance(v,str) and v.startswith('can://')}
                assert strings and all(v==root or v.startswith(root+'/') for v in strings), strings
                ids={v['id'] for v in walk(payload) if isinstance(v,dict) and isinstance(v.get('id'),str)}
                endpoint_count=0
                for value in walk(payload):
                    if isinstance(value,dict):
                        for key in ('source','target','src','dst','caller','callee'):
                            endpoint=value.get(key)
                            if isinstance(endpoint,str) and endpoint.startswith('can://'):
                                assert endpoint in ids,(language,key,endpoint)
                                endpoint_count+=1
                assert all(module.id in ids for module in application.symbol_table.values())
                results.append(dict(language=language,file=filename,case=case,root=root,entities=len(ids),references=len(strings),endpoints=endpoint_count))
    print(json.dumps(results,indent=2))
if __name__=='__main__':
    main()
