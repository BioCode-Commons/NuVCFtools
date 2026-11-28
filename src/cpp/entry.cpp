/*
 * entry.cpp
 *
 *  Created on: Dec 12, 2012
 *      Author: amarcketta
 */

#include "entry.h"

// Parse only calls that the consuming statistic would visit.
void entry::parse_kept_genotype_entries(bool GT, bool GQ, bool DP, bool FT)
{
	for (unsigned int i=0; i<N_indv; ++i)
		if (include_indv[i] && include_genotype[i])
			parse_genotype_entry(i, GT, GQ, DP, FT);
}

/*
// This function implements an exact SNP test of Hardy-Weinberg
// Equilibrium as described in Wigginton, JE, Cutler, DJ, and
// Abecasis, GR (2005) A Note on Exact Tests of Hardy-Weinberg
// Equilibrium. American Journal of Human Genetics. 76: 000 - 000
//
// Written by Jan Wigginton
*/
void entry::SNPHWE(int obs_hets, int obs_hom1, int obs_hom2, double &p_hwe, double &p_lo, double &p_hi)
{
	p_hwe = 1.0; p_lo = 1.0; p_hi = 1.0; //p_hi_lo = 1.0;
	if (obs_hom1 + obs_hom2 + obs_hets == 0 ) return;

	if (obs_hom1 < 0 || obs_hom2 < 0 || obs_hets < 0)
		LOG.error("Internal error: negative count in HWE test", 91);

	int obs_homc = obs_hom1 < obs_hom2 ? obs_hom2 : obs_hom1;
	int obs_homr = obs_hom1 < obs_hom2 ? obs_hom1 : obs_hom2;

	int rare_copies = 2 * obs_homr + obs_hets;
	int genotypes   = obs_hets + obs_homc + obs_homr;

	// A heterozygote uses one rare copy, so its count has the same parity as
	// rare_copies. Store only those possible counts: count h is at index h/2.
	const int n_het_probs = rare_copies / 2 + 1;
	double * het_probs = (double *) malloc((size_t) n_het_probs * sizeof(double));
	if (het_probs == NULL)
		LOG.error("Internal error: SNP-HWE: Unable to allocate array", 90);

	/* start at midpoint */
	int mid = rare_copies * (2 * genotypes - rare_copies) / (2 * genotypes);

	/* check to ensure that midpoint and rare alleles have same parity */
	if ((rare_copies & 1) ^ (mid & 1))
		mid++;

	int curr_hets = mid;
	int curr_homr = (rare_copies - mid) / 2;
	int curr_homc = genotypes - curr_hets - curr_homr;

	het_probs[mid / 2] = 1.0;
	double sum = het_probs[mid / 2];
	for (curr_hets = mid; curr_hets > 1; curr_hets -= 2)
	{
	  het_probs[(curr_hets - 2) / 2] = het_probs[curr_hets / 2] * curr_hets * (curr_hets - 1.0) / (4.0 * (curr_homr + 1.0) * (curr_homc + 1.0));
	  sum += het_probs[(curr_hets - 2) / 2];

	  /* 2 fewer heterozygotes for next iteration -> add one rare, one common homozygote */
	  curr_homr++;
	  curr_homc++;
	}

	curr_hets = mid;
	curr_homr = (rare_copies - mid) / 2;
	curr_homc = genotypes - curr_hets - curr_homr;
	for (curr_hets = mid; curr_hets <= rare_copies - 2; curr_hets += 2)
	{
	  het_probs[(curr_hets + 2) / 2] = het_probs[curr_hets / 2] * 4.0 * curr_homr * curr_homc	/((curr_hets + 2.0) * (curr_hets + 1.0));
	  sum += het_probs[(curr_hets + 2) / 2];

	  /* add 2 heterozygotes for next iteration -> subtract one rare, one common homozygote */
	  curr_homr--;
	  curr_homc--;
	}

	// Both recurrences fill every stored element. Impossible counts contributed
	// only positive zero; omitting them preserves the order of all other terms.
	for (int i = 0; i < n_het_probs; i++)
		het_probs[i] /= sum;

	// alternate p-value calculation for p_hi/p_lo
	const int observed_idx = obs_hets / 2;
	p_hi = het_probs[observed_idx];
	for (int i = observed_idx + 1; i < n_het_probs; i++)
	 p_hi += het_probs[i];

	p_lo = het_probs[observed_idx];
	for (int i = observed_idx - 1; i >= 0; i--)
	  p_lo += het_probs[i];

	//p_hi_lo = p_hi < p_lo ? 2.0 * p_hi : 2.0 * p_lo;

	p_hwe = 0.0;
	/*  p-value calculation for p_hwe  */
	for (int i = 0; i < n_het_probs; i++)
	{
		if (het_probs[i] > het_probs[observed_idx])
			continue;
		p_hwe += het_probs[i];
	}

	p_hwe = p_hwe > 1.0 ? 1.0 : p_hwe;

	free(het_probs);
}

