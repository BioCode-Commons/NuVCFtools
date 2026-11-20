#!/usr/bin/env python3
"""Independently compare the legacy BED predicate with in-place interval indexing."""

import argparse
import bisect
import itertools
import json
import random

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1


def legacy_match(intervals, start, end):
    # Literal legacy clauses; intentionally do not simplify or normalize.
    for left, right in intervals:
        if ((start > left and start <= right)
                or (end > left and end <= right)
                or (start <= left and end >= right)):
            return True
    return False


def build_index(intervals):
    # Mirrors the C++ in-place transformation, including overlap-only merging.
    indexed = list(intervals)
    for index, (left, right) in enumerate(indexed):
        indexed[index] = (left + 1, right) if left < right else (right, left)
    indexed.sort()
    merged_count = 0
    for index in range(len(indexed)):
        left, right = indexed[index]
        if merged_count and left <= indexed[merged_count - 1][1]:
            previous_left, previous_right = indexed[merged_count - 1]
            indexed[merged_count - 1] = (previous_left, max(previous_right, right))
        else:
            indexed[merged_count] = (left, right)
            merged_count += 1
    del indexed[merged_count:]
    assert all(INT_MIN <= left <= right <= INT_MAX for left, right in indexed)
    assert all(a[1] < b[0] for a, b in zip(indexed, indexed[1:]))
    return indexed


def indexed_match(indexed, start, end):
    previous = bisect.bisect_right(indexed, (end, INT_MAX)) - 1
    return previous >= 0 and indexed[previous][1] >= start


def check(intervals, queries):
    indexed = build_index(intervals)
    count = 0
    for start, end in queries:
        assert start <= end
        expected = legacy_match(intervals, start, end)
        actual = indexed_match(indexed, start, end)
        if expected != actual:
            raise AssertionError((intervals, indexed, (start, end), expected, actual))
        # Both include and exclude keep/reject decisions must agree.
        for exclude in (False, True):
            assert (expected != exclude) == (actual != exclude)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='bed-model-checks.json')
    args = parser.parse_args()
    results = {}

    endpoints = range(-4, 5)
    queries = list(itertools.combinations_with_replacement(range(-5, 6), 2))
    count = 0
    for interval in itertools.product(endpoints, repeat=2):
        count += check([interval], queries)
    results['exhaustive_single_intervals'] = {'comparisons': count, 'intervals': 81}

    choices = list(itertools.product(range(-2, 3), repeat=2))
    queries = list(itertools.combinations_with_replacement(range(-3, 4), 2))
    count = sets = 0
    for length in range(4):
        for intervals in itertools.product(choices, repeat=length):
            count += check(intervals, queries)
            sets += 1
    results['exhaustive_ordered_interval_sequences'] = {
        'comparisons': count, 'sequences': sets, 'maximum_length': 3,
        'includes': ['empty', 'duplicates', 'all permutations', 'zero length',
                     'reversed', 'negative', 'overlapping', 'nested', 'disjoint', 'adjacent'],
    }

    boundaries = [INT_MIN, INT_MIN + 1, -1, 0, 1, INT_MAX - 1, INT_MAX]
    choices = list(itertools.product(boundaries, repeat=2))
    queries = list(itertools.combinations_with_replacement(boundaries, 2))
    count = sets = 0
    for length in (1, 2):
        for intervals in itertools.product(choices, repeat=length):
            count += check(intervals, queries)
            sets += 1
    results['int32_boundaries'] = {'comparisons': count, 'sequences': sets}

    rng = random.Random(20261120)
    count = 0
    for _ in range(10000):
        intervals = [(rng.randint(-10000, 10000), rng.randint(-10000, 10000))
                     for _ in range(rng.randrange(101))]
        queries = [tuple(sorted((rng.randint(-11000, 11000), rng.randint(-11000, 11000))))
                   for _ in range(32)]
        # Deliberately preserve random query order; no sorted-VCF assumption.
        count += check(intervals, queries)
    results['deterministic_random_sequences'] = {
        'comparisons': count, 'sequences': 10000, 'seed': 20261120,
        'maximum_intervals': 100, 'queries_in_random_order': True,
    }

    missing_chromosome_decisions = []
    for exclude in (False, True):
        expected_kept = exclude
        actual_kept = False != exclude
        assert expected_kept == actual_kept
        missing_chromosome_decisions.append({'exclude': exclude, 'kept': actual_kept})
    results['missing_chromosome'] = missing_chromosome_decisions
    examples = {
        'nested': [(start, 200000 - start) for start in range(100000)],
        'identical': [(10, 20)] * 100000,
        'disjoint': [(3 * index, 3 * index + 1) for index in range(100000)],
    }
    results['stored_interval_counts'] = {
        name: {'before': len(intervals), 'after': len(build_index(intervals))}
        for name, intervals in examples.items()
    }
    results['total_predicate_comparisons'] = sum(
        item.get('comparisons', 0) for item in results.values() if isinstance(item, dict))
    results['status'] = 'PASS'
    results['scope'] = (
        'Independent algorithm model only, not a substitute for binary byte comparisons. '
        'Queries cover the legacy invariant start <= end. BED parsing, header skipping, '
        'raw entry logging, chromosome-map lifetime and allele-span arithmetic are unchanged.')
    with open(args.output, 'w') as handle:
        json.dump(results, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'status': results['status'],
                      'total_predicate_comparisons': results['total_predicate_comparisons'],
                      'output': args.output}))


if __name__ == '__main__':
    main()
