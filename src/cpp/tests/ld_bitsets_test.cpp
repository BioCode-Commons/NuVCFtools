#include "../ld_bitsets.h"

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <unistd.h>

static void require(bool condition)
{
	if (!condition) throw std::runtime_error("LD bitset test failed");
}

static ld_moments scalar(const std::vector<unsigned char> &a,
	const std::vector<unsigned char> &b, bool haplotypes)
{
	ld_moments out;
	for (size_t i = 0; i < a.size(); ++i)
	{
		int x[2] = {(a[i] >> 4) & 3, a[i] & 3};
		int y[2] = {(b[i] >> 4) & 3, b[i] & 3};
		if (haplotypes)
		{
			for (int j = 0; j < 2; ++j)
			{
				if (x[j] == 2 || y[j] == 2) continue;
				const int sx = x[j] == 0, sy = y[j] == 0;
				++out.n;
				out.x += sx; out.y += sy;
				out.xx += sx * sx; out.yy += sy * sy; out.xy += sx * sy;
			}
		}
		else
		{
			if (x[0] == 2 || x[1] == 2 || y[0] == 2 || y[1] == 2) continue;
			const int sx = x[0] != x[1] ? 1 : (x[0] == 0 ? 2 : 0);
			const int sy = y[0] != y[1] ? 1 : (y[0] == 0 ? 2 : 0);
			++out.n;
			out.x += sx; out.y += sy;
			out.xx += sx * sx; out.yy += sy * sy; out.xy += sx * sy;
		}
	}
	return out;
}

static void same(const ld_moments &a, const ld_moments &b)
{
	require(a.n == b.n && a.x == b.x && a.y == b.y && a.xx == b.xx && a.yy == b.yy && a.xy == b.xy);
}

static void same(const ld_bitsets &a, const ld_bitsets &b)
{
	require(a.valid == b.valid && a.reference == b.reference && a.heterozygous == b.heterozygous);
}

static uint32_t next_random(uint32_t &state)
{
	state ^= state << 13; state ^= state >> 17; state ^= state << 5;
	return state;
}

static void test_counts()
{
	ld_bitsets a, b;
	// Exhaust every byte pair, including unused high nibble bits and missing
	// alleles. The scalar oracle follows the previous temporary-byte decoder.
	for (unsigned int x = 0; x < 256; ++x)
		for (unsigned int y = 0; y < 256; ++y)
			for (int mode = 0; mode < 2; ++mode)
			{
				std::vector<unsigned char> av(1, x), bv(1, y);
				a.decode(av, mode); b.decode(bv, mode);
				same(scalar(av, bv, mode), mode ? count_ld_haplotypes(a,b) : count_ld_genotypes(a,b));
			}
	const size_t lengths[] = {0, 1, 2, 31, 32, 33, 63, 64, 65, 127, 128, 129, 2504};
	uint32_t random = 193273;
	for (size_t n = 0; n < sizeof(lengths)/sizeof(lengths[0]); ++n)
		for (int trial = 0; trial < 40; ++trial)
		{
			std::vector<unsigned char> av(lengths[n]), bv(lengths[n]);
			for (size_t i = 0; i < av.size(); ++i)
			{
				av[i] = next_random(random); bv[i] = next_random(random);
			}
			for (int mode = 0; mode < 2; ++mode)
			{
				a.decode(av, mode); b.decode(bv, mode);
				same(scalar(av,bv,mode), mode ? count_ld_haplotypes(a,b) : count_ld_genotypes(a,b));
			}
		}
}

static void test_reader(size_t samples, bool haplotypes, size_t budget)
{
	char name[] = "/tmp/nuvcf-ld-test-XXXXXX";
	int descriptor = mkstemp(name);
	require(descriptor >= 0);
	close(descriptor);
	std::vector<std::streamoff> offsets;
	std::vector<ld_bitsets> expected;
	std::ofstream output(name, std::ios::binary);
	uint32_t random = 541;
	const std::string chrom[] = {"chr2", "chr1", "chr1", std::string(180, 'X')};
	for (int row = 0; row < 37; ++row)
	{
		offsets.push_back(output.tellp());
		output << chrom[row % 4] << '\n';
		const int position = row % 5;
		output.write(reinterpret_cast<const char *>(&position), sizeof(position));
		std::vector<unsigned char> bytes(samples);
		for (size_t i = 0; i < samples; ++i) bytes[i] = next_random(random);
		if (samples) output.write(reinterpret_cast<const char *>(&bytes[0]), samples);
		ld_bitsets bits; bits.decode(bytes, haplotypes); expected.push_back(bits);
	}
	offsets.push_back(output.tellp());
	output.close();
	std::ifstream input(name, std::ios::binary);
	ld_site_reader reader(input, samples, haplotypes, budget);
	// Sequential scans with skipped records, reverse seeks, repeated offsets,
	// eviction, oversized records and a disabled cache must all agree.
	for (int pass = 0; pass < 7; ++pass)
		for (int i = 0; i < 37; ++i)
		{
			const int row = pass % 2 ? 36-i : i;
			reader.seek(offsets[row]);
			std::string c; int pos;
			reader.read_header(c, pos);
			require(c == chrom[row % 4] && pos == row % 5);
			if (pass % 3 == 0 && row % 3 == 0) reader.skip_payload();
			else same(reader.read_payload(), expected[row]);
			require(reader.tell() == offsets[row + 1]);
			require(reader.cached_storage_bytes() <= budget);
		}
	reader.seek(0);
	for (int row = 0; row < 37; ++row)
	{
		std::string c; int pos; ld_bitsets bits;
		reader.read_site(c, pos, bits); same(bits, expected[row]);
	}
	input.close();
	std::remove(name);
}

int main()
{
	test_counts();
	const size_t budgets[] = {0, 1, 512, 4096, 8 * 1024 * 1024};
	const size_t samples[] = {0, 1, 65, 2504};
	for (size_t b = 0; b < sizeof(budgets)/sizeof(budgets[0]); ++b)
		for (size_t n = 0; n < sizeof(samples)/sizeof(samples[0]); ++n)
			for (int mode = 0; mode < 2; ++mode)
				test_reader(samples[n], mode, budgets[b]);
	std::cout << "LD counts and bounded reader tests passed\n";
}