void entry::make_typed_string(vector<char> &out, const string &in, bool typed)
{
	vector<char> tmp_vector;
	out.resize(0);

	if (in == "." or in == " " or in == "")
	{
		if (typed == false)
			return;

		int8_t tmp = (int8_t)0;
		tmp = tmp << 4;
		tmp = tmp | (int8_t)7;
		out.push_back( tmp );

		return;
	}

	if (typed == true)
	{
		if (in.length() >= 15)
		{
			int8_t tmp = (int8_t)15;
			tmp = tmp << 4;
			tmp = tmp | (int8_t)7;
			out.push_back( tmp );

			make_typed_int(tmp_vector, in.length(), typed);
			out.insert( out.end(), tmp_vector.begin(), tmp_vector.end() );
		}
		else
		{
			int8_t tmp = (int8_t)in.length();
			tmp = tmp << 4;
			tmp = tmp | (int8_t)7;
			out.push_back( tmp );
		}
	}
	out.reserve(out.size()+in.size());
	copy(in.begin(), in.end(), back_inserter(out));
}

void entry::make_typed_int(vector<char> &out, const int &in, bool typed)
{
	vector<char> tmp_char;
	out.resize(0);

	int type;
	int8_t size_type = (int8_t)1;
	if (in < 127 and in >-127)
		type = 1;
	else if (in < 32767 and in>-32767)
		type = 2;
	else
		type = 3;

	make_int(tmp_char, in, type);

	if (typed == true)
	{
		size_type = size_type << 4;
		size_type = size_type | type;
		out.push_back(size_type);
	}
	out.insert(out.end(), tmp_char.begin(), tmp_char.end());
}

void entry::make_typed_string_vector( vector<char> &out, const vector<string> &in, int number )
{
	vector<char> tmp_char;
	int max_val = 0;
	int8_t size_type;
	out.resize(0);

	if (number == -1)
	{
		for (unsigned int ui=0; ui<in.size(); ui++)
		{
			if ((int)in[ui].size() > max_val)
				max_val = in[ui].size();
		}
	}
	else
		max_val = number;

	if (max_val < 15)
	{
		size_type = (int8_t)max_val;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)7;

		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)7;

		out.push_back( size_type );

		make_typed_int(tmp_char, max_val, true);
		out.insert( out.end(), tmp_char.begin(), tmp_char.end() );
	}

	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		for (unsigned int uj=0; (int)uj<max_val; uj++)
		{
			if (in[ui] == ".")
				out.push_back( '\0' );
			else if (uj<in[ui].size())
				out.push_back( in[ui][uj] );
			else
				out.push_back( '\0' );
		}
	}
}

