"""Additive lifecycle migration; no V2 table or journaling changes."""
import hashlib
from datetime import datetime, timezone

TABLES = ('projects', 'gates', 'work_orders', 'artifacts', 'trace_links', 'test_models',
          'test_cases', 'test_executions', 'defects', 'gate_assessments', 'gate_decisions', 'evidence', 'releases')
SCHEMA = '\n'.join(
    f'CREATE TABLE IF NOT EXISTS lc_{name} (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), status TEXT NOT NULL, data TEXT NOT NULL);'
    f'CREATE INDEX IF NOT EXISTS lc_{name}_project_status ON lc_{name}(project_id,status,id);'
    for name in TABLES
) + '''
CREATE TABLE IF NOT EXISTS lc_artifact_versions (artifact_id TEXT NOT NULL REFERENCES lc_artifacts(id), version INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(artifact_id,version));
CREATE TABLE IF NOT EXISTS lc_test_case_versions (case_id TEXT NOT NULL REFERENCES lc_test_cases(id), version INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(case_id,version));
CREATE TABLE IF NOT EXISTS lc_release_versions (release_id TEXT NOT NULL REFERENCES lc_releases(id), version INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(release_id,version));
CREATE TABLE IF NOT EXISTS lc_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL REFERENCES projects(id), event_id TEXT NOT NULL UNIQUE, type TEXT NOT NULL, entity_id TEXT NOT NULL, data TEXT NOT NULL, occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS lc_events_project_sequence ON lc_events(project_id,sequence);
CREATE TABLE IF NOT EXISTS lc_migrations (version INTEGER PRIMARY KEY, sha256 TEXT NOT NULL, applied_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS lc_active_agent ON lc_work_orders(json_extract(data,'$.agent_id')) WHERE status='CLAIMED';
CREATE UNIQUE INDEX IF NOT EXISTS lc_active_case ON lc_test_executions(json_extract(data,'$.case_id'),json_extract(data,'$.case_version')) WHERE status='ACTIVE';
CREATE INDEX IF NOT EXISTS lc_trace_from ON lc_trace_links(project_id,json_extract(data,'$.from.id'),status);
CREATE INDEX IF NOT EXISTS lc_trace_to ON lc_trace_links(project_id,json_extract(data,'$.to.id'),status);
'''

MIGRATION_2 = 'CREATE INDEX IF NOT EXISTS lc_events_project_entity_sequence ON lc_events(project_id,entity_id,sequence);'


def migrate(connection):
    digest = hashlib.sha256(SCHEMA.encode()).hexdigest()
    digest2 = hashlib.sha256(MIGRATION_2.encode()).hexdigest()
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lc_migrations'").fetchone()
    if exists:
        old = connection.execute('SELECT sha256 FROM lc_migrations WHERE version=1').fetchone()
        if old:
            if old[0] != digest:
                raise ValueError('lifecycle migration digest mismatch')
            existing = connection.execute('SELECT sha256 FROM lc_migrations WHERE version=2').fetchone()
            if existing and existing[0] != digest2:
                raise ValueError('lifecycle migration digest mismatch')
            connection.execute(MIGRATION_2)
            if not existing:
                connection.execute('INSERT INTO lc_migrations VALUES (2,?,?)', (digest2, datetime.now(timezone.utc).isoformat()))
            return
    # executescript commits implicitly; execute each DDL in the owning transaction.
    for statement in SCHEMA.split(';'):
        if statement.strip(): connection.execute(statement)
    connection.execute('INSERT INTO lc_migrations VALUES (1,?,?)', (digest, datetime.now(timezone.utc).isoformat()))
    connection.execute(MIGRATION_2)
    connection.execute('INSERT INTO lc_migrations VALUES (2,?,?)', (digest2, datetime.now(timezone.utc).isoformat()))
