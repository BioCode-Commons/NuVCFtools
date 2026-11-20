#!/usr/bin/env python3
"""Check extracted window-pi helpers against legacy range updates and mask scans.

The counter oracle is the actual previous source loop with local names adapted.
Mask tests exhaust byte decoding and compare real candidate rolling helpers with
independent direct scans. These supplement complete CLI comparisons, not replace
them. All three char signedness configurations compile in C++98.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DRIVER = r'''
#include <algorithm>
#include <climits>
#include <iostream>
#include <vector>
using namespace std;
@ROW@
@HELPERS@

void baseline_add(vector<window_stat_row<unsigned long, 4> > &bins,
    int first, int last, unsigned long comparisons, unsigned int mismatches, bool polymorphic)
{
    const unsigned int N_variant_sites=0, N_variant_site_pairs=1, N_mismatches=2, N_polymorphic_sites=3;
    const window_stat_row<unsigned long,4> empty_vector;
    @BASELINE@
}

unsigned long bin_checks=0, range_operations=0, predicate_checks=0, rolling_checks=0;
unsigned int random_state=7119;
unsigned int next_random() { random_state=random_state*1664525U+1013904223U; return random_state; }
bool check_bins(const vector<window_stat_row<unsigned long,4> > &old_bins,
                const vector<window_stat_row<unsigned long,4> > &new_bins)
{
    if (old_bins.size()!=new_bins.size()) return false;
    window_stat_row<unsigned long,4> totals;
    // Run the prefix twice without modifying differences, as duplicate
    // chromosome output does in the production caller.
    for (unsigned int pass=0;pass<2;pass++)
    {
        totals=window_stat_row<unsigned long,4>();
        for (size_t i=0;i<new_bins.size();i++)
            for (unsigned int column=0;column<4;column++)
            {
                totals[column]+=new_bins[i][column];
                bin_checks++;
                if (totals[column]!=old_bins[i][column]) return false;
            }
    }
    return true;
}

bool apply(vector<window_stat_row<unsigned long,4> > &old_bins,
           vector<window_stat_row<unsigned long,4> > &new_bins,
           int first,int last,unsigned long comparisons,unsigned int mismatches,bool polymorphic)
{
    baseline_add(old_bins,first,last,comparisons,mismatches,polymorphic);
    add_window_pi_range(new_bins,first,last,comparisons,mismatches,polymorphic);
    range_operations++;
    return check_bins(old_bins,new_bins);
}

bool range_tests()
{
    vector<pair<int,int> > operations;
    for (int first=0;first<=4;first++)
        for (int last=first;last<=4;last++) operations.push_back(make_pair(first,last));
    operations.push_back(make_pair(0,-1));
    operations.push_back(make_pair(0,-2));
    operations.push_back(make_pair(-1,-1)); // chromosome revisit
    const unsigned long sums[]={0,1,ULONG_MAX,ULONG_MAX-3,123456789};
    for (unsigned int a=0;a<operations.size();a++)
        for (unsigned int b=0;b<operations.size();b++)
            for (unsigned int c=0;c<operations.size();c++)
                for (unsigned int mode=0;mode<5;mode++)
                {
                    vector<window_stat_row<unsigned long,4> > old_bins(1),new_bins(1);
                    // Seed only bin zero near wrap, including counters that
                    // normal-size CLI fixtures cannot reach cheaply.
                    for (unsigned int column=0;column<4;column++)
                        old_bins[0][column]=new_bins[0][column]=sums[mode];
                    const unsigned int seq[]={a,b,c};
                    for (unsigned int i=0;i<3;i++)
                    {
                        pair<int,int> op=operations[seq[i]];
                        if (op.first==-1)
                        {
                            old_bins.resize(1);new_bins.resize(1);
                            if (!check_bins(old_bins,new_bins)) return false;
                        }
                        else if (!apply(old_bins,new_bins,op.first,op.second,sums[(mode+i)%5],
                                        i%2 ? UINT_MAX : 3U,(i+mode)%2)) return false;
                    }
                }
    vector<vector<window_stat_row<unsigned long,4> > > old_chrs(5),new_chrs(5);
    unsigned int previous=99;
    for (unsigned int i=0;i<50000;i++)
    {
        unsigned int chr=next_random()%5;
        if (chr!=previous)
        {
            old_chrs[chr].resize(1);new_chrs[chr].resize(1);previous=chr;
        }
        int first=next_random()%64,last=static_cast<int>(next_random()%67)-2;
        if (!apply(old_chrs[chr],new_chrs[chr],first,last,
                   sums[next_random()%5],next_random(),next_random()%2)) return false;
    }
    return true;
}

bool reference_keep(char value,int threshold,bool invert)
{
    short digit=value;
    digit-='0';
    vector<char> decoded(1);
    decoded[0]=digit;
    bool keep=decoded[0]<=threshold;
    if (invert) keep=!keep;
    return keep;
}

bool check_range(window_pi_mask_counter &counter,const vector<bool> &mask,
                 unsigned int start,unsigned int end)
{
    unsigned long expected=0;
    for (unsigned int i=start;i<end;i++) if(mask[i]) expected++;
    rolling_checks++;
    return counter.count(mask,start,end)==expected;
}

bool mask_tests()
{
    const int thresholds[]={INT_MIN,-257,-177,-129,-128,-49,-1,0,1,4,9,127,128,255,256,INT_MAX};
    for (unsigned int t=0;t<sizeof(thresholds)/sizeof(thresholds[0]);t++)
        for (unsigned int invert=0;invert<2;invert++)
            for (unsigned int value=0;value<256;value++)
            {
                predicate_checks++;
                if (reference_keep(static_cast<char>(value),thresholds[t],invert)!=
                    window_pi_mask_keep(static_cast<char>(value),thresholds[t],invert)) return false;
            }
    for (unsigned int bits=0;bits<256;bits++)
    {
        vector<bool> mask(8);
        for (unsigned int i=0;i<8;i++) mask[i]=(bits>>i)&1;
        // Every transition between every pair of valid or empty ranges.
        for (unsigned int a=0;a<=8;a++)
            for (unsigned int b=0;b<=8;b++)
                for (unsigned int c=0;c<=8;c++)
                    for (unsigned int d=0;d<=8;d++)
                    {
                        window_pi_mask_counter counter;
                        if (!check_range(counter,mask,a,b)||!check_range(counter,mask,c,d)) return false;
                    }
    }
    vector<bool> mask(257);
    for (unsigned int i=0;i<mask.size();i++) mask[i]=next_random()%3;
    window_pi_mask_counter counter;
    for (unsigned int i=0;i<20000;i++)
    {
        const unsigned int start=next_random()%300;
        const unsigned int end=next_random()%258;
        if (!check_range(counter,mask,start,end)) return false;
    }
    const unsigned int coordinates[]={0,1,2,UINT_MAX,UINT_MAX-1,UINT_MAX/2,UINT_MAX/2+1};
    const unsigned int steps[]={1,2,3,INT_MAX};
    const unsigned int widths[]={1,2,17,INT_MAX};
    for (unsigned int s=0;s<sizeof(coordinates)/sizeof(coordinates[0]);s++)
        for (unsigned int t=0;t<sizeof(steps)/sizeof(steps[0]);t++)
            for (unsigned int w=0;w<sizeof(widths)/sizeof(widths[0]);w++)
            {
                // Same unsigned wrap and length narrowing as the caller;
                // any nonempty interval is bounded by the actual mask.
                unsigned int start=coordinates[s]*steps[t];
                unsigned int end=min(start+widths[w],static_cast<unsigned int>(mask.size()));
                if (!check_range(counter,mask,start,end)) return false;
                if (!check_range(counter,mask,0,17)) return false;
            }
    vector<bool> empty;
    if (!check_range(counter,empty,UINT_MAX,0)||!check_range(counter,empty,0,0)) return false;
    return true;
}

int main()
{
    if (!range_tests()||!mask_tests()) { cerr<<"Mismatch"<<endl;return 1; }
    cout<<"{\"range_operations\":"<<range_operations<<",\"bin_value_comparisons\":"<<bin_checks
        <<",\"mask_predicate_comparisons\":"<<predicate_checks<<",\"rolling_range_comparisons\":"
        <<rolling_checks<<",\"passed\":true}"<<endl;
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True, help='Previous sixth-pass source with original window-pi loops')
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    old_path = args.baseline.resolve() / 'src/cpp/variant_file_output.cpp'
    new_path = args.candidate.resolve() / 'src/cpp/variant_file_output.cpp'
    old, new = old_path.read_text(), new_path.read_text()
    row_start = new.index('template<typename T, unsigned int Width>')
    row = new[row_start:new.index('\n};', row_start) + 3]
    start = new.index('static void add_window_pi_range(')
    helpers = new[start:new.index('\nvoid variant_file::output_windowed_nucleotide_diversity(', start)]
    old_function = old[old.index('void variant_file::output_windowed_nucleotide_diversity('):]
    start = old_function.index('\t\tif(last>= (int)bins[CHROM].size())')
    baseline = old_function[start:old_function.index('\n\t}\n\n\t// Calculate and print', start)]
    baseline = baseline.replace('bins[CHROM]', 'bins').replace('N_comparisons', 'comparisons').replace('N_site_mismatches', 'mismatches').replace('allele_counts[0] < (signed)N_non_missing_chr', 'polymorphic')
    source = args.out_dir.resolve() / 'window_pi_probe.cpp'
    source.write_text(DRIVER.replace('@ROW@', row).replace('@HELPERS@', helpers).replace('@BASELINE@', baseline))
    runs = []
    for name, flags in [('default', []), ('signed-char', ['-fsigned-char']), ('unsigned-char', ['-funsigned-char'])]:
        executable = args.out_dir.resolve() / ('window_pi_probe_' + name)
        command = [args.cxx, '-std=c++98', '-O2', *flags, str(source), '-o', str(executable)]
        build = subprocess.run(command, capture_output=True)
        (args.out_dir / (name + '.build.log')).write_bytes(build.stdout + build.stderr)
        build.check_returncode()
        result = subprocess.run([str(executable)], capture_output=True)
        (args.out_dir / (name + '.stdout')).write_bytes(result.stdout)
        (args.out_dir / (name + '.stderr')).write_bytes(result.stderr)
        result.check_returncode()
        runs.append({'configuration': name, 'compile_command': command, 'checks': json.loads(result.stdout),
                     'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()})
    summary = {'all_passed': all(r['checks']['passed'] for r in runs), 'runs': runs,
               'baseline_source_sha256': hashlib.sha256(old_path.read_bytes()).hexdigest(),
               'candidate_source_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
               'extracted_helpers_sha256': hashlib.sha256(helpers.encode()).hexdigest(),
               'driver_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'scope': 'Actual candidate helpers; previous-source range loop with identifiers adapted; direct mask scans and exact legacy char narrowing as oracle. Each configuration is counted separately.',
               'limitations': ['No full CLI or mask-file parser test; complete CLI corpus covers those separately.',
                               'Bin probes preserve unsigned-long modular arithmetic; existing signed-overflow dimensions and invalid indices are excluded.',
                               'Endpoint wrapping is tested without allocating a multi-GiB mask.']}
    (args.out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'all_passed': summary['all_passed'], 'configurations': len(runs), 'checks_per_configuration': runs[0]['checks']}))


if __name__ == '__main__':
    main()
