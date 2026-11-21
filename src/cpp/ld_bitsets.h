#ifndef LD_BITSETS_H_
#define LD_BITSETS_H_

#include <stdint.h>
#include <cstddef>
#include <fstream>
#include <list>
#include <map>
#include <string>
#include <vector>

// A lane is one chromosome for haplotype LD, or one diploid sample for
// genotype LD. Padding lanes remain zero in every plane.
struct ld_bitsets
{
	std::vector<uint64_t> valid;
	std::vector<uint64_t> reference;
	std::vector<uint64_t> heterozygous;

	void decode(const std::vector<unsigned char> &bytes, bool haplotypes);
	size_t storage_bytes() const;
};

struct ld_moments
{
	uint64_t n, x, y, xx, yy, xy;
	ld_moments() : n(0), x(0), y(0), xx(0), yy(0), xy(0) {}
};

ld_moments count_ld_haplotypes(const ld_bitsets &a, const ld_bitsets &b);
ld_moments count_ld_genotypes(const ld_bitsets &a, const ld_bitsets &b);

// Reads the existing one-byte-per-sample temporary format. Offsets are logical:
// a cache hit need not move the underlying stream. Each reader owns its cache,
// so equal offsets in two files cannot alias. No input sorting is performed.
class ld_site_reader
{
public:
	ld_site_reader(std::ifstream &input, size_t samples, bool haplotypes,
		size_t cache_bytes = 8 * 1024 * 1024);
	void seek(std::streamoff offset);
	std::streamoff tell() const;
	void read_header(std::string &chromosome, int &position);
	const ld_bitsets &read_payload();
	void skip_payload();
	void read_site(std::string &chromosome, int &position, ld_bitsets &result);
	size_t cached_storage_bytes() const;

private:
	struct cached_site
	{
		std::string chromosome;
		int position;
		std::streamoff payload_offset;
		ld_bitsets bits;
		std::list<std::streamoff>::iterator recency;
		size_t storage_bytes() const;
	};
	typedef std::map<std::streamoff, cached_site> site_map;
	std::ifstream &input;
	const size_t samples;
	const bool haplotypes;
	const size_t budget;
	size_t used;
	std::streamoff cursor, current_offset, payload_offset;
	std::string chromosome;
	int position;
	std::vector<unsigned char> bytes;
	ld_bitsets uncached;
	site_map sites;
	std::list<std::streamoff> recency;
	void touch(site_map::iterator site);
	ld_site_reader(const ld_site_reader &);
	ld_site_reader &operator=(const ld_site_reader &);
};

#endif
