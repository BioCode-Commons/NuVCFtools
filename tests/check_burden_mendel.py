#!/usr/bin/env python3
"""Independent dense-counter and parental-product models for burden/Mendel edits."""
import argparse
import itertools
import json
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    genotype_checks = 0
    for first, second, ancestor, double_count in itertools.product(
            (-2, -1, 0, 1, 2, 127), (-2, -1, 0, 1, 2, 127), (0, 1, 2), (0, 1)):
        old = []
        if first != ancestor and first >= 0:
            old.append(first)
        if double_count == 0 or first != second:
            if second != ancestor and second >= 0:
                old.append(second)
        count = 2 if double_count == 0 or first != second else 1
        new = [allele for allele in (first, second)[:count] if allele != ancestor and allele >= 0]
        assert old == new
        genotype_checks += 1

    rng = random.Random(6119)
    block_width = 256
    updates = allocation_checks = 0
    scenarios = 0
    for n in (1, 2, 3, 4, 7, 16, 31, 64, 127, 128, 129, 257):
        width = 2 * n + 1
        n_blocks = (width - 1) // block_width + 1
        streams = [[], [(r, c) for c in range(width) for r in range(n)],
                   [(r, c) for c in reversed(range(width)) for r in range(n)],
                   [(r, 1) for r in range(n)], [(n - 1, width - 1)] * 300]
        streams += [[(rng.randrange(n), rng.randrange(width)) for _ in range(2000)] for _ in range(8)]
        for events in streams:
            dense = [[0] * width for _ in range(n)]
            segmented = [None for _ in range(n)]
            for individual, frequency in events:
                dense[individual][frequency] += 1
                if segmented[individual] is None:
                    segmented[individual] = [None] * n_blocks
                directory = segmented[individual]
                index, offset = divmod(frequency, block_width)
                if directory[index] is None:
                    directory[index] = [0] * min(block_width, width - index * block_width)
                    # No existing counter block is copied or deallocated during
                    # accumulation. Only the newly needed fixed block is added.
                    active = sum(len(block) for row in segmented if row is not None
                                 for block in row if block is not None)
                    assert active <= n * width
                    assert sum(len(row) for row in segmented if row is not None) <= n * n_blocks
                    allocation_checks += 1
                directory[index][offset] += 1
                updates += 1
            actual = []
            for directory in segmented:
                if directory is None:
                    actual.append([0] * width)
                else:
                    actual.append([0 if directory[c // block_width] is None else
                                   directory[c // block_width][c % block_width] for c in range(width)])
            assert dense == actual
            scenarios += 1

    mendel_checks = skipped = 0
    values = (-2147483648, -2, -1, 0, 1, 2, 2147483647)
    for c0, c1, m0, m1, f0, f1 in itertools.product(values, repeat=6):
        # The caller skips exactly -1, not every negative value.
        if -1 in (c0, c1, m0, m1, f0, f1):
            skipped += 1
            continue
        original = {(m0, f0), (m0, f1), (m1, f0), (m1, f1)}
        old_error = (c0, c1) not in original and (c1, c0) not in original
        new_error = not (((c0 == m0 or c0 == m1) and (c1 == f0 or c1 == f1))
                         or ((c1 == m0 or c1 == m1) and (c0 == f0 or c0 == f1)))
        assert old_error == new_error
        mendel_checks += 1
    out = {'all_passed': True, 'genotype_increment_order_checks': genotype_checks,
           'counter_scenarios': scenarios, 'counter_updates': updates,
           'block_allocation_bound_checks': allocation_checks,
           'block_width': block_width, 'counter_payload_copied_during_growth': 0,
           'mendel_parental_product_checks': mendel_checks, 'mendel_exact_minus_one_skips': skipped,
           'seed': 6119,
           'scope': 'Independent algorithm models; real command output must also be compared. Memory bound counts int payload and pointer slots, not allocator overhead/RSS. No existing int block is copied or replaced during accumulation. Signed int counter-overflow behavior is unchanged and not modeled.'}
    args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