void entry::make_typed_GT_vector(vector<char> &out, vector<string> &in )
{
	vector<char> tmp_vector;
	int8_t size_type;
	int max_ploidy = 0;
	out.resize(0);

	max_ploidy = *max_element(ploidy.begin(), ploidy.end());

	if (max_ploidy < 15)
	{
		size_type = (int8_t)max_ploidy;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)1;

		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)1;

		out.push_back( size_type );

		make_typed_int(tmp_vector, max_ploidy, true);
		out.insert( out.end(), tmp_vector.begin(), tmp_vector.end() );
		tmp_vector.resize(0);
	}

	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		encode_genotype(tmp_vector, in[ui], max_ploidy);
		out.insert( out.end(), tmp_vector.begin(), tmp_vector.end() );
		tmp_vector.resize(0);
	}
	out.insert( out.end(), tmp_vector.begin(), tmp_vector.end() );
}

void entry::encode_genotype(vector<char> &out, string &in, int exp_size)
{
	int8_t tmp_int;
	int8_t phased = 0;
	out.resize(exp_size);
	int idx = 0;

	for (unsigned int ui=0; ui<in.length(); ui++)
	{
		if (in[ui] =='|')
			phased = 1;
		else if (in[ui] == '/')
			phased = 0;
		else
		{
			if(in[ui] != '.')
			{
				tmp_int = header::str2int( in.substr(ui,1) );
				tmp_int++;
				tmp_int = tmp_int << 1;
				tmp_int = tmp_int | phased;
			}
			else
				tmp_int = 0x80;

			out[idx] = (int8_t)tmp_int;
			idx++;
		}
	}
	while (idx<exp_size)
	{
		out[idx] = (int8_t)0x81;
		idx++;
	}
}

// Reparse short numeric text to avoid a full integer matrix. For long text,
// retaining the converted values avoids paying the conversion cost twice.
// The limit is the average number of input characters per encoded integer.
static const size_t bcf_integer_reparse_limit = 64;

// Read one comma-delimited value without copying the complete token list.
// A trailing delimiter has no token, just as in header::tokenize; absent
// fields are vector-end sentinels, whereas empty fields and "." are missing.
static int next_bcf_integer(const string &in, string::size_type &position)
{
	if (position == string::npos || position >= in.size())
		return 0x80000001;

	const string::size_type end = in.find(',', position);
	const string::size_type length = (end == string::npos ? in.size() : end) - position;
	int value;
	if (length == 0 || (length == 1 && in[position] == '.'))
		value = 0x80000000;
	else if (length <= 2 && in[position] >= '0' && in[position] <= '9' &&
		(length == 1 || (in[position+1] >= '0' && in[position+1] <= '9')))
	{
		value = in[position] - '0';
		if (length == 2)
			value = value * 10 + in[position+1] - '0';
	}
	else
		value = atoi(in.c_str() + position);
	position = end == string::npos ? string::npos : end + 1;
	return value;
}

void entry::make_typed_int_vector(vector<char> &out, const string &in, int number )
{
	vector<char> tmp_char;
	int converted, type;
	int8_t size_type;
	unsigned int max = 0;
	unsigned int max_val = 0;
	out.resize(0);

	if (in == " " or in == "." or in == "")
	{
		size_type = (int8_t)0;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)1;

		out.push_back( size_type );
		return;
	}

	if (number == -1)
	{
		max_val = count(in.begin(), in.end(), ',');
		if (in[in.size()-1] != ',')
			max_val++;
	}
	else
		max_val = number;

	const bool retain_values = max_val != 0 && in.size() / max_val > bcf_integer_reparse_limit;
	vector<int> retained_values;
	// Determine the common width first. Short fields are read again below;
	// expensive long values are retained in their original conversion order.
	string::size_type position = 0;
	for (unsigned int ui=0; ui<max_val; ui++)
	{
		const bool has_value = position != string::npos && position < in.size();
		// Padding cannot widen the type, and 32 bits is already the widest.
		// Retained values still need the complete original conversion pass.
		if (!retain_values && (!has_value || max >= 32767))
			break;
		converted = next_bcf_integer(in, position);
		if (has_value && (converted != (int)0x80000000) && (abs(converted) > (int)max))
			max = abs(converted);
		if (retain_values)
			retained_values.push_back(converted);
	}

	if (max < 127)
		type = 1;
	else if (max < 32767)
		type = 2;
	else
		type = 3;

	if (max_val < 15)
	{
		size_type = (int8_t)max_val;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );

		make_typed_int(tmp_char, max_val, true);
		out.insert( out.end(), tmp_char.begin(), tmp_char.begin() );
	}

	position = 0;
	for (unsigned int ui=0; ui<max_val; ui++)
	{
		converted = retain_values ? retained_values[ui] : next_bcf_integer(in, position);
		make_int(tmp_char, converted, type);
		out.insert( out.end(), tmp_char.begin(), tmp_char.end() );
	}
}

