/*
 * dgeev.cpp
 *
 *	Created on: 20 Apr 2011
 *			Author: auton
 * ($Revision: 1 $)
 */

#if HAVE_CONFIG_H
# include "config.h"
#endif

#if HAVE_LIBLAPACK

#include "dgeev.h"
#include <algorithm>

namespace
{
struct dgeev_magnitude_order
{
	const double *magnitude;
	dgeev_magnitude_order(const double *values) : magnitude(values) {}
	bool operator()(int left, int right) const
	{
		if (fabs(magnitude[left]) > fabs(magnitude[right])) return true;
		if (fabs(magnitude[left]) < fabs(magnitude[right])) return false;
		return left < right; // Preserve the original order of equal magnitudes.
	}
};

void dgeev_sort_columns(double *Er, double *Ei, double **Evecs, int N)
{
	double *E2 = new double[N];
	int *order = new int[N];
	int i, j;
	for (i=0; i<N; i++)
	{
		E2[i] = Er[i]*Er[i]+Ei[i]*Ei[i];
		order[i] = i;
	}

	// An unordered magnitude never moved in the adjacent-swap implementation.
	// Sort each non-NaN run independently so nothing crosses those barriers.
	for (i=0; i<N; )
	{
		if (E2[i] != E2[i]) { i++; continue; }
		j = i + 1;
		while (j<N && E2[j] == E2[j]) j++;
		std::sort(order+i, order+j, dgeev_magnitude_order(E2));
		i = j;
	}

	// Reuse the magnitude buffer to move each value/column only once.
	for (i=0; i<N; i++) E2[i] = Er[order[i]];
	for (i=0; i<N; i++) Er[i] = E2[i];
	for (i=0; i<N; i++) E2[i] = Ei[order[i]];
	for (i=0; i<N; i++) Ei[i] = E2[i];
	if (Evecs != 0)
		for (i=0; i<N; i++)
		{
			for (j=0; j<N; j++) E2[j] = Evecs[i][order[j]];
			for (j=0; j<N; j++) Evecs[i][j] = E2[j];
		}
	delete [] order;
	delete [] E2;
}
}

void dgeev_sort(double *Er, double *Ei, int N)
{
	dgeev_sort_columns(Er, Ei, 0, N);
}

void dgeev_sort(double *Er, double *Ei, double **Evecs, int N)
{
	dgeev_sort_columns(Er, Ei, Evecs, N);
}


double* dgeev_ctof(double **in, int rows, int cols)
{
	double *out;
	int i, j;

	out = new double[rows*cols];
	for (i=0; i<rows; i++)
		for (j=0; j<cols; j++)
			out[i+j*cols] = in[i][j];
	return(out);
}


void dgeev_ftoc(double *in, double **out, int rows, int cols)
{
	int i, j;

	for (i=0; i<rows; i++)
		for (j=0; j<cols; j++)
			out[i][j] = in[i+j*cols];
}


void dgeev(double **H, int n, double *Er, double *Ei)
{
	char jobvl, jobvr;
	int lda, ldvl, ldvr, lwork, info;
	double *a, *work;
	double vl, vr;

	jobvl = 'N'; // V/N to calculate/not calculate the left eigenvectors of the matrix H.
	jobvr = 'N'; // As above, but for the right eigenvectors.

	lda = n; // The leading dimension of the matrix a.
	a = dgeev_ctof(H, n, lda); // Convert the matrix H from double pointer C form to single pointer Fortran form.

	// LAPACK does not reference VL/VR when their JOB argument is 'N'.
	// Keep the original dimensions and workspace; only replace unused storage.

	ldvl = n;
	ldvr = n;
	work = new double[4*n];
	lwork = 4*n;

	dgeev_(&jobvl, &jobvr, &n, a, &lda, Er, Ei, &vl, &ldvl, &vr, &ldvr, work, &lwork, &info);

	dgeev_sort(Er, Ei, n); //Sort the results by eigenvalue in decreasing magnitude.

	delete [] a;
	delete [] work;
}


void dgeev(double **H, int n, double *Er, double *Ei, double **Evecs)
{
	char jobvl, jobvr;
	int lda,	ldvl, ldvr, lwork, info;
	double *a, *vr, *work;
	double vl;

	jobvl = 'N';
	jobvr = 'V';
	lda = n;
	a = dgeev_ctof(H, n, lda);

	ldvl = n;
	ldvr = n;
	vr = new double[n*n];
	work = new double[4*n];
	lwork = 4*n;

	dgeev_(&jobvl, &jobvr, &n, a, &lda, Er, Ei, &vl, &ldvl, vr, &ldvr, work, &lwork, &info);

	dgeev_ftoc(vr, Evecs, n, ldvr);
	dgeev_sort(Er, Ei, Evecs, n);

	delete [] a;
	delete [] vr;
	delete [] work;
}

#endif
