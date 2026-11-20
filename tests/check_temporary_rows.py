#!/usr/bin/env python3
"""Probe the actual bounded row copier against getline plus string insertion.

The helper is extracted from the candidate source, not reimplemented. This is
a stream-contract check, not a CLI or performance benchmark. It checks raw
bytes, consumed input, stream state and flush counts, including injected read
errors with the default no-exception stream mask used by the converters.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HARNESS = r'''
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;

@HELPER@

class InputBuffer : public streambuf
{
    string bytes;
    size_t offset;
    size_t fail_at;
    bool fault_enabled;
public:
    InputBuffer(const string &text, size_t fail_position)
        : bytes(text), offset(0), fail_at(fail_position), fault_enabled(true) {}
    size_t position() const { return offset; }
    void disable_fault() { fault_enabled = false; }
protected:
    int_type underflow()
    {
        if (fault_enabled && offset == fail_at)
            throw runtime_error("injected read failure");
        if (offset == bytes.size())
            return traits_type::eof();
        return traits_type::to_int_type(bytes[offset]);
    }
    int_type uflow()
    {
        const int_type next = underflow();
        if (!traits_type::eq_int_type(next, traits_type::eof()))
            ++offset;
        return next;
    }
};

class OutputBuffer : public stringbuf
{
public:
    unsigned int flushes;
    OutputBuffer() : flushes(0) {}
    int sync() { ++flushes; return stringbuf::sync(); }
};

struct Result
{
    string bytes;
    string remaining;
    size_t consumed;
    int state;
    unsigned int flushes;
    bool threw;
};

Result run(const string &bytes, size_t fail_at, bool candidate, bool header)
{
    InputBuffer input_buffer(bytes, fail_at);
    istream fault_input(&input_buffer);
    istringstream buffered_input(bytes);
    const bool inject_fault = fail_at != static_cast<size_t>(-1);
    istream &input = inject_fault ? fault_input : buffered_input;
    OutputBuffer output_buffer;
    ostream output(&output_buffer);
    Result result;
    result.threw = false;
    try
    {
        if (candidate)
        {
            if (header)
                output << ">S1-0" << endl;
            copy_temporary_row(input, output);
            output << endl;
        }
        else
        {
            string row;
            getline(input, row);
            if (header)
                output << ">S1-0" << endl;
            output << row << endl;
        }
        output << "suffix";
    }
    catch (...)
    {
        result.threw = true;
    }
    result.bytes = output_buffer.str();
    result.state = input.rdstate();
    result.consumed = input_buffer.position();
    result.flushes = output_buffer.flushes;
    input_buffer.disable_fault();
    input.clear();
    result.remaining.assign(istreambuf_iterator<char>(input), istreambuf_iterator<char>());
    if (!inject_fault)
        result.consumed = bytes.size() - result.remaining.size();
    return result;
}

string payload(size_t length, bool binary)
{
    string result(length, 'A');
    for (size_t i=0; i<length; ++i)
        result[i] = binary && i%31 == 0 ? '\0' : static_cast<char>('A' + i%26);
    return result;
}

void save(const string &path, const string &value)
{
    ofstream output(path.c_str(), ios::out | ios::binary);
    output.write(value.data(), value.size());
}

bool compare(const string &name, const string &bytes, size_t fail_at,
             bool header, unsigned int index, const string &directory)
{
    const Result baseline = run(bytes, fail_at, false, header);
    const Result candidate = run(bytes, fail_at, true, header);
    const bool equal = baseline.bytes == candidate.bytes &&
        baseline.remaining == candidate.remaining && baseline.consumed == candidate.consumed &&
        baseline.state == candidate.state && baseline.flushes == candidate.flushes &&
        baseline.threw == candidate.threw;
    cout << name << '\t' << equal << '\t' << baseline.state << '\t' << candidate.state
         << '\t' << baseline.consumed << '\t' << candidate.consumed
         << '\t' << baseline.bytes.size() << '\t' << candidate.bytes.size()
         << '\t' << baseline.flushes << '\t' << candidate.flushes << '\n';
    if (!equal)
    {
        ostringstream prefix;
        prefix << directory << "/failure-" << index;
        save(prefix.str() + "-baseline.bin", baseline.bytes);
        save(prefix.str() + "-candidate.bin", candidate.bytes);
        save(prefix.str() + "-baseline-remaining.bin", baseline.remaining);
        save(prefix.str() + "-candidate-remaining.bin", candidate.remaining);
    }
    return equal;
}

int main(int argc, char **argv)
{
    if (argc != 2)
        return 2;
    const string directory = argv[1];
    const size_t no_fault = static_cast<size_t>(-1);
    const size_t lengths[] = {0, 1, 2, 8190, 8191, 8192, 16382, 16383, 16384, 1048577};
    unsigned int count = 0, failures = 0;
    for (unsigned int li=0; li<sizeof(lengths)/sizeof(lengths[0]); ++li)
        for (unsigned int binary=0; binary<2; ++binary)
            for (unsigned int ending=0; ending<4; ++ending)
                for (unsigned int header=0; header<2; ++header)
                {
                    string bytes = payload(lengths[li], binary != 0);
                    if (ending == 1) bytes += '\n';
                    else if (ending == 2) bytes += "\r\n";
                    else if (ending == 3) bytes += string("\nsecond\0line\nthird", 18);
                    ostringstream name;
                    name << "length_" << lengths[li] << "_binary_" << binary
                         << "_ending_" << ending << "_header_" << header;
                    if (!compare(name.str(), bytes, no_fault, header != 0, count++, directory))
                        ++failures;
                }
    const size_t fault_positions[] = {0, 1, 8190, 8191, 8192, 16382, 16383, 20000, 20001, 20002};
    for (unsigned int fi=0; fi<sizeof(fault_positions)/sizeof(fault_positions[0]); ++fi)
        for (unsigned int header=0; header<2; ++header)
        {
            const string bytes = payload(20000, true) + "\nremaining";
            ostringstream name;
            name << "read_failure_" << fault_positions[fi] << "_header_" << header;
            if (!compare(name.str(), bytes, fault_positions[fi], header != 0, count++, directory))
                ++failures;
        }
    return failures ? 1 : 0;
}
'''


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.out_dir = args.out_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    source = args.source / 'src/cpp/variant_file_format_convert.cpp'
    text = source.read_text()
    start = text.index('void copy_temporary_row(')
    end = text.index('\n}\n', start) + len('\n}')
    helper = text[start:end]
    cpp = args.out_dir / 'temporary_rows.cpp'
    cpp.write_text(HARNESS.replace('@HELPER@', helper))
    binary = args.out_dir / 'temporary_rows'
    command = [args.cxx, '-std=c++98', '-O2', str(cpp), '-o', str(binary)]
    build = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (args.out_dir / 'build.log').write_text(build.stdout + build.stderr)
    if build.returncode:
        print(build.stderr, file=sys.stderr)
        return build.returncode
    proc = subprocess.run([str(binary), str(args.out_dir)], capture_output=True, text=True, timeout=30)
    (args.out_dir / 'cases.tsv').write_text(proc.stdout)
    (args.out_dir / 'stderr').write_text(proc.stderr)
    results = []
    keys = ('name', 'equal', 'baseline_state', 'candidate_state',
            'baseline_consumed', 'candidate_consumed', 'baseline_bytes',
            'candidate_bytes', 'baseline_flushes', 'candidate_flushes')
    for line in proc.stdout.splitlines():
        values = line.split('\t')
        if len(values) != 10:
            raise RuntimeError('Unexpected probe output: ' + line)
        results.append(dict(zip(keys, [values[0], bool(int(values[1])), *map(int, values[2:])])))
    report = {'cases': len(results), 'passed': sum(item['equal'] for item in results),
              'all_passed': proc.returncode == 0 and all(item['equal'] for item in results),
              'return_code': proc.returncode, 'source_sha256': fingerprint(source),
              'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(),
              'probe_sha256': fingerprint(binary),
              'compiler': subprocess.check_output([args.cxx, '--version'], text=True),
              'flags': ['-std=c++98', '-O2'],
              'contract': 'Raw output bytes, remaining input bytes, consumed bytes, input state and flush counts; default stream exception mask.',
              'limitations': ['Stream-contract probe only; CLI regression and performance are separate.',
                              'Read failures are injected through streambuf::underflow; arbitrary OS failure timing is not modeled.'],
              'failures': [item for item in results if not item['equal']], 'results': results}
    (args.out_dir / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('results', 'compiler')}, indent=2))
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