void entry::make_typed_int_vector(vector<char> &out, const vector<string> &in, int number )
{
	vector<char> tmp_char;
	int converted, type;
	int8_t size_type;
	unsigned int max = 0;
	unsigned int max_val = 0;
	out.resize(0);

	if (number == -1)
	{
		unsigned int tmp_int = 0;
		for (unsigned int ui=0; ui<in.size(); ui++)
		{
			tmp_int = count(in[ui].begin(), in[ui].end(), ',');

			if (tmp_int > max_val)
				max_val = tmp_int;
		}
		max_val++;
	}
	else
		max_val = number;

	size_t text_size = 0;
	for (unsigned int ui=0; ui<in.size(); ui++)
		text_size += in[ui].size();
	const bool retain_values = !in.empty() && max_val != 0 &&
		text_size / in.size() / max_val > bcf_integer_reparse_limit;
	vector<int> retained_values;

	// Only long text needs a retained integer matrix; ordinary columns use
	// the original strings for a second, bounded-storage pass.
	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		if (!retain_values && max >= 32767)
			break;
		string::size_type position = 0;
		for (unsigned int uj=0; uj<max_val; uj++)
		{
			const bool has_value = position != string::npos && position < in[ui].size();
			// Only present values can widen the type; no type exceeds 32 bits.
			if (!retain_values && (!has_value || max >= 32767))
				break;
			converted = next_bcf_integer(in[ui], position);
			if (has_value && (converted != (int)0x80000000) && (abs(converted) > (int)max))
				max = abs(converted);
			if (retain_values)
				retained_values.push_back(converted);
		}
	}

	if (max < 127)
		type = 1;
	else if (max < 32767)
		type = 2;
	else
		type = 3;
	if (max_val < 15)
	{
		size_type = (int8_t)max_val;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );

		make_typed_int(tmp_char, max_val, true);
		out.insert( out.end(), tmp_char.begin(), tmp_char.begin() );
	}

	size_t retained_index = 0;
	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		string::size_type position = 0;
		for (unsigned int uj=0; uj<max_val; uj++)
		{
			converted = retain_values ? retained_values[retained_index++] : next_bcf_integer(in[ui], position);
			make_int(tmp_char, converted, type);
			out.insert( out.end(), tmp_char.begin(), tmp_char.end() );
		}
	}
}

void entry::make_typed_int_vector(vector<char> &out, const vector<int> &in )
{
	vector<char> tmp_char;
	int type;
	int8_t size_type;
	unsigned int max = 0;
	out.resize(0);

	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		if ((abs(in[ui]) > (int)max) and ( (int8_t)in[ui] != (int8_t)0x80))
			max = abs(in[ui]);
	}

	if (max < 127)
		type = 1;
	else if (max < 32767)
		type = 2;
	else
		type = 3;

	if (in.size() < 15)
	{
		size_type = (int8_t)in.size();
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)type;

		out.push_back( size_type );

		make_typed_int(tmp_char, in.size(), true);
		out.insert( out.end(), tmp_char.begin(), tmp_char.begin() );
	}

	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		make_int(tmp_char, in[ui], type);
		out.insert( out.end(), tmp_char.begin(), tmp_char.end() );
	}
}

