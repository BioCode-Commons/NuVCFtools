#ifndef RELATEDNESS_BLOCK_H_
#define RELATEDNESS_BLOCK_H_

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdint.h>
#include <vector>

// Transpose one machine word of sites at a time. Homozygous allele IDs are
// bit-sliced, so unequal IDs remain distinguishable without assuming 0 or 1.
// Missing or partially missing calls occupy neither genotype mask.
class relatedness_block
{
public:
    explicit relatedness_block(size_t samples)
        : heterozygotes(samples, 0.0), both_het(samples), opposite_hom(samples),
          het(samples, 0), hom(samples, 0), sites(0), used_planes(0)
    {
        for (size_t i=0; i<samples; ++i)
        {
            both_het[i].assign(samples-i, 0.0);
            opposite_hom[i].assign(samples-i, 0.0);
        }
    }

    void append(size_t sample, int first, int second)
    {
        if (first < 0 || second < 0) return;
        const uint64_t lane = uint64_t(1) << sites;
        if (first != second)
        {
            het[sample] |= lane;
            return;
        }
        hom[sample] |= lane;
        unsigned int allele = static_cast<unsigned int>(first);
        size_t plane = 0;
        while (allele)
        {
            if (plane == allele_bits.size())
                allele_bits.push_back(std::vector<uint64_t>(het.size(), 0));
            if (allele & 1U) allele_bits[plane][sample] |= lane;
            allele >>= 1;
            ++plane;
        }
        used_planes = std::max(used_planes, plane);
    }

    void finish_site()
    {
        if (++sites == std::numeric_limits<uint64_t>::digits) flush();
    }

    void flush()
    {
        if (!sites) return;
        for (size_t i=0; i<het.size(); ++i)
        {
            add_units(heterozygotes[i], population(het[i]));
            for (size_t j=i; j<het.size(); ++j)
            {
                add_units(both_het[i][j-i], population(het[i] & het[j]));
                uint64_t different = 0;
                for (size_t p=0; p<used_planes; ++p)
                    different |= allele_bits[p][i] ^ allele_bits[p][j];
                add_units(opposite_hom[i][j-i], population(hom[i] & hom[j] & different));
            }
        }
        std::fill(het.begin(), het.end(), 0);
        std::fill(hom.begin(), hom.end(), 0);
        for (size_t p=0; p<used_planes; ++p)
            std::fill(allele_bits[p].begin(), allele_bits[p].end(), 0);
        sites = used_planes = 0;
    }

    std::vector<double> heterozygotes;
    std::vector<std::vector<double> > both_het, opposite_hom;

private:
    std::vector<uint64_t> het, hom;
    std::vector<std::vector<uint64_t> > allele_bits;
    size_t sites, used_planes;

    static unsigned int population(uint64_t value)
    {
#if defined(__GNUC__) || defined(__clang__)
        return __builtin_popcountll(value);
#else
        unsigned int count = 0;
        while (value) { value &= value-1; ++count; }
        return count;
#endif
    }

    static void add_units(double &counter, unsigned int amount)
    {
        // Match repeated double += 1 even beyond exact integer precision: the
        // original counters stop increasing at this representable value.
        const double limit = std::ldexp(1.0, std::numeric_limits<double>::digits);
        counter = std::min(limit, counter + amount);
    }
};
#endif
