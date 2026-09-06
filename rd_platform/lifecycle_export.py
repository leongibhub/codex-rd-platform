"""Isolated metadata export of one consistent lifecycle project revision.

No project state or source files are changed. Source file bodies and raw process
output are deliberately excluded. Only a COMPLETE manifest is a finished bundle.
"""
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import stat
from uuid import uuid4

from .lifecycle_reporting import _capture_project, lifecycle_report, sanitize_report_value


_sanitize=sanitize_report_value


def _json(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'


def _cell(value):
    if value is None: return 'UNDECIDED'
    if isinstance(value,(dict,list)): value=json.dumps(value,ensure_ascii=False,sort_keys=True)
    value=html.escape(str(value))
    for symbol in ('\\','`','[',']','(',')','*','_','|'):
        value=value.replace(symbol,'\\'+symbol)
    return value.replace('\r','').replace('\n','<br>')


def _table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+
                     ['| '+' | '.join(_cell(value) for value in row)+' |' for row in rows])+'\n'


def _is_link(path):
    try:
        details=path.lstat()
        return path.is_symlink() or bool(getattr(details,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024))
    except FileNotFoundError: return False


def _destination(destination):
    path=Path(destination)
    if '..' in path.parts: raise ValueError('destination traversal is not permitted')
    path=path.absolute()
    if path.exists() or _is_link(path): raise ValueError('export destination already exists')
    if not path.parent.is_dir(): raise ValueError('export parent must be an existing directory')
    for parent in [path.parent,*path.parent.parents]:
        if _is_link(parent): raise ValueError('export destination cannot use link or junction ancestors')
    return path.parent.resolve()/path.name


