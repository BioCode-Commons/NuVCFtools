/*
 * variant_file.cpp
 *
 *  Created on: Dec 11, 2012
 *      Author: amarcketta
 */

#include "variant_file.h"

variant_file::~variant_file() {}

// Return the number of individuals that have not been filtered out
int variant_file::N_kept_individuals() const
{
	int N_kept = 0;
	for (unsigned int ui=0; ui<include_indv.size(); ui++)
		if (include_indv[ui] == true)
			N_kept++;
	return N_kept;
}

// Return the number of sites that have not been filtered out
int variant_file::N_kept_sites() const
{
	return N_kept_entries;
}

// Return the total number of sites in the file
int variant_file::N_total_sites() const
{
	return N_entries;
}

void variant_file::ByteSwap(unsigned char *b, int n) const
{
   int i = 0;
   int j = n-1;
   while (i<j)
   {
      std::swap(b[i], b[j]);
      i++, j--;
   }
}

void variant_file::get_contigs(const string &contigs_file, vector<string> &contig_vector)
{
	if (contigs_file == "")
		LOG.error("Contig declarations in header are necessary for BCF conversion. Use --contigs <filename> to add contigs to the header.");

	ifstream contigs(contigs_file.c_str());
	if (!contigs.is_open())
		LOG.error("Could not open contigs file: " + contigs_file);

	string line;
	int contig_lines = 0;
	contig_vector.resize(0);

	while (getline(contigs, line))
	{
		if (line.find("##contig=")==string::npos)
			LOG.error("Contigs file must contain only contig header lines.");

		contig_vector.push_back(line);
		contig_lines++;
	}

	contigs.close();
	LOG.printLOG("Including "+header::int2str(contig_lines)+" header lines from the contig file.\n");
}

namespace
{
// Read genotype bytes in bounded blocks, leaving the final byte as a normal
// read so the caller observes the same gcount and stream state. Failed reads
// leave the supplied byte unchanged, as in the original one-byte reader.
class ld_temp_byte_reader
{
	ifstream &input;
	char buffer[4096];
	size_t remaining;
	size_t next;
	size_t count;
public:
	ld_temp_byte_reader(ifstream &stream, size_t bytes)
		: input(stream), remaining(bytes), next(0), count(0) {}

	void read(char &value)
	{
		if (remaining > 1)
		{
			if (next == count && input.good())
			{
				const size_t bytes = min(remaining - 1, sizeof(buffer));
				input.read(buffer, static_cast<streamsize>(bytes));
				count = static_cast<size_t>(input.gcount());
				next = 0;
			}
			if (next < count)
				value = buffer[next++];
			else
				input.read(&value, sizeof(value));
		}
		else
			input.read(&value, sizeof(value));
		--remaining;
	}

	void discard()
	{
		// Consume the same reads as read(), but do not visit every buffered byte.
		// A short read still falls back to the original one-byte failed reads.
		while (remaining > 1 && input.good())
		{
			if (next == count)
			{
				const size_t bytes = min(remaining - 1, sizeof(buffer));
				input.read(buffer, static_cast<streamsize>(bytes));
				count = static_cast<size_t>(input.gcount());
				next = 0;
			}
			if (next == count)
				break;
			remaining -= count - next;
			next = count;
		}
		char ignored;
		while (remaining != 0)
			read(ignored);
	}
};
}

void variant_file::read_temp_site_header(ifstream &tmp_file, string &CHROM, int &POS)
{
	stringstream chr;
	char tmp_char;
	while(true)
	{
		tmp_file.read(&tmp_char,sizeof(char));
		if (tmp_char == '\n')
			break;
		chr << tmp_char;
	}
	CHROM = chr.str();

	tmp_file.read((char*)&POS,sizeof(POS));
}

void variant_file::read_temp_site_payload(ifstream &tmp_file, vector<ld_genotype> &GTs)
{
	ld_temp_byte_reader bytes(tmp_file, GTs.size());
	char in_byte, tmp_gt;
	for(unsigned int ui=0; ui<GTs.size(); ui++)
	{
		bytes.read(in_byte);
		tmp_gt = in_byte & 0x03;
		if (tmp_gt == 0x02)
			GTs[ui].second = -1;
		else
			GTs[ui].second = (int)tmp_gt;
		in_byte = in_byte >> 4;
		tmp_gt = in_byte & 0x03;
		if (tmp_gt == 0x02)
			GTs[ui].first = -1;
		else
			GTs[ui].first = (int)tmp_gt;
	}
}

void variant_file::read_big_temp_site_header(ifstream &tmp_file, string &CHROM, int &POS, int &alleles)
{
	stringstream chr;
	char tmp_char;
	while(true)
	{
		tmp_file.read(&tmp_char,sizeof(char));
		if (tmp_char == '\n')
			break;
		chr << tmp_char;
	}
	CHROM = chr.str();

	tmp_file.read((char*)&POS,sizeof(POS));

	int8_t tmp_alleles;
	tmp_file.read((char*)&tmp_alleles,sizeof(tmp_alleles));
	alleles = (int)tmp_alleles;
}

void variant_file::read_big_temp_site_payload(ifstream &tmp_file, vector<ld_genotype> &GTs)
{
	ld_temp_byte_reader bytes(tmp_file, GTs.size() * 2);
	char in_byte = 0xFF;
	for(unsigned int ui=0; ui<GTs.size(); ui++)
	{
		bytes.read(in_byte);
		if (in_byte == (char)0xFF)
			GTs[ui].first = -1;
		else
			GTs[ui].first = (int)in_byte;

		bytes.read(in_byte);
		if (in_byte == (char)0xFF)
			GTs[ui].second = -1;
		else
			GTs[ui].second = (int)in_byte;
	}
}

void variant_file::discard_temp_site_payload(ifstream &tmp_file, size_t bytes)
{
	ld_temp_byte_reader reader(tmp_file, bytes);
	reader.discard();
}

void variant_file::read_temp_site(ifstream &tmp_file, string &CHROM, int &POS, vector<ld_genotype> &GTs)
{
	read_temp_site_header(tmp_file, CHROM, POS);
	read_temp_site_payload(tmp_file, GTs);
}

void variant_file::read_big_temp_site(ifstream &tmp_file, string &CHROM, int &POS, int &alleles, vector<ld_genotype> &GTs)
{
	read_big_temp_site_header(tmp_file, CHROM, POS, alleles);
	read_big_temp_site_payload(tmp_file, GTs);
}
