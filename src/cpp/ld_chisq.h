#ifndef LD_CHISQ_H_
#define LD_CHISQ_H_

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdint.h>
#include <utility>
#include <vector>
#include "gamma.h"

namespace ld_chisq_detail {
using std::min;
using std::numeric_limits;
using std::pair;
inline int genotype_pair_index(const pair<int, int> &genotype, int n_alleles)
{
	// The former map lookup returned zero for alleles outside its keys.
	if (genotype.first < 0 || genotype.second < 0 ||
		genotype.first >= n_alleles || genotype.second >= n_alleles)
		return 0;

	const int64_t a = min(genotype.first, genotype.second);
	const int64_t b = max(genotype.first, genotype.second);
	// Count the rows preceding (a,b) in the original upper-triangle order.
	// Widen before multiplication so calculating the index cannot overflow int.
	const int64_t index = a * n_alleles - a * (a + 1) / 2 + b;
	if (index > numeric_limits<int>::max())
		return 0;
	return (int)index;
}

}

// One workspace per caller. No input, output, logging or shared mutable state.
// Storage is reused across pairs; accumulation order follows the serial kernel.
class ld_chisq_workspace
{
public:
    void calculate(const std::vector<std::pair<short, short> > &GT1,
        const std::vector<std::pair<short, short> > &GT2, int N0, int N1,
        double &chisq, double &dof, double &pval, int &indv_count)
{
	int N_genotypes0 = N0 * (N0+1) / 2;
	int N_genotypes1 = N1 * (N1+1) / 2;

	observed.assign(static_cast<size_t>(N_genotypes0) * N_genotypes1, 0);
	indv_count = 0;
	std::pair<int, int> geno1, geno2;
	for (unsigned int ui=0; ui<GT1.size(); ui++)
	{
		geno1 = GT1[ui];
		geno2 = GT2[ui];
		if ((geno1.first < 0) || (geno1.second < 0))
			continue;

		if ((geno2.first < 0) || (geno2.second < 0))
			continue;

		int idx1 = ld_chisq_detail::genotype_pair_index(geno1, N0);
		int idx2 = ld_chisq_detail::genotype_pair_index(geno2, N1);

		observed[static_cast<size_t>(idx1) * N_genotypes1 + idx2]++;
		indv_count++;
	}

	// Retain double storage before use, but only keep the current expected row.
	expected.assign(N_genotypes1, 0);
	row_tot.assign(N_genotypes0, 0);
	col_tot.assign(N_genotypes1, 0);
	double tot=0;
	for (int ui=0; ui<N_genotypes0; ui++)
	{
		for (int uj=0; uj<N_genotypes1; uj++)
		{
			row_tot[ui] += observed[static_cast<size_t>(ui) * N_genotypes1 + uj];
			col_tot[uj] += observed[static_cast<size_t>(ui) * N_genotypes1 + uj];
			tot += observed[static_cast<size_t>(ui) * N_genotypes1 + uj];
		}
	}

	chisq = 0;
	for (int ui=0; ui<N_genotypes0; ui++)
	{
		for (int uj=0; uj<N_genotypes1; uj++)
			expected[uj] = row_tot[ui] * col_tot[uj] / tot;

		for (int uj=0; uj<N_genotypes1; uj++)
		{
			if ((row_tot[ui] > 0) && (col_tot[uj] > 0))	// Don't use incomplete cases
				chisq += std::pow(observed[static_cast<size_t>(ui) * N_genotypes1 + uj] - expected[uj], 2) / expected[uj];
		}
	}
	int n_col=0, n_row=0;
	for (int ui=0; ui<N_genotypes0; ui++)
		if (row_tot[ui] > 0)
			n_row++;
	for (int ui=0; ui<N_genotypes1; ui++)
		if (col_tot[ui] > 0)
			n_col++;

	dof = (n_row-1) * (n_col-1);
	pval = 1.0-gammp(dof/2, chisq/2);
}

private:
    std::vector<double> observed, expected, row_tot, col_tot;
};
#endif
