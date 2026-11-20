#!/usr/bin/env python3
"""Compare actual VCF/BCF entry reset and ownership behavior using matching build objects.

Only the C++98 driver is compiled. Each executable links the explicitly supplied
source tree's existing entry objects; do not mix object files from another build.
This is a focused public-API differential probe, not a full build or benchmark.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


OBJECTS = (
    'entry', 'entry_getters', 'entry_setters', 'entry_filters', 'vcf_entry',
    'vcf_entry_setters', 'bcf_entry', 'bcf_entry_setters', 'header', 'parameters',
    'output_log', 'bgzf', 'knetfile',
)

DRIVER = r'''
#include "vcf_entry.h"
#include "bcf_entry.h"
#include <algorithm>
#include <stdint.h>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;

output_log LOG;
unsigned int failures = 0;

void blob(const string &name, const string &value)
{
    const char digits[] = "0123456789abcdef";
    cout << name << '\t' << value.size() << '\t';
    for (size_t i=0; i<value.size(); ++i)
    {
        const unsigned char byte = static_cast<unsigned char>(value[i]);
        cout << digits[byte >> 4] << digits[byte & 15];
    }
    cout << '\n';
}

void snapshot(entry &record, const string &name, const parameters &params, bool empty)
{
    cout << "CASE\t" << name << '\n';
    const int applied = record.apply_filters(params);
    cout << "filter\t" << applied << '\t' << record.passed_filters << '\n';
    if (applied != (empty ? 0 : 1) || record.passed_filters != !empty)
        ++failures;
    if (!record.passed_filters) return;
    record.parse_basic_entry(true, true, true);
    record.parse_full_entry(true);
    record.parse_genotype_entries(true, true, true, true);
    blob("chrom", record.get_CHROM());
    cout << "pos\t" << record.get_POS() << '\n';
    blob("id", record.get_ID());
    blob("ref", record.get_REF());
    blob("alt", record.get_ALT());
    blob("filter", record.get_FILTER());
    cout << "quality\t" << record.get_QUAL() << '\n';
    for (unsigned int i=0; i<record.N_indv; ++i)
    {
        pair<int,int> genotype;
        record.get_indv_GENOTYPE_ids(i, genotype);
        cout << "sample\t" << i << '\t' << genotype.first << '\t' << genotype.second
             << '\t' << record.get_indv_PHASE(i) << '\t' << record.get_indv_ploidy(i)
             << '\t' << record.get_indv_DEPTH(i) << '\t' << record.get_indv_GQUALITY(i) << '\n';
        string filter;
        record.get_indv_GFILTER(i, filter);
        blob("sample_filter", filter);
    }
    ostringstream rendered;
    const set<string> keep_info;
    record.print(rendered, keep_info, true);
    blob("recode", rendered.str());
}

vector<char> bytes(const string &value)
{
    return vector<char>(value.begin(), value.end());
}

template<class T> void append(vector<char> &out, T value)
{
    const char *data = reinterpret_cast<const char*>(&value);
    out.insert(out.end(), data, data + sizeof(value));
}

vector<char> bcf_row(const header &meta, int pos, const string &id, bool missing)
{
    vector<char> shared, individual, row;
    append(shared, static_cast<uint32_t>(0));
    append(shared, static_cast<uint32_t>(pos-1));
    append(shared, static_cast<uint32_t>(1));
    append(shared, static_cast<float>(42.5));
    append(shared, static_cast<uint32_t>(2u << 16));
    append(shared, static_cast<uint32_t>((1u << 24) | 2u));
    shared.push_back(static_cast<char>((id.size() << 4) | 7));
    shared.insert(shared.end(), id.begin(), id.end());
    shared.push_back(0x17); shared.push_back('A');
    shared.push_back(0x17); shared.push_back('G');
    shared.push_back(0x11);
    shared.push_back(static_cast<char>(meta.FILTER_reverse_map.find("PASS")->second));
    individual.push_back(0x11);
    individual.push_back(static_cast<char>(meta.FORMAT_reverse_map.find("GT")->second));
    individual.push_back(0x21);
    individual.push_back(missing ? 0 : 2); individual.push_back(missing ? 0 : 4);
    individual.push_back(5); individual.push_back(5);
    append(row, static_cast<uint32_t>(shared.size()));
    append(row, static_cast<uint32_t>(individual.size()));
    row.insert(row.end(), shared.begin(), shared.end());
    row.insert(row.end(), individual.begin(), individual.end());
    return row;
}

int main()
{
    header meta;
    unsigned int index = 0;
    meta.parse_meta("##fileformat=VCFv4.2", index);
    meta.parse_meta("##contig=<ID=chr1,length=1000000>", index);
    meta.parse_meta("##FILTER=<ID=PASS,Description=\"Passed\">", index);
    meta.parse_meta("##INFO=<ID=TXT,Number=1,Type=String,Description=\"Text\">", index);
    meta.parse_meta("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">", index);
    meta.parse_meta("##FORMAT=<ID=GQ,Number=1,Type=Integer,Description=\"Quality\">", index);
    meta.parse_meta("##FORMAT=<ID=DP,Number=1,Type=Integer,Description=\"Depth\">", index);
    meta.parse_meta("##FORMAT=<ID=FT,Number=1,Type=String,Description=\"Filter\">", index);
    meta.parse_header("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2");
    vector<bool> include(meta.N_indv, true);
    parameters params(0, NULL);
    vcf_entry first(meta, include), second(meta, include);
    const vector<char> empty;
    const string complete = "chr1\t12\tcomplete\tA\tG\t50\tPASS\tTXT=one\tGT:GQ:DP:FT\t0/1:40:12:PASS\t1|1:60:20:PASS";
    const string short_row = "chr1\t30\tshort\tC\tT\t.\tPASS\t.\tGT\t0/0\t./.";
    snapshot(first, "vcf_initial_empty", params, true);
    vector<char> input = bytes(complete);
    first.reset(input);
    fill(input.begin(), input.end(), 'X');
    snapshot(first, "vcf_owned_after_input_mutation", params, false);
    first.reset(empty);
    snapshot(first, "vcf_complete_to_empty", params, true);
    first.reset(bytes(short_row));
    snapshot(first, "vcf_empty_to_complete", params, false);

    first.reset(bytes(complete));
    first.parse_basic_entry(true);
    second.reset(bytes(short_row));
    vcf_entry third(meta, include); // Constructor also clears static convert_line.
    snapshot(first, "vcf_interleaved_first_partial_parse", params, false);
    snapshot(second, "vcf_interleaved_second_unparsed", params, false);
    first.reset(bytes(complete));
    second.reset(empty);
    snapshot(first, "vcf_other_reset_empty", params, false);
    snapshot(second, "vcf_interleaved_empty", params, true);

    string nul_row = "chr1\t40\t";
    nul_row.append("id\0raw", 6);
    nul_row += "\tA\tG\t50\tPASS\tTXT=";
    nul_row.append("before\0after", 12);
    nul_row += "\tGT:GQ:DP:FT\t0/1:40:12:PASS\t1|1:60:20:PASS";
    first.reset(bytes(nul_row));
    snapshot(first, "vcf_embedded_nul", params, false);
    first.reset(bytes(complete + "\r\n"));
    snapshot(first, "vcf_crlf", params, false);
    first.reset(bytes("chr1\t50\ttruncated\tA\tG\t.\tPASS\t.\tGT:DP\t0/1"));
    snapshot(first, "vcf_truncated_sample", params, false);
    first.reset(bytes("chr1\t60\teight_fields\tA\tG\t.\tPASS\t."));
    snapshot(first, "vcf_truncated_format", params, false);
    first.reset(bytes(complete));
    snapshot(first, "vcf_recover_after_failed_getline", params, false);
    const string long_row = "chr1\t70\tlong\tA\tG\t50\tPASS\tTXT=" + string(65537, 'A') + "\tGT\t0/1\t1|1";
    input = bytes(long_row);
    first.reset(input);
    input.clear();
    snapshot(first, "vcf_long_owned_row", params, false);
    first.reset(bytes(short_row));
    snapshot(first, "vcf_long_to_short", params, false);

    bcf_entry binary(meta, include), binary_second(meta, include);
    snapshot(binary, "bcf_initial_empty", params, true);
    input = bcf_row(meta, 101, "first", false);
    binary.reset(input);
    fill(input.begin(), input.end(), '\0');
    binary_second.reset(bcf_row(meta, 202, string("b\0c", 3), true));
    snapshot(binary, "bcf_owned_and_interleaved", params, false);
    snapshot(binary_second, "bcf_second_embedded_nul", params, false);
    binary.reset(empty);
    snapshot(binary, "bcf_complete_to_empty", params, true);
    binary.reset(bcf_row(meta, 303, "last", false));
    snapshot(binary, "bcf_empty_to_complete", params, false);
    cout << "FAILURES\t" << failures << '\n';
    return failures ? 1 : 0;
}
'''


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--baseline-objects', type=Path, required=True)
    parser.add_argument('--candidate-source', type=Path, required=True)
    parser.add_argument('--candidate-objects', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    args.out_dir = args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    driver = args.out_dir / 'entry_reset.cpp'
    driver.write_text(DRIVER)
    runs = {}
    for version in ('baseline', 'candidate'):
        source = getattr(args, version + '_source').resolve()
        object_dir = getattr(args, version + '_objects').resolve()
        objects = [object_dir / (name + '.o') for name in OBJECTS]
        for obj in objects:
            if not obj.is_file():
                raise FileNotFoundError(obj)
        executable = args.out_dir / ('entry_reset_' + version)
        command = [args.cxx, '-std=c++98', '-O2', '-DPACKAGE_VERSION="reset-probe"',
                   '-I', str(source / 'src/cpp'),
                   str(driver), *map(str, objects), '-lz', '-lm', '-lpthread', '-o', str(executable)]
        build = subprocess.run(command, capture_output=True, timeout=60)
        (args.out_dir / ('build-' + version + '.stdout')).write_bytes(build.stdout)
        (args.out_dir / ('build-' + version + '.stderr')).write_bytes(build.stderr)
        if build.returncode:
            sys.stderr.buffer.write(build.stderr)
            return build.returncode
        proc = subprocess.run([str(executable)], capture_output=True, timeout=60)
        (args.out_dir / (version + '.stdout')).write_bytes(proc.stdout)
        (args.out_dir / (version + '.stderr')).write_bytes(proc.stderr)
        runs[version] = {
            'return_code': proc.returncode,
            'cases': [line.decode('ascii') for line in proc.stdout.splitlines() if line.startswith(b'CASE\t')],
            'stdout_sha256': hashlib.sha256(proc.stdout).hexdigest(),
            'stderr_sha256': hashlib.sha256(proc.stderr).hexdigest(),
            'executable_sha256': sha256(executable),
            'object_sha256': {obj.name: sha256(obj) for obj in objects},
            'source_sha256': {name: sha256(source / 'src/cpp' / name)
                              for name in ('entry.h', 'entry_filters.cpp', 'vcf_entry.cpp', 'bcf_entry.cpp')},
            'link_command': command,
        }
    equal_stdout = (args.out_dir / 'baseline.stdout').read_bytes() == (args.out_dir / 'candidate.stdout').read_bytes()
    equal_stderr = (args.out_dir / 'baseline.stderr').read_bytes() == (args.out_dir / 'candidate.stderr').read_bytes()
    passed = (equal_stdout and equal_stderr and all(run['return_code'] == 0 for run in runs.values())
              and len(runs['baseline']['cases']) == 20)
    report = {
        'all_passed': passed, 'cases': len(runs['baseline']['cases']),
        'stdout_byte_identical': equal_stdout, 'stderr_byte_identical': equal_stderr,
        'driver_sha256': sha256(driver), 'runs': runs,
        'scope': 'Actual linked VCF/BCF entry objects; public filtering, parsing, getters and VCF rendering. Initial/empty reset states, owned bytes after caller mutation, interleaved records, NUL, CRLF, truncation and long-to-short rows.',
        'limitations': ['Not a whole CLI regression or performance benchmark.',
                        'Explicit object directories must match their supplied source headers.',
                        'BCF fixture bytes use the native integer layout expected by this implementation.'],
    }
    (args.out_dir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'all_passed': passed, 'cases': report['cases'], 'report': str(args.out_dir / 'report.json')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
