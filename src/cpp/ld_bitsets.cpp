#include "ld_bitsets.h"

#include <limits>
#include <stdexcept>

namespace
{
inline unsigned int population_count(uint64_t word)
{
#if defined(__GNUC__) || defined(__clang__)
	return __builtin_popcountll(word);
#else
	word -= (word >> 1) & UINT64_C(0x5555555555555555);
	word = (word & UINT64_C(0x3333333333333333)) + ((word >> 2) & UINT64_C(0x3333333333333333));
	word = (word + (word >> 4)) & UINT64_C(0x0f0f0f0f0f0f0f0f);
	return (word * UINT64_C(0x0101010101010101)) >> 56;
#endif
}
}

void ld_bitsets::decode(const std::vector<unsigned char> &bytes, bool haplotypes)
{
	if (haplotypes && bytes.size() > std::numeric_limits<size_t>::max() / 2)
		throw std::length_error("LD haplotype count is too large");
	const size_t lanes = bytes.size() * (haplotypes ? 2 : 1);
	const size_t words = lanes / 64 + (lanes % 64 != 0);
	valid.assign(words, 0);
	reference.assign(words, 0);
	heterozygous.assign(haplotypes ? 0 : words, 0);
	for (size_t i = 0; i < bytes.size(); ++i)
	{
		// Match read_temp_site_payload: only the low two bits of each nibble
		// are used; code 2 is missing, including either half of a partial call.
		const unsigned int first = (bytes[i] >> 4) & 3;
		const unsigned int second = bytes[i] & 3;
		if (haplotypes)
		{
			const size_t lane = 2 * i;
			const uint64_t bit = UINT64_C(1) << (lane % 64);
			if (first != 2) valid[lane / 64] |= bit;
			if (first == 0) reference[lane / 64] |= bit;
			if (second != 2) valid[lane / 64] |= bit << 1;
			if (second == 0) reference[lane / 64] |= bit << 1;
		}
		else if (first != 2 && second != 2)
		{
			const uint64_t bit = UINT64_C(1) << (i % 64);
			valid[i / 64] |= bit;
			if (first != second) heterozygous[i / 64] |= bit;
			else if (first == 0) reference[i / 64] |= bit;
		}
	}
}

size_t ld_bitsets::storage_bytes() const
{
	return sizeof(uint64_t) * (valid.capacity() + reference.capacity() + heterozygous.capacity());
}

ld_moments count_ld_haplotypes(const ld_bitsets &a, const ld_bitsets &b)
{
	ld_moments out;
	for (size_t i = 0; i < a.valid.size(); ++i)
	{
		const uint64_t valid = a.valid[i] & b.valid[i];
		const uint64_t x = a.reference[i] & valid;
		const uint64_t y = b.reference[i] & valid;
		out.n += population_count(valid);
		out.x += population_count(x);
		out.y += population_count(y);
		out.xy += population_count(x & y);
	}
	out.xx = out.x;
	out.yy = out.y;
	return out;
}

ld_moments count_ld_genotypes(const ld_bitsets &a, const ld_bitsets &b)
{
	ld_moments out;
	for (size_t i = 0; i < a.valid.size(); ++i)
	{
		const uint64_t valid = a.valid[i] & b.valid[i];
		const uint64_t ar = a.reference[i] & valid, br = b.reference[i] & valid;
		const uint64_t ah = a.heterozygous[i] & valid, bh = b.heterozygous[i] & valid;
		const unsigned int nr_a = population_count(ar), nr_b = population_count(br);
		const unsigned int nh_a = population_count(ah), nh_b = population_count(bh);
		out.n += population_count(valid);
		out.x += 2 * nr_a + nh_a;
		out.y += 2 * nr_b + nh_b;
		out.xx += 4 * nr_a + nh_a;
		out.yy += 4 * nr_b + nh_b;
		out.xy += 4 * population_count(ar & br) + 2 * population_count(ar & bh)
			+ 2 * population_count(ah & br) + population_count(ah & bh);
	}
	return out;
}

ld_site_reader::ld_site_reader(std::ifstream &input, size_t samples, bool haplotypes, size_t cache_bytes)
	: input(input), samples(samples), haplotypes(haplotypes), budget(cache_bytes), used(0),
	  cursor(0), current_offset(0), payload_offset(0), position(0) {}

void ld_site_reader::seek(std::streamoff offset) { cursor = offset; }
std::streamoff ld_site_reader::tell() const { return cursor; }
size_t ld_site_reader::cached_storage_bytes() const { return used; }

size_t ld_site_reader::cached_site::storage_bytes() const
{
	// Charge record objects and allocated payload capacity. Map/list bookkeeping
	// and allocator overhead are additional, bounded by the number of records.
	return sizeof(cached_site) + chromosome.capacity() + 1 + bits.storage_bytes();
}

void ld_site_reader::touch(site_map::iterator site)
{
	recency.splice(recency.begin(), recency, site->second.recency);
}

void ld_site_reader::read_header(std::string &chrom, int &pos)
{
	current_offset = cursor;
	site_map::iterator hit = sites.find(current_offset);
	if (hit != sites.end())
	{
		touch(hit);
		chromosome = hit->second.chromosome;
		position = hit->second.position;
		payload_offset = hit->second.payload_offset;
	}
	else
	{
		input.seekg(current_offset);
		if (!std::getline(input, chromosome) || !input.read(reinterpret_cast<char *>(&position), sizeof(position)))
			throw std::runtime_error("Could not read LD temporary site header");
		payload_offset = input.tellg();
	}
	chrom = chromosome;
	pos = position;
}

void ld_site_reader::skip_payload()
{
	cursor = payload_offset + static_cast<std::streamoff>(samples);
}

const ld_bitsets &ld_site_reader::read_payload()
{
	skip_payload();
	site_map::iterator hit = sites.find(current_offset);
	if (hit != sites.end()) return hit->second.bits;
	bytes.resize(samples);
	input.seekg(payload_offset);
	if (samples && !input.read(reinterpret_cast<char *>(&bytes[0]), samples))
		throw std::runtime_error("Could not read LD temporary site genotypes");
	uncached.decode(bytes, haplotypes);
	cached_site next;
	next.chromosome = chromosome;
	next.position = position;
	next.payload_offset = payload_offset;
	next.bits = uncached;
	const size_t cost = next.storage_bytes();
	if (cost > budget) return uncached;
	while (used > budget - cost)
	{
		site_map::iterator victim = sites.find(recency.back());
		used -= victim->second.storage_bytes();
		sites.erase(victim);
		recency.pop_back();
	}
	recency.push_front(current_offset);
	next.recency = recency.begin();
	std::pair<site_map::iterator, bool> inserted = sites.insert(std::make_pair(current_offset, next));
	used += inserted.first->second.storage_bytes();
	return inserted.first->second.bits;
}

void ld_site_reader::read_site(std::string &chrom, int &pos, ld_bitsets &result)
{
	read_header(chrom, pos);
	result = read_payload();
}
