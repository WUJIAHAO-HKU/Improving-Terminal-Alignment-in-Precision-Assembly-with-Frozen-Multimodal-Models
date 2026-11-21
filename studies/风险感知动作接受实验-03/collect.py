"""Run one isolated, image-only Sol request per condition, matching round 02."""
import json
import os
import sys
from pathlib import Path

import model_client as client

client.responses = client.D / 'isolated-responses'
client.responses.mkdir(exist_ok=True)
assert len(client.rows) == 300

def main():
    smoke = sys.argv[1:] == ['smoke']
    jobs = [(row, mode, 'gpt-6.2-sol') for row in client.rows for mode in ('direct', 'measured')]
    if smoke:
        client.predict(jobs[0])
        return
    assert (client.D / 'policy-lock.json').exists()
    client.run(jobs)
    actions = {}
    for row in client.rows:
        direct = client.get(row, 'direct')
        measured = client.get(row, 'measured')
        actions[row['id']] = dict(direct=direct, always=measured, oracle=[-row['x'], -row['y']])
    (client.D / 'actions.json').write_text(json.dumps(actions, indent=2))

if __name__ == '__main__':
    main()
