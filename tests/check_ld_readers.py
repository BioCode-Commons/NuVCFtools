#!/usr/bin/env python3
"""Compare the actual old and new LD temporary readers on binary file inputs.

The two reader definitions and the candidate's bounded-byte helper are extracted
from source and compiled as C++98. This probes decoding and the final stream
contract; it is not a CLI regression or a performance benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HARNESS = r'''
#include <algorithm>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdint.h>
#include <string>
#include <utility>
#include <vector>
using namespace std;

@GENOTYPE_TYPE@

class variant_file
{
public:
    void read_temp_site(ifstream &, string &, int &, vector<ld_genotype> &);
    void read_big_temp_site(ifstream &, string &, int &, int &, vector<ld_genotype> &);
    void read_temp_site_header(ifstream &, string &, int &);
    void read_big_temp_site_header(ifstream &, string &, int &, int &);
    void read_temp_site_payload(ifstream &, vector<ld_genotype> &);
    void read_big_temp_site_payload(ifstream &, vector<ld_genotype> &);
    void discard_temp_site_payload(ifstream &, size_t);
};
class baseline_variant_file
{
public:
    void read_temp_site(ifstream &, string &, int &, vector<pair<int,int> > &);
    void read_big_temp_site(ifstream &, string &, int &, int &, vector<pair<int,int> > &);
};

@DEFINITIONS@

struct Result
{
    string chrom;
    int pos;
    int alleles;
    vector<pair<int,int> > genotypes;
    int state;
    streamsize count;
    streamoff position;
    string remaining;
};

Result run(const string &path, bool candidate, bool big, size_t samples)
{
    Result result;
    result.chrom = "unchanged";
    result.pos = -12345;
    result.alleles = -12345;
    result.genotypes.assign(samples, make_pair(-12345,-23456));
    ifstream input(path.c_str(), ios::in | ios::binary);
    if (candidate)
    {
        variant_file reader;
        vector<ld_genotype> genotypes(samples, make_pair(-12345,-23456));
        if (big) reader.read_big_temp_site(input, result.chrom, result.pos, result.alleles, genotypes);
        else reader.read_temp_site(input, result.chrom, result.pos, genotypes);
        result.genotypes.assign(genotypes.begin(), genotypes.end());
    }
    else
    {
        baseline_variant_file reader;
        if (big) reader.read_big_temp_site(input, result.chrom, result.pos, result.alleles, result.genotypes);
        else reader.read_temp_site(input, result.chrom, result.pos, result.genotypes);
    }
    result.state = input.rdstate();
    result.count = input.gcount();
    input.clear();
    result.position = input.tellg();
    result.remaining.assign(istreambuf_iterator<char>(input), istreambuf_iterator<char>());
    return result;
}

void save_result(const string &path, const Result &result)
{
    ofstream output(path.c_str());
    output << "state=" << result.state << " gcount=" << result.count << " position=" << result.position << '\n';
    output << "chrom=" << result.chrom << " pos=" << result.pos << " alleles=" << result.alleles << '\n';
    for (size_t i=0; i<result.genotypes.size(); ++i)
        output << result.genotypes[i].first << ',' << result.genotypes[i].second << '\n';
}

bool compare(const string &directory, const string &name, bool big, size_t samples,
             size_t available, int seed, bool suffix, const string &chrom)
{
    const string path = directory + "/input.bin";
    ofstream output(path.c_str(), ios::out | ios::binary);
    output.write(chrom.data(), chrom.size());
    output.put('\n');
    const int pos = seed % 2 ? -123456789 : 123456789;
    output.write(reinterpret_cast<const char*>(&pos), sizeof(pos));
    if (big) output.put(static_cast<char>(seed));
    for (size_t i=0; i<available; ++i)
        output.put(static_cast<char>((seed + i*73) & 255));
    if (suffix) output.write("next\0record\n", 12);
    output.close();
    const Result old = run(path, false, big, samples);
    const Result now = run(path, true, big, samples);
    const bool equal = old.chrom == now.chrom && old.pos == now.pos && old.alleles == now.alleles &&
        old.genotypes == now.genotypes && old.state == now.state && old.count == now.count &&
        old.position == now.position && old.remaining == now.remaining;
    cout << name << '\t' << equal << '\t' << old.state << '\t' << now.state
         << '\t' << old.count << '\t' << now.count << '\t' << old.position << '\t' << now.position
         << '\t' << old.remaining.size() << '\t' << now.remaining.size() << '\n';
    if (!equal)
    {
        save_result(directory + "/" + name + "-baseline.txt", old);
        save_result(directory + "/" + name + "-candidate.txt", now);
    }
    return equal;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    const string directory = argv[1];
    unsigned int failures = 0;
    const size_t sizes[] = {0, 1, 2, 3, 2047, 2048, 2049, 4094, 4095, 4096, 4097, 4098, 8191, 8192, 8193, 10001};
    const size_t cuts[] = {0, 1, 2, 3, 2047, 2048, 2049, 4094, 4095, 4096, 4097, 4098, 8191, 8192, 8193};
    const int seeds[] = {0, 2, 127, 128, 254, 255};
    for (unsigned int big=0; big<2; ++big)
    {
        // Every possible input char, also as the last successful byte before EOF.
        for (int seed=0; seed<256; ++seed)
            for (unsigned int truncated=0; truncated<2; ++truncated)
            {
                const size_t samples = 6;
                ostringstream name;
                name << "all_bytes_" << big << '_' << seed << '_' << truncated;
                if (!compare(directory, name.str(), big != 0, samples,
                             truncated ? 1 : samples*(big+1), seed, !truncated, "chr1"))
                    ++failures;
            }
        for (size_t si=0; si<sizeof(sizes)/sizeof(sizes[0]); ++si)
            for (size_t vi=0; vi<sizeof(seeds)/sizeof(seeds[0]); ++vi)
            {
                const size_t samples = sizes[si];
                const size_t bytes = samples*(big+1);
                const int seed = seeds[vi];
                for (unsigned int suffix=0; suffix<2; ++suffix)
                {
                    ostringstream name;
                    name << "complete_" << big << '_' << samples << '_' << seed << '_' << suffix;
                    const string chrom = vi == 0 ? "" : vi == 1 ? string("chr\0X", 5) : vi == 2 ? string(5003, 'A') : "chr22";
                    if (!compare(directory, name.str(), big != 0, samples, bytes, seed, suffix != 0, chrom))
                        ++failures;
                }
                for (size_t ci=0; ci<=sizeof(cuts)/sizeof(cuts[0]); ++ci)
                {
                    const size_t available = ci == sizeof(cuts)/sizeof(cuts[0]) ? (bytes ? bytes-1 : 0) : cuts[ci];
                    if (available >= bytes || (!big && available == 0)) continue;
                    ostringstream name;
                    name << "truncated_" << big << '_' << samples << '_' << available << '_' << seed << '_' << ci;
                    if (!compare(directory, name.str(), big != 0, samples, available, seed, false, "chr22"))
                        ++failures;
                }
            }
    }
    return failures ? 1 : 0;
}
'''


def extract_block(text, marker):
    start = text.index(marker)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
        end += 1
    return text[start:end]


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    args.out_dir = args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    candidate = args.source.resolve() / 'src/cpp/variant_file.cpp'
    baseline = args.baseline.resolve() / 'src/cpp/variant_file.cpp'
    candidate_text = candidate.read_text()
    baseline_text = baseline.read_text()
    header = (args.source.resolve() / 'src/cpp/variant_file.h').read_text()
    genotype_type = next(line for line in header.splitlines() if line.startswith('typedef ') and line.endswith(' ld_genotype;'))
    helper = extract_block(candidate_text, 'class ld_temp_byte_reader') + ';'
    definitions = ['namespace {\n' + helper + '\n}']
    for method in ('read_temp_site_header', 'read_big_temp_site_header',
                   'read_temp_site_payload', 'read_big_temp_site_payload', 'discard_temp_site_payload'):
        marker = 'void variant_file::' + method + '('
        if marker in candidate_text:
            definitions.append(extract_block(candidate_text, marker))
    for method in ('read_temp_site', 'read_big_temp_site'):
        marker = 'void variant_file::' + method + '('
        definitions.append(extract_block(candidate_text, marker))
        definitions.append(extract_block(baseline_text, marker).replace('variant_file::', 'baseline_variant_file::'))
    cpp = args.out_dir / 'ld_readers.cpp'
    cpp.write_text(HARNESS.replace('@DEFINITIONS@', '\n\n'.join(definitions)).replace('@GENOTYPE_TYPE@', genotype_type))
    modes = []
    for char_mode in ('signed', 'unsigned'):
        binary = args.out_dir / ('ld_readers_' + char_mode)
        flags = ['-std=c++98', '-O2', '-f' + char_mode + '-char']
        command = [args.cxx, *flags, str(cpp), '-o', str(binary)]
        build = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (args.out_dir / ('build-' + char_mode + '.log')).write_text(build.stdout + build.stderr)
        if build.returncode:
            print(build.stderr, file=sys.stderr)
            return build.returncode
        mode_dir = args.out_dir / char_mode
        mode_dir.mkdir()
        proc = subprocess.run([str(binary), str(mode_dir)], capture_output=True, text=True, timeout=60)
        (args.out_dir / ('cases-' + char_mode + '.tsv')).write_text(proc.stdout)
        (args.out_dir / ('stderr-' + char_mode)).write_text(proc.stderr)
        keys = ('name', 'equal', 'baseline_state', 'candidate_state', 'baseline_gcount',
                'candidate_gcount', 'baseline_position', 'candidate_position',
                'baseline_remaining', 'candidate_remaining')
        results = []
        for line in proc.stdout.splitlines():
            values = line.split('\t')
            if len(values) != 10:
                raise RuntimeError('Unexpected probe output: ' + line)
            results.append(dict(zip(keys, [values[0], bool(int(values[1])), *map(int, values[2:])])))
        modes.append({'char_mode': char_mode, 'cases': len(results),
                      'passed': sum(item['equal'] for item in results),
                      'all_passed': bool(results) and proc.returncode == 0 and all(item['equal'] for item in results),
                      'return_code': proc.returncode, 'flags': flags,
                      'probe_sha256': fingerprint(binary),
                      'failures': [item for item in results if not item['equal']]})
        (mode_dir / 'input.bin').unlink(missing_ok=True)
    report = {'cases': sum(mode['cases'] for mode in modes),
              'passed': sum(mode['passed'] for mode in modes),
              'all_passed': all(mode['all_passed'] for mode in modes),
              'candidate_source_sha256': fingerprint(candidate),
              'baseline_source_sha256': fingerprint(baseline),
              'extracted_definitions_sha256': hashlib.sha256('\n\n'.join(definitions).encode()).hexdigest(),
              'compiler': subprocess.check_output([args.cxx, '--version'], text=True),
              'contract': 'Exact CHROM, POS, allele count, genotype order and values, final rdstate/gcount/position and remaining raw bytes on binary ifstreams.',
              'limitations': ['Not a CLI regression or performance benchmark.',
                              'Headers are complete; malformed header behavior is unchanged and not tested.',
                              'Packed rows with zero available genotype bytes and nonzero samples are excluded because the baseline reads an uninitialized char.',
                              'Default stream exception mask; arbitrary OS I/O errors and exception-enabled streams are not modeled.'],
              'modes': modes}
    (args.out_dir / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
