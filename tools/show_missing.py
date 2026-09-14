"""Print the uncovered regions of one file from a coverage report, with the
enclosing function and a little context, so a gap can be read without
paging through the whole file.

    python3 tools/show_missing.py ../out.txt formshare/views/form.py [context] [max lines]

The report is the text pytest-cov prints (``pytest --cov=formshare`` with the
default terminal report) or the output of ``coverage report -m``. Each region
is printed as ``--- lines  [in function()]`` followed by the lines, the
uncovered ones marked with ``>``.
"""

import re
import sys


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    report, target = argv[1], argv[2]
    context = int(argv[3]) if len(argv) > 3 else 2
    cap = int(argv[4]) if len(argv) > 4 else 40

    spec = None
    for line in open(report):
        if line.startswith(target + " "):
            parts = line.split()
            stats, spec = parts[1:4], " ".join(parts[4:])
            break
    if spec is None:
        sys.exit("not in the report: " + target)

    source = open(target).read().splitlines()
    enclosing = {}
    current = "<module>"
    for number, text in enumerate(source, 1):
        match = re.match(r"\s*(?:async\s+)?(def|class)\s+(\w+)", text)
        if match:
            current = match.group(2) + ("()" if match.group(1) == "def" else "")
        enclosing[number] = current

    print("=" * 78)
    print(target, "statements/missed/covered:", stats)
    print("=" * 78)
    for chunk in spec.split(", "):
        if not chunk:
            continue
        if "-" in chunk:
            first, last = map(int, chunk.split("-"))
        else:
            first = last = int(chunk)
        low, high = max(1, first - context), min(len(source), last + context)
        print("--- %s  [in %s]" % (chunk, enclosing.get(first)))
        shown = 0
        for number in range(low, high + 1):
            mark = ">" if first <= number <= last else " "
            print("%s%5d  %s" % (mark, number, source[number - 1]))
            shown += 1
            if shown >= cap and number < high:
                print("      ... (%d more lines to %d)" % (high - number, high))
                break


if __name__ == "__main__":
    main(sys.argv)
