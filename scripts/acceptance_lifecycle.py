"""Bounded lifecycle acceptance; never shuts down WSL or deletes named data volumes."""
import json
import sys
import dev


def fingerprint(database):
    tables = dev.psql("SELECT schemaname || '.' || tablename FROM pg_tables "
                     "WHERE schemaname IN ('public','planner_internal') ORDER BY 1;", database).splitlines()
    result = {}
    for table in tables:
        schema, name = table.split('.')
        dev.identifier(schema)
        dev.identifier(name)
        result[table] = dev.psql(f"SELECT count(*) || ':' || md5(COALESCE(string_agg(to_jsonb(t)::text, "
            f"E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM {schema}.{name} t;", database)
    return result


def main(source, restored, second):
    for name in (source, restored, second):
        dev.identifier(name)
        if not name.startswith('test_'):
            raise ValueError('Lifecycle acceptance only accepts dedicated test_* databases.')
    registered = {row['database']: row for row in dev.records()}
    second_config = registered[second]
    if dev.psql("SELECT count(*) FROM trips WHERE status IN ('queued','running');", 'trip') != '0':
        raise RuntimeError('A real planner job is active; refusing to interrupt it.')
    original = fingerprint(source)
    if original != fingerprint(restored):
        raise RuntimeError('Restored records differ from the source snapshot; no containers stopped.')
    print(f'Restore verified: {len(original)} tables, including account/session/history/checkpoint contents.')
    probe_name = 'local-dev-acceptance-probe'
    if dev.run(['docker', 'ps', '-a', '--filter', f'name=^/{probe_name}$', '--format', '{{.Names}}'], capture=True).strip():
        raise RuntimeError('Probe container already exists; inspect it before retrying.')
    image = dev.envfile(dev.LOCK)['POSTGRES_IMAGE']
    dev.run(['docker', 'run', '-d', '--name', probe_name, '--label', 'local.dev.acceptance=true',
             '--network', 'local-dev', '--user', 'postgres', '--read-only', '--cap-drop', 'ALL',
             '--security-opt', 'no-new-privileges', '--memory', '128m', '--cpus', '0.5', image, 'sleep', 'infinity'])
    sql_command = ('IFS= read -r PGPASSWORD; export PGPASSWORD; exec psql -h postgres '
                   f"-U {second_config['role']} -d {second} -Atc 'SELECT 1'")

    def probe():
        result = dev.run(['docker', 'exec', '-i', probe_name, 'sh', '-c', sql_command],
                         data=second_config['password'] + '\n', capture=True)
        if result.strip() != '1':
            raise RuntimeError('Second project cannot connect.')

    probe()
    dev.backup_all()
    dev.stop_trip()
    probe()
    print('Stopping the travel workspace did not affect the independent second-project client.')
    dev.run(dev.compose('project', 'up', '-d', '--force-recreate'))
    if original != fingerprint(source):
        raise RuntimeError('Data changed while rebuilding workspace.')
    dev.stop_trip()
    dev.run(dev.compose('infra', 'up', '-d', '--force-recreate', '--wait', '--wait-timeout', '90'))
    probe()
    if original != fingerprint(source) or original != fingerprint(restored):
        raise RuntimeError('Data mismatch after PostgreSQL recreation.')
    dev.run(dev.compose('project', 'up', '-d'))
    dev.run(['docker', 'stop', probe_name])
    print('Workspace and PostgreSQL recreated; original named volumes retained and row contents verified.')
    print('Probe container stopped and retained for inspection. WSL/Ollama were not shut down.')


if __name__ == '__main__':
    main(*sys.argv[1:])
