#!/usr/bin/env python3
"""Compare actual LD reader/decode-skip protocols, including read request traces.

Use the preceding seventh-pass source as baseline. Headers must be complete.
The fixture streams are real binary ifstreams; optional badbit injection happens
at a recorded payload read request, not by replacing decoding with a model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DRIVER = r'''
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
static vector<streamsize> requests;
static size_t fail_request=0;
static void traced_read(ifstream &input, char *buffer, streamsize size)
{
    requests.push_back(size);
    if(fail_request && requests.size()==fail_request) input.setstate(ios::badbit);
    input.read(buffer,size);
}
struct Result
{
    vector<string> chroms;
    vector<int> positions,alleles,genotypes;
    vector<streamsize> reads;
    int state;
    streamsize count;
    streamoff position;
    string remaining;
    bool threw;
    size_t genotype_capacity;
};
'''

DECLARATIONS = r'''
typedef pair<short,short> ld_genotype;
class variant_file
{
public:
    void read_temp_site(ifstream &,string &,int &,vector<ld_genotype> &);
    void read_big_temp_site(ifstream &,string &,int &,int &,vector<ld_genotype> &);
    void read_temp_site_header(ifstream &,string &,int &);
    void read_big_temp_site_header(ifstream &,string &,int &,int &);
    void read_temp_site_payload(ifstream &,vector<ld_genotype> &);
    void read_big_temp_site_payload(ifstream &,vector<ld_genotype> &);
    void discard_temp_site_payload(ifstream &,size_t);
};
'''

RUNNER = r'''
Result run(const string &path,bool big,size_t samples,int records,unsigned int selected,
           int exception_mode,size_t fault)
{
    ifstream input(path.c_str(),ios::in|ios::binary);
    if(exception_mode==1) input.exceptions(ios::badbit);
    if(exception_mode==2) input.exceptions(ios::badbit|ios::failbit|ios::eofbit);
    variant_file reader;
    vector<ld_genotype> genotypes;
    @INITIAL_SIZE@
    Result result;result.threw=false;
    requests.clear();fail_request=fault;
    for(int record=0;record<records;record++)
    {
        string chrom="unchanged";int pos=-12345,alleles=-12345;
        const bool accepted=(selected&(1U<<record))!=0;
        try
        {
            @READ@
        }
        catch(const ios_base::failure &) {result.threw=true;}
        result.chroms.push_back(chrom);result.positions.push_back(pos);result.alleles.push_back(alleles);
        if(accepted && !result.threw)
            for(size_t i=0;i<genotypes.size();i++)
            {result.genotypes.push_back(genotypes[i].first);result.genotypes.push_back(genotypes[i].second);}
        if(result.threw || !input.good()) break;
    }
    result.reads=requests;result.state=input.rdstate();result.count=input.gcount();
    result.genotype_capacity=genotypes.capacity();
    input.exceptions(ios::goodbit);input.clear();result.position=input.tellg();
    result.remaining.assign(istreambuf_iterator<char>(input),istreambuf_iterator<char>());
    return result;
}
'''

MAIN = r'''
static unsigned long cases=0,read_requests=0,skip_only=0,short_cases=0,exception_cases=0;
static bool same(const Result &a,const Result &b)
{
    return a.chroms==b.chroms && a.positions==b.positions && a.alleles==b.alleles
        && a.genotypes==b.genotypes && a.reads==b.reads && a.state==b.state
        && a.count==b.count && a.position==b.position && a.remaining==b.remaining
        && a.threw==b.threw;
}
static void put_record(ofstream &out,bool big,size_t bytes,int seed,const string &chrom,int pos)
{
    out.write(chrom.data(),chrom.size());out.put('\n');out.write((char*)&pos,sizeof(pos));
    if(big){int8_t alleles=(int8_t)(seed%2 ? 127 : -128);out.write((char*)&alleles,1);}
    for(size_t i=0;i<bytes;i++){char value=(char)(i*73+seed*17);out.write(&value,1);}
}
static void check(const string &path,bool big,size_t samples,int records,unsigned int selected,
                  int exception_mode,size_t fault,bool shortened)
{
    Result a=baseline::run(path,big,samples,records,selected,exception_mode,fault);
    Result b=candidate::run(path,big,samples,records,selected,exception_mode,fault);
    if(!same(a,b))
    {
        cerr<<"Mismatch "<<cases<<" big="<<big<<" N="<<samples<<" records="<<records
            <<" selected="<<selected<<" exceptions="<<exception_mode<<" fault="<<fault<<'\n';
        cerr<<a.state<<' '<<b.state<<" count "<<a.count<<' '<<b.count<<" pos "<<a.position<<' '<<b.position<<'\n';
        exit(1);
    }
    if(selected==0 && b.genotype_capacity!=0){cerr<<"Allocated rejected-only genotype vector\n";exit(1);}
    cases++;read_requests+=a.reads.size();skip_only+=(selected==0);short_cases+=shortened;exception_cases+=(exception_mode!=0||fault!=0);
}
int main(int argc,char **argv)
{
    if(argc!=2)return 2;
    const string path=string(argv[1])+"/input.bin";
    const size_t sizes[]={0,1,2,3,15,4095,4096,4097,4098,8193};
    for(int big=0;big<2;big++)for(size_t n=0;n<sizeof(sizes)/sizeof(sizes[0]);n++)
    {
        const size_t samples=sizes[n],wanted=samples*(big?2:1);
        vector<size_t> available;
        available.push_back(0);available.push_back(1);available.push_back(2);
        available.push_back(wanted/2);if(wanted)available.push_back(wanted-1);
        available.push_back(wanted);available.push_back(wanted+5);
        sort(available.begin(),available.end());available.erase(unique(available.begin(),available.end()),available.end());
        for(size_t j=0;j<available.size();j++)for(int seed=0;seed<4;seed++)
        {
            if(!big && samples && available[j]==0)continue; // Old uninitialized packed byte.
            const string chrom=seed==3 ? string(257,'X') : "1";
            {ofstream out(path.c_str(),ios::out|ios::binary);put_record(out,big,available[j],seed,chrom,seed*100-7);}
            for(unsigned selected=0;selected<2;selected++)for(int exceptions=0;exceptions<3;exceptions++)
                check(path,big,samples,1,selected,exceptions,0,available[j]<wanted);
        }
        if(wanted>=2)
        {
            {ofstream out(path.c_str(),ios::out|ios::binary);put_record(out,big,wanted,7,"1",17);}
            const size_t header_reads=3+(big?1:0); // '1', newline, int, optional allele.
            for(unsigned selected=0;selected<2;selected++)for(int exceptions=0;exceptions<3;exceptions++)
                check(path,big,samples,1,selected,exceptions,header_reads+2,false);
        }
    }
    const size_t protocol_sizes[]={0,1,2,17,4097};
    for(int big=0;big<2;big++)for(size_t n=0;n<sizeof(protocol_sizes)/sizeof(protocol_sizes[0]);n++)
        for(int seed=0;seed<3;seed++)
        {
            const size_t samples=protocol_sizes[n];
            {ofstream out(path.c_str(),ios::out|ios::binary);
             for(int record=0;record<5;record++)put_record(out,big,samples*(big?2:1),seed+record,record%2 ? "X" : "1",record*17);}
            for(unsigned selected=0;selected<32;selected++)check(path,big,samples,5,selected,0,0,false);
        }
    cout<<"{\"cases\":"<<cases<<",\"read_requests_compared\":"<<read_requests
        <<",\"skip_only_cases\":"<<skip_only<<",\"short_payload_cases\":"<<short_cases
        <<",\"exception_or_fault_cases\":"<<exception_cases<<",\"passed\":true}\n";
}
'''


def block(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def extract(source, namespace, optimized):
    text = (source / 'src/cpp/variant_file.cpp').read_text()
    parts = [DECLARATIONS, block(text, 'class ld_temp_byte_reader') + ';']
    for method in ['read_temp_site_header', 'read_big_temp_site_header', 'read_temp_site_payload',
                   'read_big_temp_site_payload', 'discard_temp_site_payload', 'read_temp_site', 'read_big_temp_site']:
        marker = 'void variant_file::' + method + '('
        if marker in text: parts.append(block(text, marker))
    code = '\n'.join(parts).replace('input.read(', 'traced_read(input, ').replace('tmp_file.read(', 'traced_read(tmp_file, ')
    if optimized:
        reading = '''if(big)reader.read_big_temp_site_header(input,chrom,pos,alleles);
            else reader.read_temp_site_header(input,chrom,pos);
            if(accepted){genotypes.resize(samples,make_pair(-12345,-23456));
                if(big)reader.read_big_temp_site_payload(input,genotypes);else reader.read_temp_site_payload(input,genotypes);}
            else reader.discard_temp_site_payload(input,samples*(big?2:1));'''
    else:
        reading = '''if(big)reader.read_big_temp_site(input,chrom,pos,alleles,genotypes);
            else reader.read_temp_site(input,chrom,pos,genotypes);'''
    runner = RUNNER.replace('@INITIAL_SIZE@', '' if optimized else 'genotypes.resize(samples,make_pair(-12345,-23456));').replace('@READ@', reading)
    return '\nnamespace ' + namespace + ' {\n' + code + runner + '\n}\n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    directory = args.out_dir.resolve(); directory.mkdir(parents=True, exist_ok=False)
    old = extract(args.baseline.resolve(), 'baseline', False)
    new = extract(args.candidate.resolve(), 'candidate', True)
    driver = directory / 'ld_metadata_probe.cpp'; driver.write_text(DRIVER + old + new + MAIN)
    modes = []
    for name, flags in [('signed-char', ['-fsigned-char']), ('unsigned-char', ['-funsigned-char'])]:
        executable = directory / name
        command = [args.cxx, '-std=c++98', '-O2', *flags, str(driver), '-o', str(executable)]
        built = subprocess.run(command, capture_output=True)
        (directory / (name + '.build.log')).write_bytes(built.stdout + built.stderr); built.check_returncode()
        result = subprocess.run([str(executable), str(directory)], capture_output=True)
        (directory / (name + '.stdout')).write_bytes(result.stdout)
        (directory / (name + '.stderr')).write_bytes(result.stderr); result.check_returncode()
        modes.append({'configuration': name, 'compile_command': command, 'checks': json.loads(result.stdout), 'executable_sha256': digest(executable)})
    (directory / 'input.bin').unlink()
    report = {'all_passed': all(m['checks']['passed'] for m in modes), 'modes': modes,
              'baseline_reader_sha256': digest(args.baseline / 'src/cpp/variant_file.cpp'),
              'candidate_reader_sha256': digest(args.candidate / 'src/cpp/variant_file.cpp'),
              'extracted_candidate_sha256': hashlib.sha256(new.encode()).hexdigest(), 'driver_sha256': digest(driver),
              'scope': 'Actual reader definitions with read-call tracing; metadata, accepted genotype bytes, ifstream::read request lengths/order, final rdstate/gcount/position/remainder and thrown status match. Rejected-only candidate vectors stay unallocated.',
              'limitations': ['Complete headers only; old packed zero-available-payload uninitialized reads excluded.',
                              'Actual EOF and injected badbit at a payload request; not arbitrary physical-device fault injection.',
                              'Default, badbit-only and failbit/eofbit/badbit exception masks checked; a failed record ends the probe before any malformed next header.',
                              'Reader protocol probe, not complete CLI or performance measurement.']}
    (directory / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'all_passed': report['all_passed'], 'modes': [{k: v for k, v in m.items() if k in ['configuration', 'checks']} for m in modes]}))


if __name__ == '__main__':
    main()