def _write_text(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(text); stream.flush(); os.fsync(stream.fileno())


def _marker(destination,value):
    temp=destination/('.export-marker-'+uuid4().hex+'.json')
    _write_text(temp,_json(value))
    os.replace(temp,destination/'export-manifest.json')


def _render_files(snapshot,versions,report):
    project=snapshot['project_id']; revision=snapshot['source_revision']; gates=snapshot['gates']
    manifest={'lifecycle_mode':'active','project_id':project,'authority':'READ_ONLY_EXPORT','source_revision':revision,
              'active_gate_register':'docs/08-project-management/gate-register.md',
              'rtm':'docs/03-requirements/requirement-traceability-matrix.md',
              'note':'Exported facts only; no new Gate decision, approval, release or source-project mode change.'}
    gate_rows=[(g['gate_id'],g.get('gate_status'),g.get('evaluation_state'),g.get('recorded_gate_status'),g.get('freshness'),g.get('current_assessment_id'),g.get('freshness_reason','')) for g in gates]
    trace=snapshot['traceability']; links=snapshot['trace_links']
    outgoing={}
    for link in links:
        if link['status']=='VALID': outgoing.setdefault(link['from']['id'],[]).append(link['to'])
    trace_rows=[]
    for row in trace:
        ident=row['requirement_id']
        related=[]; seen={ident}; queue=[ident]
        while queue:
            current=queue.pop()
            for ref in outgoing.get(current,[]):
                if ref['id'] not in seen: related.append(ref); seen.add(ref['id']); queue.append(ref['id'])
        columns=[['%s@%s'%(ref['id'],ref['version']) for ref in related if ref['type'] in types] for types in ({'DES','ADR'},{'TASK'},{'CODE_CHANGE'},{'TEST_CASE'},{'TEST_EXECUTION','EVIDENCE'},{'BUG'},{'REL'})]
        trace_rows.append((ident,row.get('version'),row['status'],*columns,row.get('missing',[])))
    evidence=[{key:e.get(key) for key in ('id','kind','status','version','source','recorded_by','recorded_role','observed_at','recorded_at','locator','metadata','supersedes_id')} for e in snapshot['evidence']]
    artifacts=[{key:a.get(key) for key in ('id','artifact_type','title','version','state','content_ref','source','created_by','created_at')} for a in snapshot['artifacts']]
    files={
        'platform-manifest.json':_json(manifest),
        'docs/08-project-management/gates.json':_json(gates),
        'docs/08-project-management/gate-register.md':'# Exported Gate Register\n\nAuthority: READ_ONLY_EXPORT. Null/UNDECIDED means no current Gate decision. Recorded status is history, not a replacement decision.\n\n'+_table(['Gate','Current Gate Status','Evaluation State','Recorded Status','Freshness','Assessment','Reason'],gate_rows),
        'docs/08-project-management/gate-assessments.json':_json(snapshot['gate_assessments']),
        'docs/08-project-management/gate-decisions.json':_json(snapshot['gate_decisions']),
        'docs/03-requirements/requirement-traceability-matrix.md':'# Exported Requirement Traceability Matrix\n\nSource-revision projection; missing links remain explicit. Referenced targets do not independently establish coverage. Full typed/versioned edges are in trace-links.json.\n\n'+_table(['Requirement','Version','Traceability','Design','Task','Code','Case','Execution/Evidence','Defect','Release','Missing'],trace_rows),
        'docs/03-requirements/traceability.json':_json(trace),
        'docs/03-requirements/trace-links.json':_json(links),
        'docs/evidence/artifact-index.json':_json(artifacts),
        'docs/evidence/version-index.json':_json(versions),
        'docs/evidence/evidence-index.json':_json(evidence),
        'docs/06-test/test-report.json':_json(report),
        'docs/06-test/test-report.md':'# Declared-scope Test Report\n\nCurrent results require fresh verified evidence. Observed Result is immutable history, not current acceptance.\n\n'+_table(['Metric','Value'],[(key,report[key]) for key in ('report_scope','total','executed','counts','complete_snapshot','conclusion','recommend_release','release_reasons')])+ '\n'+_table(['Case','Version','Type','Current Result','Observed Result','Freshness','Reason','Execution'],[(r['case_id'],r['case_version'],r['test_type'],r['result'],r['observed_result'],r['freshness'],r['freshness_reason'],r['execution_id']) for r in report['case_results']]),
        'README.md':'# Lifecycle project export\n\nProject: '+_cell(project)+'\n\nSource revision SHA-256: `'+revision['sha256']+'`\n\nThis active-project projection does not modify its source or grant approval. Only export-manifest.json status COMPLETE means all listed files were written. UNDECIDED Gates have no decision. This package includes metadata/indexes and excludes source-file bodies, inline artifact content and raw execution output.\n\n'+_table(['Fact','Value'],[('Current Gate',snapshot['lifecycle']['current_gate']),('Declared test cases',report['total']),('Test conclusion',report['conclusion']),('Recommend release',report['recommend_release'])]),
    }
    return files


def export_project(runtime,project_id,destination,*,page_size=200):
    """Export a complete project view without overwriting or modifying its source."""
    target=_destination(destination)
    snapshot,versions=_capture_project(runtime,project_id,page_size=page_size,include_versions=True)
    snapshot=_sanitize(snapshot); versions=_sanitize(versions); report=_sanitize(lifecycle_report(snapshot))
    files=_render_files(snapshot,versions,report)
    target.mkdir(exist_ok=False)
    marker={'schema_version':'lifecycle-export-v1','project_id':project_id,'status':'IN_PROGRESS',
            'created_at':datetime.now(timezone.utc).isoformat(),'source_revision':snapshot['source_revision'],'files':[]}
    try:
        _marker(target,marker)
        for relative,text in files.items():
            path=target/relative
            if path.is_absolute() and not path.is_relative_to(target): raise ValueError('unsafe generated export path')
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.parent.resolve()!=path.parent or _is_link(path.parent): raise ValueError('export directory was replaced by a link')
            _write_text(path,text)
            marker['files'].append({'path':relative,'sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),'bytes':len(text.encode('utf-8'))})
        marker.update(status='COMPLETE',completed_at=datetime.now(timezone.utc).isoformat(),collection_counts=snapshot['collection_counts'])
        _marker(target,marker)
    except BaseException as error:
        marker.update(status='FAILED',failure_type=type(error).__name__)
        try: _marker(target,marker)
        except (OSError,ValueError): pass # Existing IN_PROGRESS remains visibly incomplete.
        raise
    return dict(marker,destination=str(target))
