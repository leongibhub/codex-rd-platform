"""Shared storage, provenance and version-reference validation."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from uuid import uuid4

from .store import Store
from .lifecycle_store import TABLES

ARTIFACT_TYPES = {'BG', 'MR', 'PRD', 'REQ', 'NFR', 'DES', 'ADR', 'TASK', 'CODE_CHANGE', 'CR', 'RISK', 'DOC', 'TEST_MODEL'}
STATES = {'DRAFT', 'BASELINED', 'APPROVED', 'OBSOLETE'}
EVIDENCE_STATES = {'PENDING', 'NOT_AVAILABLE', 'NOT_EXECUTED', 'INFERRED', 'OBSERVED', 'VERIFIED'}


class LifecycleBase:
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def ident(prefix): return prefix + '-' + uuid4().hex

    @staticmethod
    def text(value, field):
        if not isinstance(value, str) or not value.strip(): raise ValueError(field + ' must be non-empty text')
        return value

    @staticmethod
    def enum(value, allowed, field):
        if not isinstance(value, str) or value not in allowed: raise ValueError('invalid ' + field)
        return value

    @staticmethod
    def integer(value, field, low=1, high=2147483647):
        if type(value) is not int or not low <= value <= high: raise ValueError('invalid ' + field)
        return value

    @staticmethod
    def strings(value, field, nonempty=True):
        if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(v, str) or not v.strip() for v in value) or len(set(value)) != len(value):
            raise ValueError(field + ' must be a unique list of strings')
        return value

    @staticmethod
    def digest(value): return hashlib.sha256(Store.dumps(value).encode('utf-8')).hexdigest()

    def safe_json(self, value):
        Store.dumps(value)
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str): raise ValueError('JSON keys must be strings')
                if re.search(r'(token|password|cookie|authorization|private_key|secret)', key, re.I):
                    if item != '[REDACTED_SECRET]' and not (isinstance(item, str) and item.startswith('secret-ref:')):
                        raise ValueError('sensitive field must use a secret reference or redaction')
                self.safe_json(item)
        elif isinstance(value, list):
            for item in value: self.safe_json(item)
        elif isinstance(value, str):
            if self.redact_text(value) != value:
                raise ValueError('sensitive text must be redacted before registration')

    @staticmethod
    def redact_text(value):
        from .runner import _secret_values
        for secret in _secret_values([], ()):
            value = value.replace(secret, '[REDACTED_SECRET]')
        value = re.sub(r'(?i)\b(Bearer|Basic)\s+(?!\[REDACTED(?:_SECRET)?\])[^\s\"\'<>;,]+', r'\1 [REDACTED_SECRET]', value)
        value = re.sub(r'(?i)\b(password|api[_-]?key|access[_-]?token|cookie|authorization)\s*[:=]\s*(?!\[REDACTED(?:_SECRET)?\]|secret-ref:)[^\s\"\'<>;,]+', r'\1=[REDACTED_SECRET]', value)
        value = re.sub(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?(?:-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|$)', '[REDACTED_SECRET]', value)
        return value

    def redact_projection(self,value):
        if isinstance(value,dict): return {k:self.redact_projection(v) for k,v in value.items()}
        if isinstance(value,list): return [self.redact_projection(v) for v in value]
        return self.redact_text(value) if isinstance(value,str) else value

    def get(self, c, table, ident):
        assert table in TABLES
        self.text(ident, 'id')
        row = c.execute(f'SELECT data,status FROM lc_{table} WHERE id=?', (ident,)).fetchone()
        if row is None: raise KeyError(table + ' not found: ' + ident)
        result=Store.loads(row[0])
        if table=='gate_assessments': result['status']=row[1]
        return result

    def rows(self, c, table, project, *, limit=None):
        assert table in TABLES
        sql = f'SELECT data,status FROM lc_{table} WHERE project_id=? ORDER BY rowid'
        args = (project,)
        if limit is not None: sql += ' LIMIT ?'; args += (limit,)
        return [dict(Store.loads(r[0]),status=r[1]) if table=='gate_assessments' else Store.loads(r[0]) for r in c.execute(sql, args)]

    def put(self, c, table, row, *, new=False):
        assert table in TABLES
        status = row.get('status', row.get('state', 'CURRENT'))
        if new:
            if c.execute(f'SELECT 1 FROM lc_{table} WHERE id=?', (row['id'],)).fetchone(): raise ValueError(table + ' id already exists')
            c.execute(f'INSERT INTO lc_{table} VALUES (?,?,?,?)', (row['id'], row['project_id'], status, Store.dumps(row)))
        else: c.execute(f'UPDATE lc_{table} SET status=?,data=? WHERE id=?', (status, Store.dumps(row), row['id']))
        return row

    def event(self, c, project, kind, entity, data):
        now = self.now()
        c.execute('INSERT INTO lc_events(project_id,event_id,type,entity_id,data,occurred_at,recorded_at) VALUES (?,?,?,?,?,?,?)', (project,self.ident('event'),kind,entity,Store.dumps(data),now,now))

    def project(self, c, ident): return self.get(c, 'projects', ident)

    def agent(self, c, ident, roles=None):
        self.text(ident, 'agent_id')
        row = c.execute('SELECT * FROM agents WHERE id=?', (ident,)).fetchone()
        if row is None: raise ValueError('registered agent required')
        if roles and row['role'] not in roles: raise ValueError('agent role is not permitted')
        return dict(row)

    def source(self, c, value):
        if not isinstance(value, dict): raise ValueError('source provenance required')
        self.enum(value.get('kind'), {'host', 'tool', 'import', 'model'}, 'source kind')
        self.agent(c, value.get('actor'))
        self.safe_json(value)
        return value

    def content(self, c, project, value):
        if not isinstance(value, dict): raise ValueError('content_ref must be object')
        if ('inline_json' in value) == ('path' in value): raise ValueError('exactly one inline_json or path required')
        if 'inline_json' in value:
            self.safe_json(value['inline_json'])
            raw = Store.dumps(value['inline_json']).encode('utf-8')
            if len(raw) > 1048576: raise ValueError('inline content exceeds 1 MiB')
            digest = hashlib.sha256(raw).hexdigest()
            if 'sha256' in value and value['sha256'] != digest: raise ValueError('content hash mismatch')
            return {'inline_json': value['inline_json'], 'sha256': digest}
        path = Path(self.text(value.get('path'), 'path'))
        if path.is_absolute() or '..' in path.parts: raise ValueError('path must be confined to repository')
        root = Path(self.project(c, project)['repository_root'])
        full = (root / path).resolve()
        if not full.is_relative_to(root) or not full.is_file(): raise ValueError('path is outside repository or missing')
        digest = hashlib.sha256(full.read_bytes()).hexdigest()
        if value.get('sha256') != digest: raise ValueError('content hash mismatch')
        return {'path': path.as_posix(), 'sha256': digest}

    def content_current(self, c, project, content):
        try: return self.content(c, project, content)['sha256'] == content['sha256']
        except (ValueError, OSError): return False

    def ref(self, c, project, value, *, current=True):
        if not isinstance(value, dict): raise ValueError('reference must be {type,id,version}')
        kind, ident = value.get('type'), value.get('id')
        self.text(kind,'reference type')
        table = {'TEST_CASE':'test_cases','TEST_EXECUTION':'test_executions','BUG':'defects','REL':'releases','EVIDENCE':'evidence','TEST_MODEL':'test_models'}.get(kind)
        if table is None:
            self.enum(kind, ARTIFACT_TYPES | {'ARTIFACT_VERSION'}, 'reference type')
            table = 'artifacts'
        row = self.get(c, table, ident)
        if row['project_id'] != project: raise ValueError('reference belongs to another project')
        if table == 'artifacts' and kind != 'ARTIFACT_VERSION' and row['artifact_type'] != kind: raise ValueError('reference type mismatch')
        if current and table == 'artifacts' and not self.content_current(c, project, row['content_ref']): raise ValueError('artifact content hash no longer matches')
        version = self.integer(value.get('version', row.get('version', 1)), 'reference version')
        if current and version != row.get('version', 1): raise ValueError('stale reference version')
        if not current and table == 'artifacts':
            if not c.execute('SELECT 1 FROM lc_artifact_versions WHERE artifact_id=? AND version=?', (ident,version)).fetchone(): raise ValueError('missing artifact version')
        elif version != row.get('version', 1): raise ValueError('stale reference version')
        return {'type':kind,'id':ident,'version':version}

    def refs(self, c, project, values, *, nonempty=True):
        if not isinstance(values,list) or (nonempty and not values): raise ValueError('references required')
        result = [self.ref(c,project,v) for v in values]
        if len({Store.dumps(v) for v in result}) != len(result): raise ValueError('duplicate references')
        return result

    def evidence_refs(self, c, project, values, *, kinds=None, roles=None, nonempty=True):
        refs = self.refs(c, project, values, nonempty=nonempty)
        result = []
        for ref in refs:
            if ref['type'] != 'EVIDENCE': raise ValueError('evidence reference required')
            e = self.get(c,'evidence',ref['id'])
            if c.execute("SELECT 1 FROM lc_evidence WHERE project_id=? AND json_extract(data,'$.supersedes_id')=?",(project,e['id'])).fetchone(): raise ValueError('evidence has been superseded')
            if e['status'] != 'VERIFIED' or (kinds and e['kind'] not in kinds): raise ValueError('qualified verified evidence required')
            if roles and e.get('recorded_role') not in roles: raise ValueError('independent evidence role required')
            if not self.content_current(c, project, e['locator']): raise ValueError('evidence content changed')
            for linked in e.get('metadata',{}).get('artifact_refs',[]): self.ref(c,project,linked)
            result.append(e)
        return result
