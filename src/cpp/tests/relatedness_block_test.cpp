#include "../relatedness_block.h"
#include <cassert>
#include <climits>
#include <iostream>
#include <utility>

int main()
{
    typedef std::pair<int,int> call;
    const call genotypes[] = {call(0,0),call(0,1),call(1,1),call(-1,-1),call(-1,1),call(2,2),call(3,3),call(INT_MAX,INT_MAX),call(2,3)};
    const size_t n = sizeof(genotypes)/sizeof(genotypes[0]);
    const size_t lengths[] = {0,1,63,64,65,129};
    for (size_t c=0; c<sizeof(lengths)/sizeof(lengths[0]); ++c)
    {
        relatedness_block block(n);
        std::vector<double> het(n,0);
        std::vector<std::vector<double> > both(n,std::vector<double>(n,0)), opposite(both);
        for (size_t site=0; site<lengths[c]; ++site)
        {
            for (size_t i=0; i<n; ++i)
            {
                call a=genotypes[(i+site)%n];
                block.append(i,a.first,a.second);
                if (a.first<0 || a.second<0) continue;
                if (a.first!=a.second) ++het[i];
                for (size_t j=i; j<n; ++j)
                {
                    call b=genotypes[(j+site)%n];
                    if (b.first<0 || b.second<0) continue;
                    if (a.first!=a.second && b.first!=b.second) ++both[i][j];
                    if (a.first==a.second && b.first==b.second && a.first!=b.first) ++opposite[i][j];
                }
            }
            block.finish_site();
        }
        block.flush();block.flush();
        for (size_t i=0; i<n; ++i)
        {
            assert(het[i]==block.heterozygotes[i]);
            for (size_t j=i; j<n; ++j)
            {
                assert(both[i][j]==block.both_het[i][j-i]);
                assert(opposite[i][j]==block.opposite_hom[i][j-i]);
            }
        }
    }
    relatedness_block precision(1);
    double scalar=std::ldexp(1.0,std::numeric_limits<double>::digits)-2;
    precision.heterozygotes[0]=precision.both_het[0][0]=scalar;
    for (unsigned i=0;i<64;++i) { scalar+=1;precision.append(0,0,1);precision.finish_site(); }
    assert(precision.heterozygotes[0]==scalar && precision.both_het[0][0]==scalar);
    std::cout << "Relatedness block scalar equivalence passed\n";
}