void entry::make_int(vector<char> &out, const int &in, int type)
{
	out.resize(0);
	if (type == 1)
	{
		int8_t tmp_int;
		if (in == (int)0x80000000 || in >= 128)
			tmp_int = (int8_t)0x80;
		else if (in == (int)0x80000001)
			tmp_int = (int8_t)0x81;
		else
			tmp_int = (int8_t)in;
		out.push_back( (int8_t)tmp_int);
	}
	else if (type == 2)
	{
		int16_t tmp_int;

		if (in == (int)0x80000000 || in >= 32768)
			tmp_int = 0x8000;
		else if (in == (int)0x80000001)
			tmp_int = (int8_t)0x8001;
		else
			tmp_int = (int16_t)in;

		int8_t split;
		for(unsigned int ui=0; ui<2; ui++)
		{
			split = tmp_int & (int16_t)0x00FF;//0000000011111111
			out.push_back(split);
			tmp_int = tmp_int >> 8;
		}
	}
	else
	{
		int32_t tmp_int;
		tmp_int = (int32_t)in;

		int8_t split;
		for(unsigned int ui=0; ui<4; ui++)
		{
			split = tmp_int & (int32_t)0x0000FF;
			out.push_back( (int8_t)split);
			tmp_int = tmp_int >> 8;
		}
	}
}

void entry::make_typed_float_vector(vector<char> &out, const string &in, int number )
{
	vector<string> split_string;
	int8_t size_type;
	int max_val = 0;
	out.resize(0);

	if (in == " " or in == "." or in == "")
	{
		size_type = (int8_t)0;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)1;

		out.push_back( size_type );
		return;
	}

	header::tokenize(in, ',', split_string);
	if (number == -1)
		max_val = split_string.size();
	else
		max_val = number;

	if ( max_val < 15 )
	{
		size_type = (int8_t)max_val;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)5;
		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)5;
		out.push_back( size_type );

		vector<char> size_vector;
		make_typed_int(size_vector, max_val, true );
		out.insert(out.end(), size_vector.begin(), size_vector.end());
	}

	float value;
	char missing[4] = {static_cast<char>(0x01), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};
	char end[4] = {static_cast<char>(0x02), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};

	for(unsigned int ui=0; (int)ui<max_val; ui++)
	{
		if (ui < split_string.size() )
			value = (float)header::str2double(split_string[ui], 0x7F800001);
		else
			value = 0x7F800002;

		char *p = (char *)&value;

		for(unsigned int uj=0; uj<sizeof(value); uj++)
			if (value == (float)0x7F800001)
				out.push_back( missing[uj] );
			else if (value == (float)0x7F800002)
				out.push_back( end[uj] );
			else
				out.push_back( p[uj] );
	}
}

void entry::make_typed_float_vector(vector<char> &out, const vector<string> &in, int number )
{
	vector<string> split_string;
	int8_t size_type;
	unsigned int max_val = 0;
	out.resize(0);

	if (number == -1)
	{
		unsigned int tmp_int = 0;
		for (unsigned int ui=0; ui<in.size(); ui++)
		{
			tmp_int = count(in[ui].begin(), in[ui].end(), ',');
			if (tmp_int > max_val)
				max_val = tmp_int;
		}
		max_val++;
	}
	else
		max_val = number;

	if ( max_val < 15 )
	{
		size_type = (int8_t)max_val;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)5;
		out.push_back( size_type );
	}
	else
	{
		size_type = (int8_t)15;
		size_type = size_type << 4;
		size_type = size_type | (int8_t)5;
		out.push_back( size_type );

		vector<char> size_vector;
		make_typed_int(size_vector, max_val, true );
		out.insert(out.end(), size_vector.begin(), size_vector.end());
	}

	float value;
	char missing[4] = {static_cast<char>(0x01), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};
	char end[4] = {static_cast<char>(0x02), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};
	for (unsigned int ui=0; ui<in.size(); ui++)
	{
		header::tokenize(in[ui], ',', split_string);
		for(unsigned int uj=0; uj<max_val; uj++)
		{
			if (uj < split_string.size() )
				value = (float)header::str2double(split_string[uj], 0x7F800001);
			else
				value = (float)0x7F800002;

			char *p = (char *)&value;

			for(unsigned int uk=0; uk<sizeof(value); uk++)
			{
				if (value == float(0x7F800001))
					out.push_back( missing[uk] );
				else if (value == float(0x7F800002))
					out.push_back( end[uk] );
				else
					out.push_back( p[uk] );
			}
		}
	}
}

