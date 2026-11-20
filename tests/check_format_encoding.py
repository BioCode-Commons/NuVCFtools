#!/usr/bin/env python3
"""Compare actual FORMAT encoders and raw BGZF record bytes using matching objects.

The driver exhausts small token patterns, including the legacy trailing-token
inheritance of short sample fields. It links real entry objects; it does not
replace numeric encoders or normalize binary output. Explicit build directories
must match their source headers. CLI conversion cases are a separate layer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from check_entry_reset import OBJECTS


DRIVER = r'''
#include "vcf_entry.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
output_log LOG;
unsigned int cases = 0;

void snapshot(vcf_entry &entry, ofstream &encoded, BGZF *bcf, const string &format,
              const vector<string> &values, bool write_bcf = true, bool genotype = false)
{
    string line = "1\t100\tprobe\tA\tC\t60\tPASS\t.\t" + format;
    for (size_t i=0; i<values.size(); ++i) line += "\t" + values[i];
    const vector<char> bytes(line.begin(), line.end());
    entry.reset(bytes);
    entry.parse_basic_entry(true, true, true);
    entry.parse_full_entry();
    if (genotype) entry.parse_genotype_entries(true);
    entry.parse_FORMAT();
    vector<char> binary;
    entry.get_FORMAT_binary(binary);
    const uint32_t size = binary.size();
    encoded.write(reinterpret_cast<const char*>(&size), sizeof(size));
    if (!binary.empty()) encoded.write(&binary[0], binary.size());
    if (write_bcf)
    {
        const set<string> keep;
        entry.print_bcf(bcf, keep, true);
    }
    ++cases;
}

void strings(vector<string> &out, string prefix, int fields, int at)
{
    const string tokens[] = {"", ".", "a"};
    if (at == fields) { out.push_back(prefix); return; }
    for (int i=0; i<3; ++i)
        strings(out, prefix + (at ? ":" : "") + tokens[i], fields, at+1);
}

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    ofstream encoded(argv[1], ios::binary);
    BGZF *bcf = bgzf_open(argv[2], "w");
    if (!bcf) return 3;
    header meta;
    unsigned int index = 0;
    meta.parse_meta("##fileformat=VCFv4.2", index);
    meta.parse_meta("##contig=<ID=1,length=1000000>", index);
    meta.parse_meta("##FILTER=<ID=PASS,Description=\"Passed\">", index);
    const char *names[] = {"X", "Y", "Z", "GT", "I", "F", "C"};
    const char *types[] = {"String", "String", "String", "String", "Integer", "Float", "Character"};
    for (int i=0; i<7; ++i)
        meta.parse_meta(string("##FORMAT=<ID=")+names[i]+",Number=.,Type="+types[i]+",Description=\"Probe\">", index);
    meta.parse_header("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\tS3");
    vector<bool> include(3, true);
    vcf_entry entry(meta, include);
    const string formats[] = {"X", "X:Y", "X:Y:Z"};
    for (int fields=1; fields<=3; ++fields)
    {
        vector<string> choices;
        for (int n=1; n<=fields; ++n) strings(choices, "", n, 0);
        vector<string> values(3);
        for (size_t a=0; a<choices.size(); ++a)
            for (size_t b=0; b<choices.size(); ++b)
                for (size_t c=0; c<choices.size(); ++c)
                {
                    values[0]=choices[a]; values[1]=choices[b]; values[2]=choices[c];
                    snapshot(entry, encoded, bcf, formats[fields-1], values);
                }
    }
    const string schemas[] = {"Z:X:Y", "X:X:Y", "UNKNOWN:X:Y", "X:UNKNOWN:Y", "X:Y:UNKNOWN"};
    const string patterns[] = {"", ".", "left", "left:", ":right", "a:b:c", "a::c", ":.:"};
    for (int schema=0; schema<5; ++schema)
        for (int a=0; a<8; ++a)
            for (int b=0; b<8; ++b)
            {
                vector<string> values(3);
                values[0]=patterns[a]; values[1]=patterns[b]; values[2]=patterns[(a+b)%8];
                // Unknown middle/first FORMAT metadata indexing is a separate
                // baseline issue; compare actual FORMAT bytes without rendering.
                snapshot(entry, encoded, bcf, schemas[schema], values, schema<2 || schema==4);
            }
    vector<string> values(3);
    values[0]="0/1:126,-126:1.25,.:a:long";
    values[1]="1|0:127,-127:1e-30,1e30:b:";
    values[2]=".:32767,-32767:0,-0:c";
    snapshot(entry, encoded, bcf, "GT:I:F:C:X", values, true, true);
    values[0]="1:32766,-32766:.:x:tail";
    values[1]="0/.:32768,-32768:inf,-inf:y";
    values[2]="./1:2147483647,-2147483647:nan,2:z:";
    snapshot(entry, encoded, bcf, "GT:I:F:C:X", values, true, true);
    values[0]=string(65537, 'a')+":tail:x";
    values[1]="short";
    values[2]=".:.:";
    snapshot(entry, encoded, bcf, "X:Y:Z", values);
    values[0]="first:second:third"; values[1]=""; values[2]="end";
    snapshot(entry, encoded, bcf, "X:Y:Z", values);
    encoded.close();
    bgzf_close(bcf);
    cout << "CASES\t" << cases << '\n';
    return 0;
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-source', 'baseline-objects', 'candidate-source', 'candidate-objects', 'out-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--fallback-threshold', type=int,
                        help='Test variant only: compile candidate vcf_entry.cpp with a smaller split-offset limit; production source is untouched')
    args = parser.parse_args()
    if args.fallback_threshold is not None and args.fallback_threshold < 0:
        parser.error('--fallback-threshold must be nonnegative')
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    driver = output / 'format_encoding.cpp'
    driver.write_text(DRIVER)
    reports = {}
    for variant in ('baseline', 'candidate'):
        source = getattr(args, variant + '_source').resolve()
        build = getattr(args, variant + '_objects').resolve()
        executable = output / ('format_encoding_' + variant)
        objects = [build / (name + '.o') for name in OBJECTS]
        test_source = None
        if variant == 'candidate' and args.fallback_threshold is not None:
            # Change only the boundary constant, so the fallback body and the
            # production decision logic are exactly the code being exercised.
            original_source = (source / 'src/cpp/vcf_entry.cpp').read_text()
            guard = 'const string::size_type split_offset_limit = (string::size_type)numeric_limits<int>::max();'
            replacement = 'const string::size_type split_offset_limit = (string::size_type)%d;' % args.fallback_threshold
            if original_source.count(guard) != 1:
                raise ValueError('Cannot uniquely locate the production fallback threshold')
            test_source = output / 'vcf_entry_test_threshold.cpp'
            test_source.write_text(original_source.replace(guard, replacement))
            test_object = output / 'vcf_entry_test_threshold.o'
            version = (source / '.tarball-version').read_text().strip()
            compile_command = [args.cxx, '-std=c++98', '-O2', '-DPACKAGE_VERSION="' + version + '"',
                               '-I', str(source / 'src/cpp'), '-c', str(test_source), '-o', str(test_object)]
            compiled_source = subprocess.run(compile_command, capture_output=True, timeout=90)
            (output / 'candidate-threshold.build.log').write_bytes(compiled_source.stdout + compiled_source.stderr)
            if compiled_source.returncode:
                raise RuntimeError(compiled_source.stderr.decode())
            objects[OBJECTS.index('vcf_entry')] = test_object
        command = [args.cxx, '-std=c++98', '-O2', '-DPACKAGE_VERSION="format-probe"',
                   '-I', str(source / 'src/cpp'), str(driver), *map(str, objects),
                   '-lz', '-lm', '-lpthread', '-o', str(executable)]
        compiled = subprocess.run(command, capture_output=True, timeout=90)
        (output / (variant + '.build.log')).write_bytes(compiled.stdout + compiled.stderr)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr.decode())
        run = subprocess.run([str(executable), str(output / (variant + '.format.bin')),
                              str(output / (variant + '.records.bgzf'))], capture_output=True, timeout=120)
        (output / (variant + '.stdout')).write_bytes(run.stdout)
        (output / (variant + '.stderr')).write_bytes(run.stderr)
        reports[variant] = {'exit': run.returncode,
                            'stdout': run.stdout.decode(),
                            'source_sha256': digest(source / 'src/cpp/vcf_entry.cpp'),
                            'test_variant_source_sha256': digest(test_source) if test_source else None,
                            'object_sha256': {p.name: digest(p) for p in objects},
                            'executable_sha256': digest(executable)}
    files = {}
    for suffix in ('stdout', 'stderr', 'format.bin', 'records.bgzf'):
        a = output / ('baseline.' + suffix)
        b = output / ('candidate.' + suffix)
        files[suffix] = {'equal': a.read_bytes() == b.read_bytes(),
                         'bytes': a.stat().st_size, 'baseline_sha256': digest(a), 'candidate_sha256': digest(b)}
    passed = all(item['equal'] for item in files.values()) and all(r['exit'] == 0 for r in reports.values())
    summary = {'all_passed': passed, 'cases': int(reports['baseline']['stdout'].split()[1]),
               'files': files, 'runs': reports,
               'test_variant_fallback_threshold': args.fallback_threshold,
               'scope': 'Actual linked parse_FORMAT and print_bcf, exhaustive small token patterns plus duplicate/unknown/reordered tags, mixed numeric widths and long fields. Raw FORMAT bytes and compressed BGZF records are compared.',
               'limitations': ['Not a whole CLI test; records.bgzf contains encoded records without a BCF file header.',
                               'Overfull sample fields are excluded: original format_matrix indexes past its row size.',
                               'Unknown middle/first fields exercise parse_FORMAT only because print_bcf has separate legacy indexing assumptions.',
                               'When --fallback-threshold is given, only that constant is lowered in a separate compiled source copy; this exercises the production fallback body without allocating a 2-GiB string. It does not execute the actual INT_MAX-sized input.',
                               'Explicit object directories must match the supplied headers.']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'all_passed': passed, 'cases': summary['cases'], 'output': str(output)}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
