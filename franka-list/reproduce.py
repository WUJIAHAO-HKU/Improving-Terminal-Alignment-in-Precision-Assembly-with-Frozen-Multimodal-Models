"""Recreate the six-arm comparison from released branch receipts, ranks and software."""
import argparse
from pathlib import Path
import tarfile
import tempfile
from analyze_lists import analyze
from verify import verify

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', action='store_true', help='also recompute all physical labels from trajectories and geometry')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        with tarfile.open(ROOT/'source.tar.gz') as blob:
            blob.extractall(work, filter='data')
        records = work/'formal/records'
        records.mkdir()
        batches = sorted((ROOT/'archives').glob('batch-*.tgz'))
        assert len(batches) == 64
        with tarfile.open(ROOT/'locked-lists-before-overhead.tgz') as frozen:
            sealed = {Path(x.name).as_posix(): frozen.extractfile(x).read() for x in frozen if x.isfile()}
        assert len(sealed) == 128
        for archive in batches:
            with tarfile.open(archive) as blob:
                for item in blob:
                    if not item.isfile():
                        continue
                    path = Path(item.name)
                    if path.parts[0] == 'rankings':
                        assert blob.extractfile(item).read() == sealed.pop(path.as_posix())
                    elif path.name not in {'public.json', 'receipt.json', 'grip.json', 'gates.json'}:
                        continue
                    blob.extract(item, records, filter='data')
        assert not sealed
        if args.audit:
            verify(work, ROOT/'archives')
        dest = work/'computed'
        analyze(work, dest)
        for p in sorted(dest.glob('*.csv')):
            assert p.read_bytes() == (ROOT/'results'/p.name).read_bytes(), p.name
        import csv
        with (dest/'arms.csv').open(encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                print(row['model'], row['policy'], row['gate'], row['success']+'/320')
        print('All five result files match the released tables.')
if __name__ == '__main__':
    main()