void entry::make_type_size(vector<char> &out, const unsigned int &type, const unsigned int &size)
{
	uint8_t byte;
	vector<char> tmp_vector;
	tmp_vector.resize(0);
	out.resize(0);

	if (size < 15)
	{
		byte = size;
		byte = byte << 4;
	}
	else
	{
		byte = (uint8_t)15;
		make_typed_int(tmp_vector, size, true);
	}

	byte = byte | (uint8_t)type;
	out.push_back(byte);
	out.insert(out.end(), tmp_vector.begin(), tmp_vector.end());
}

string entry::get_typed_string(unsigned int * line_position, const vector<char>& line)
{
	unsigned int size, type;
	string out;

	get_type( line_position, line, type, size );
	if (type != 7)
	{
		LOG.printLOG("Error: Expected type 7 for string. Found type " + header::int2str(type) + ".\n");
	}

	char * tmp = new char[size];
	memcpy(tmp, &line[*line_position], size*sizeof(char));
	*line_position += size;
	out = string( tmp, size );

	if (out == "" or out == " ")
		out = ".";

	delete [] tmp;
	return out;
}

int entry::get_typed_int(unsigned int * line_position, const vector<char>& line, unsigned int &type, unsigned int &size)
{
	int out;

	get_type( line_position, line, type, size );

	if (size > 1)
		LOG.error("Int vector when expected only a single Integer value.\n" );

	if (type == 1)
	{
		int8_t tmp;
		tmp = *reinterpret_cast<const int8_t*>(&line[*line_position]);
		*line_position += sizeof(tmp);
		out = tmp;
	}
	else if (type == 2)
	{
		int16_t tmp;
		tmp = read_bcf_scalar<int16_t>(&line[*line_position]);
		*line_position += sizeof(tmp);
		out = tmp;
	}
	else if (type == 3)
	{
		int32_t tmp;
		tmp = read_bcf_scalar<int32_t>(&line[*line_position]);
		*line_position += sizeof(tmp);
		out = tmp;
	}
	else
		LOG.error("Invalid type for integer size.\n");
	
	return out;
}

vector<int> entry::get_int_vector(unsigned int * line_position, const vector<char>& line)
{
	unsigned int size, type;
	get_type( line_position, line, type, size );
	vector<int> out(size);

	if (type == 0)
	{
		return out;
	}
	else if (type == 1)
	{
		int8_t tmp;
		for (unsigned int ui=0; ui<size; ui++)
		{
			tmp = *reinterpret_cast<const int8_t*>(&line[*line_position]);
			*line_position += sizeof(tmp);
			out[ui] = tmp;
		}
	}
	else if (type == 2)
	{
		int16_t tmp;
		for (unsigned int ui=0; ui<size; ui++)
		{
			tmp = read_bcf_scalar<int16_t>(&line[*line_position]);
			*line_position += sizeof(tmp);
			out[ui] = tmp;
		}
	}
	else if (type == 3)
	{
		int32_t tmp;
		for (unsigned int ui=0; ui<size; ui++)
		{
			tmp = read_bcf_scalar<int32_t>(&line[*line_position]);
			*line_position += sizeof(tmp);
			out[ui] = tmp;
		}
	}
	else
		LOG.error("Invalid type for integer size.\n");

	return out;
}

void entry::get_type(unsigned int * line_position, const vector<char>& line, unsigned int &type, unsigned int &size)
{
	uint8_t byte = *reinterpret_cast<const uint8_t*>(&line[*line_position]);
	*line_position += sizeof(byte);
	size = byte >> 4;
	type = (byte & (uint8_t)15);

	if (size == 15)
	{
		int type2;
		byte = *reinterpret_cast<const uint8_t*>(&line[*line_position]);
		*line_position += sizeof(byte);

		type2 = (byte & (uint8_t)15);
		if (type2 == 1)
		{
			int8_t tmp;
			tmp = *reinterpret_cast<const int8_t*>(&line[*line_position]);
			*line_position += sizeof(tmp);
			size = (unsigned int)tmp;
		}
		else if (type2 == 2)
		{
			int16_t tmp;
			tmp = read_bcf_scalar<int16_t>(&line[*line_position]);
			*line_position += sizeof(tmp);

			size = (int)tmp;
		}
		else if (type2 == 3)
		{
			int32_t tmp;
			tmp = read_bcf_scalar<int32_t>(&line[*line_position]);
			*line_position += sizeof(tmp);
			size = (unsigned int)tmp;
		}
		else
			LOG.error("Invalid type for integer size.\n");
	}
}

void entry::skip_section(unsigned int *line_position, const vector<char> &line)
{
	unsigned int type, size;
	get_type(line_position, line, type, size);

	if ( (type == 1) || (type == 7) )
		*line_position += sizeof(int8_t)*size;
	else if (type == 2)
		*line_position += sizeof(int16_t)*size;
	else if ( (type == 3) || (type == 5) )
		*line_position += sizeof(int32_t)*size;
}

bool entry::check_missing(unsigned int line_position, const unsigned int type, const vector<char> &line)
{
	static char missing_float[4] = {static_cast<char>(0x01), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};
	static char missing_int1 = static_cast<char>(0x80);
	static char missing_int2[2] = {static_cast<char>(0x00), static_cast<char>(0x80)};
	static char missing_int3[4] = {static_cast<char>(0x00), static_cast<char>(0x00), static_cast<char>(0x00), static_cast<char>(0x80)};

	char test_char;
	bool missing = true;
	if (type==1)
	{
		test_char = *reinterpret_cast<const char*>(&line[line_position]);
		missing = (test_char == missing_int1);
	}
	else if (type==2)
	{
		for (unsigned int ui=0; ui<sizeof(int16_t); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != missing_int2[ui])
			{
				missing = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==3)
	{
		for (unsigned int ui=0; ui<sizeof(int32_t); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != missing_int3[ui])
			{
				missing = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==5)
	{
		for (unsigned int ui=0; ui<sizeof(float); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != missing_float[ui])
			{
				missing = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==7)
		missing = false;

	return missing;
}

bool entry::check_end(unsigned int line_position, const unsigned int type, const vector<char> &line)
{
	static char end_float[4] = {static_cast<char>(0x02), static_cast<char>(0x00), static_cast<char>(0x80), static_cast<char>(0x7F)};
	static char end_int1 = static_cast<char>(0x81);
	static char end_int2[2] = {static_cast<char>(0x01), static_cast<char>(0x80)};
	static char end_int3[4] = {static_cast<char>(0x01), static_cast<char>(0x00), static_cast<char>(0x00), static_cast<char>(0x80)};

	char test_char;
	bool end = true;
	if (type==1)
	{
		test_char = *reinterpret_cast<const char*>(&line[line_position]);
		end = (test_char == end_int1);
	}
	else if (type==2)
	{
		for (unsigned int ui=0; ui<sizeof(int16_t); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != end_int2[ui])
			{
				end = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==3)
	{
		for (unsigned int ui=0; ui<sizeof(int32_t); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != end_int3[ui])
			{
				end = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==5)
	{
		for (unsigned int ui=0; ui<sizeof(float); ui++)
		{
			test_char = *reinterpret_cast<const char*>(&line[line_position]);
			if (test_char != end_float[ui])
			{
				end = false;
				break;
			}
			line_position += sizeof(char);
		}
	}
	else if (type==7)
		end = false;

	return end;
}

void entry::get_number(uint32_t &out, unsigned int *line_position, const vector<char>& line)
{
	memcpy(&out, &line[*line_position], sizeof(out));
	*line_position += sizeof(out);
}
