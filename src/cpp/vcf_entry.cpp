/*
 * vcf_entry.cpp
 *
 *  Created on: Aug 19, 2009
 *      Author: Adam Auton
 *      ($Revision: 230 $)
 */

#include "vcf_entry.h"

string vcf_entry::convert_line;

vcf_entry::vcf_entry(header &meta_data, vector<bool> &include_individual)
{
	N_indv = meta_data.N_indv;
	include_indv = include_individual;
	include_genotype = vector<bool>(N_indv, true);
	line_empty = true;
	basic_parsed = false; fully_parsed = false;
	parsed_ALT = false; parsed_FILTER = false;
	parsed_INFO = false; parsed_FORMAT = false;
	FORMAT_schema_valid = false;
	CHROM = ""; POS = -1; REF = ""; QUAL = -1;
	passed_filters = true; parsed_FORMAT_binary = false;
	N_INFO_removed = 0; N_FORMAT_removed = 0;
	parsed_GT = vector<bool>(N_indv, false); parsed_GQ = vector<bool>(N_indv, false);
	parsed_DP = vector<bool>(N_indv, false); parsed_FT = vector<bool>(N_indv, false);
	GT_idx = -1; GQ_idx = -1; DP_idx = -1; FT_idx = -1;
	FORMAT_positions.resize(N_indv); FORMAT_types.resize(N_indv); FORMAT_sizes.resize(N_indv); FORMAT_skip.resize(N_indv); FORMAT_keys.resize(N_indv);
	convert_line.clear();
	data_stream.str("");
	entry_header = meta_data;
}

vcf_entry::~vcf_entry() {}

// Reset the VCF entry object with a new data line
void vcf_entry::reset(const vector<char> &data_line)
{
	basic_parsed = false;
	fully_parsed = false;
	parsed_ALT = false;
	parsed_FILTER = false;
	parsed_INFO = false;
	parsed_FORMAT = false;
	parsed_FORMAT_binary = false;
	passed_filters = true;

	data_stream.clear();
	line_empty = data_line.empty();

	// Preserve the conversion scratch string, but give this entry an owned row
	// for independent parsing when comparisons interleave two input files.
	convert_line.assign(data_line.begin(), data_line.end());
	fields.reset(convert_line);

	fill(parsed_GT.begin(), parsed_GT.end(), 0);
	fill(parsed_GQ.begin(), parsed_GQ.end(), 0);
	fill(parsed_DP.begin(), parsed_DP.end(), 0);
	fill(parsed_FT.begin(), parsed_FT.end(), 0);
	fill(include_genotype.begin(), include_genotype.end(), 1);

	N_INFO_removed = 0; N_FORMAT_removed = 0;
	FORMAT_positions.clear(); FORMAT_types.clear(); FORMAT_sizes.clear(); FORMAT_skip.clear(); FORMAT_keys.clear();
}

// Tokenize the basic information in a VCF data line (at the tab level)
void vcf_entry::parse_basic_entry(bool parse_ALT, bool parse_FILTER, bool parse_INFO)
{
	if(!basic_parsed)
	{
		fields.read(CHROM);

		fields.read(ID);
		POS = atoi(ID.c_str());
		fields.read(ID);
		fields.read(REF);
		fields.read(ALT_str);
		fields.read(QUAL_str);
		fields.read(FILTER_str);
		fields.read(INFO_str);

		QUAL = header::str2double(QUAL_str);

		// Convert to uppercase for consistency
		// Note that VCF v4.1 allows mixtures of lower/upper case in REF and ALT.
		// However, the spec specifically states that tools using VCF are not required
		// to preserve the case.
		std::transform(REF.begin(), REF.end(), REF.begin(), ::toupper);
		std::transform(ALT_str.begin(), ALT_str.end(),ALT_str.begin(), ::toupper);
	}
	basic_parsed = true;

	if (parse_ALT && !parsed_ALT)
		set_ALT(ALT_str);
	if (parse_FILTER && !parsed_FILTER)
		set_FILTER(FILTER_str);
	if (parse_INFO && !parsed_INFO)
		set_INFO(INFO_str);
}

// Tokenize the genotype information (at the 'tab' level) in the VCF entry
void vcf_entry::parse_full_entry(bool parse_FORMAT)
{
	if (fully_parsed)
		return;

	if (basic_parsed == false)
		parse_basic_entry();

	fields.read(FORMAT_str);

	if (parse_FORMAT)
		set_FORMAT(FORMAT_str);

	string tmpstr; tmpstr.reserve(64);
	GENOTYPE_str.resize(N_indv, tmpstr);

	for (unsigned int ui=0; ui<N_indv; ui++)
		fields.read(GENOTYPE_str[ui]);

	fully_parsed = true;
}

// Tokenize a given genotype entry into it's component parts
void vcf_entry::parse_genotype_entry(unsigned int indv, bool GT, bool GQ, bool DP, bool FT)
{
	if (fully_parsed == false)
		parse_full_entry(true);

	if (parsed_FORMAT == false)
		set_FORMAT(FORMAT_str);

	static string tmpstr;
	int N_required = GT + GQ + DP + FT;
	int N_got = 0;

	int i=0, start = 0, end = 0;
	while ((end = GENOTYPE_str[indv].find(':',start)) != string::npos)
	{
		if (GT && (i == GT_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start, end - start);
			set_indv_GENOTYPE_and_PHASE(indv, tmpstr);
			N_got++;
		}
		else if (GQ && (i == GQ_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start, end - start);
			set_indv_GQUALITY(indv, header::str2double(tmpstr));
			N_got++;
		}
		else if (DP && (i == DP_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start, end - start);
			set_indv_DEPTH(indv, header::str2int(tmpstr));
			N_got++;
		}
		else if (FT && (i == FT_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start, end - start);
			set_indv_GFILTER(indv, tmpstr);
			N_got++;
		}

		if (N_got == N_required)
			break;
		i++;
		start = end + 1;
	}
	if (N_got != N_required)
	{
		if (GT && (i == GT_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start);
			set_indv_GENOTYPE_and_PHASE(indv, tmpstr);
			N_got++;
		}
		else if (GQ && (i == GQ_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start);
			set_indv_GQUALITY(indv, header::str2double(tmpstr));
			N_got++;
		}
		else if (DP && (i == DP_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start);
			set_indv_DEPTH(indv, header::str2int(tmpstr));
			N_got++;
		}
		else if (FT && (i == FT_idx))
		{
			tmpstr = GENOTYPE_str[indv].substr(start);
			set_indv_GFILTER(indv, tmpstr);
			N_got++;
		}
	}

	// Set missing return values if requested a value, but couldn't find it
	if (GT && (parsed_GT[indv] == false))
	{
		set_indv_GENOTYPE_and_PHASE(indv, make_pair(-1,-1), '/');
	}
	if (GQ && (parsed_GQ[indv] == false))
	{
		set_indv_GQUALITY(indv, -1);
	}
	if (DP && (parsed_DP[indv] == false))
	{
		set_indv_DEPTH(indv, -1);
	}
	if (FT && (parsed_FT[indv] == false))
	{
		set_indv_GFILTER(indv, "");
	}
}

// Read the VCF entry and fully populate the object
void vcf_entry::parse_genotype_entries(bool GT, bool GQ, bool DP, bool FT)
{
	if (N_indv == 0)
		return;

	// Preserve the initialization performed by the first single-entry call,
	// even when no fields were requested or every requested field is cached.
	if (fully_parsed == false)
		parse_full_entry(true);
	if (parsed_FORMAT == false)
		set_FORMAT(FORMAT_str);

	// Identical neighbouring sample text has identical requested fields within
	// this row's FORMAT schema. Reuse decoded values without re-tokenizing or
	// repeating setters; each sample still owns its own values and parse flags.
	unsigned int previous = N_indv;
	unsigned int previous_fields = 0;
	for (unsigned int ui=0; ui<N_indv; ui++)
	{
		const bool need_GT = GT && !parsed_GT[ui];
		const bool need_GQ = GQ && !parsed_GQ[ui];
		const bool need_DP = DP && !parsed_DP[ui];
		const bool need_FT = FT && !parsed_FT[ui];
		const unsigned int requested = need_GT | (need_GQ << 1) | (need_DP << 2) | (need_FT << 3);
		if (!requested)
			continue;
		if (previous < N_indv && requested == previous_fields && GENOTYPE_str[ui] == GENOTYPE_str[previous])
		{
			if (need_GT)
			{
				GENOTYPE[ui] = GENOTYPE[previous];
				PHASE[ui] = PHASE[previous];
				ploidy[ui] = ploidy[previous];
				parsed_GT[ui] = true;
			}
			if (need_GQ)
			{
				if (!GQUALITY.empty()) GQUALITY[ui] = GQUALITY[previous];
				parsed_GQ[ui] = true;
			}
			if (need_DP)
			{
				if (!DEPTH.empty()) DEPTH[ui] = DEPTH[previous];
				parsed_DP[ui] = true;
			}
			if (need_FT)
			{
				GFILTER[ui] = GFILTER[previous];
				parsed_FT[ui] = true;
			}
		}
		else
			parse_genotype_entry(ui, need_GT, need_GQ, need_DP, need_FT);
		previous = ui;
		previous_fields = requested;
	}
}

void vcf_entry::parse_FORMAT()
{
	FORMAT_binary.resize(0);
	vector<char> tmp_vector;
	vector<string> tmp_split;
	vector<string::size_type> next_field;
	vector< vector<string> > format_matrix;

	unsigned int type, number, size, position=0;
	// header::split stores offsets and the initial token count in int. Keep
	// its original matrix path when those conversions can reach that boundary.
	const string::size_type split_offset_limit = (string::size_type)numeric_limits<int>::max();
	bool legacy_split = FORMAT.size() > split_offset_limit;
	for (unsigned int ui=0; ui<N_indv && !legacy_split; ui++)
		legacy_split = GENOTYPE_str[ui].size() >= split_offset_limit;
	if (legacy_split)
	{
		format_matrix.resize(N_indv);
		tmp_split.resize(FORMAT.size());
		for (unsigned int ui=0; ui<N_indv; ui++)
		{
			format_matrix[ui].resize(FORMAT.size());
			if ( (GENOTYPE_str[ui] != "") and (GENOTYPE_str[ui] != ".") )
				header::split(GENOTYPE_str[ui],':', tmp_split);
			else
				tmp_split.assign(FORMAT.size(),".");

			for (unsigned int uj=0; uj<tmp_split.size(); uj++)
				format_matrix[ui][uj] = tmp_split[uj];

			for (unsigned int uj=format_matrix[ui].size(); uj<FORMAT.size(); uj++)
				format_matrix[ui][uj] = ".";
		}
	}
	else
	{
		tmp_split.resize(N_indv);
		next_field.assign(N_indv, 0);
	}

	FORMAT_positions.resize(FORMAT.size()); FORMAT_types.resize(FORMAT.size()); FORMAT_skip.resize(FORMAT.size());

	for (unsigned int ui=0; ui<FORMAT.size(); ui++)
	{
		// Build only the current column. The original reusable split vector did
		// not clear trailing fields of a short row: retain that carry from the
		// preceding sample, including the initial empty string for each field.
		const string empty_field;
		const string *previous_field = &empty_field;
		for (unsigned int uj=0; !legacy_split && uj<N_indv; uj++)
		{
			const string &genotype = GENOTYPE_str[uj];
			if (genotype.empty() || genotype == ".")
				tmp_split[uj] = ".";
			else if (next_field[uj] != string::npos)
			{
				const string::size_type start = next_field[uj];
				const string::size_type end = genotype.find(':', start);
				tmp_split[uj].assign(genotype, start, end == string::npos ? string::npos : end-start);
				next_field[uj] = end == string::npos ? string::npos : end+1;
			}
			else
				tmp_split[uj] = *previous_field;
			previous_field = &tmp_split[uj];
		}

		if (entry_header.FORMAT_reverse_map.find(FORMAT[ui]) == entry_header.FORMAT_reverse_map.end())
		{
			LOG.one_off_warning("FORMAT value " + FORMAT[ui] + " is not defined in the header and will not be encoded.");
			N_FORMAT_removed++;
			continue;
		}
		FORMAT_positions[ui] = position;
		make_typed_int(tmp_vector, entry_header.FORMAT_reverse_map[ FORMAT[ui] ], true );
		FORMAT_binary.insert(FORMAT_binary.end(), tmp_vector.begin(), tmp_vector.end() );

		tmp_vector.resize(0);
		if (legacy_split)
			tmp_split.resize(0);

		type = entry_header.FORMAT_map[ entry_header.FORMAT_reverse_map[FORMAT[ui]] ].Type;
		number = entry_header.FORMAT_map[ entry_header.FORMAT_reverse_map[FORMAT[ui]] ].N_entries;
		if (legacy_split)
			for (unsigned int uj=0; uj<N_indv; uj++)
				tmp_split.push_back(format_matrix[uj][ui]);

		if ((int)ui == GT_idx)
			make_typed_GT_vector(tmp_vector, tmp_split );
		else if (type == Integer)
			make_typed_int_vector(tmp_vector, tmp_split, number );
		else if (type == Float)
			make_typed_float_vector(tmp_vector, tmp_split, number );
		else if ( (type == Character) or (type == String) )
			make_typed_string_vector(tmp_vector, tmp_split, number );
		else
			LOG.error("Invalid type in FORMAT definition");

		position = 0;
		get_type(&position, tmp_vector, type, size);
		FORMAT_types[ui] = type;

		if ( (type == 1) || (type == 7) )
			FORMAT_skip[ui] = size*sizeof(int8_t);
		else if (type == 2)
			FORMAT_skip[ui] = size*sizeof(int16_t);
		else if ( (type == 3) || (type == 5) )
			FORMAT_skip[ui] = size*sizeof(int32_t);

		FORMAT_binary.insert(FORMAT_binary.end(), tmp_vector.begin(), tmp_vector.end() );
		tmp_vector.resize(0);
		position = FORMAT_binary.size();
	}
	parsed_FORMAT_binary = true;
}

// Output VCF entry to output stream
void vcf_entry::print(ostream &out, const set<string> &INFO_to_keep, bool keep_all_INFO)
{
	if (fully_parsed == false)
		parse_full_entry();

	out << get_CHROM() << '\t' << POS << '\t' << get_ID() << '\t' << REF << '\t' << get_ALT();

	out << '\t' << header::double2str(QUAL);
	out << '\t' << get_FILTER();

	if (keep_all_INFO == false)
		out << '\t' << get_INFO(INFO_to_keep);
	else
		out << '\t' << INFO_str;

	pair<int, int> genotype;
	string GFILTER_tmp;
	// Adjacent equal decoded calls share their serialized GT, while every
	// sample retains independent filters and all other FORMAT fields.
	pair<int, int> previous_genotype;
	char previous_phase = 0;
	bool previous_genotype_valid = false;
	string genotype_text;
	if (FORMAT.size() > 0)
	{
		char PHASE;
		out << '\t' << get_FORMAT();

		for (unsigned int ui=0; ui<N_indv; ui++)
		{
			if (include_indv[ui] == false)
				continue;
			out << '\t';
			for (int count=0; count<(int)FORMAT.size(); count++)
			{
				if (count == GT_idx) // (FORMAT[count] == "GT")
				{
					if (count != 0)	out << ':';
					if (include_genotype[ui] == true)
					{
						get_indv_GENOTYPE_ids(ui, genotype);
						PHASE = get_indv_PHASE(ui);
						if (!previous_genotype_valid || genotype != previous_genotype || PHASE != previous_phase)
						{
							genotype_text = header::int2str(genotype.first);
							if (!((PHASE == '|') && (genotype.second == -1)))
							{
								genotype_text += PHASE;
								genotype_text += header::int2str(genotype.second);
							}
							previous_genotype = genotype;
							previous_phase = PHASE;
							previous_genotype_valid = true;
						}
						out << genotype_text;
					}
					else
						out << "./.";
				}
				else if (count == GQ_idx) //(FORMAT[count] == "GQ")
				{
					if (count != 0)	out << ':';
					out << header::double2str(get_indv_GQUALITY(ui));
				}
				else if (count == DP_idx) // (FORMAT[count] == "DP")
				{
					if (count != 0)	out << ':';
					out << header::int2str(get_indv_DEPTH(ui));
				}
				else if (count == FT_idx) // (FORMAT[count] == "FT")
				{
					if (count != 0)	out << ':';
					get_indv_GFILTER(ui, GFILTER_tmp);
					out << GFILTER_tmp;
				}
				else
				{	// Unknown FORMAT so just replicate original output
					if (count != 0)	out << ':';
					read_indv_generic_entry(ui, FORMAT[count], GFILTER_tmp);
					out << GFILTER_tmp;
				}
			}
		}
	}
	out << '\n';
}

// Output VCF entry to output stream in binary
void vcf_entry::print_bcf(BGZF* out, const set<string> &INFO_to_keep, bool keep_all_INFO)
{
	if (fully_parsed == false)
		parse_full_entry();

	if (parsed_FORMAT_binary == false)
		parse_FORMAT();

	vector<char> out_vector, tmp_vector;
	out_vector.resize(8*sizeof(int32_t));
	int vector_pos = 2*sizeof(uint32_t);
	string tmp_string;
	int index;
	vector<string> filter_vector;
	vector<pair< string, string > > tmp_info;

	tmp_string = get_CHROM();
	if (tmp_string == "." or tmp_string == " " or tmp_string == "")
		LOG.error("CHROM value must be defined for all entries.");

	if (entry_header.CONTIG_reverse_map.find(tmp_string) == entry_header.CONTIG_reverse_map.end() )
		LOG.error("CHROM value " + tmp_string + " is not defined on contig dictionary.");

	int32_t chrom = (int32_t)entry_header.CONTIG_reverse_map[tmp_string];
	memcpy(&out_vector[vector_pos], &chrom, sizeof(chrom));
	vector_pos += sizeof(chrom);

	get_POS_binary(tmp_vector);
	memcpy(&out_vector[vector_pos], &tmp_vector[0], tmp_vector.size());
	vector_pos += tmp_vector.size();
	tmp_vector.resize(0);

	get_rlen(tmp_vector);
	memcpy(&out_vector[vector_pos], &tmp_vector[0], tmp_vector.size());
	vector_pos += tmp_vector.size();
	tmp_vector.resize(0);

	get_QUAL_binary(tmp_vector);
	memcpy(&out_vector[vector_pos], &tmp_vector[0], tmp_vector.size());
	vector_pos += tmp_vector.size();
	tmp_vector.resize(0);

	get_ID_binary(tmp_vector);
	out_vector.insert(out_vector.end(), tmp_vector.begin(), tmp_vector.end());
	tmp_vector.resize(0);

	get_ALLELES_binary(tmp_vector);
	out_vector.insert(out_vector.end(), tmp_vector.begin(), tmp_vector.end());
	tmp_vector.resize(0);

	get_FILTER_vector(filter_vector);
	if (filter_vector.empty())
		make_typed_int_vector(tmp_vector, filter_vector);
	else
	{
		vector<int> index_vector;
		for(unsigned int ui=0; ui<filter_vector.size(); ui++)
		{
			if ( entry_header.FILTER_reverse_map.find( filter_vector[ui] ) == entry_header.FILTER_reverse_map.end() )
				LOG.one_off_warning("FILTER value " + filter_vector[ui] + " is not defined in the header and will not be encoded.");
			else
				index_vector.push_back( entry_header.FILTER_reverse_map[ filter_vector[ui] ] );
		}
		make_typed_int_vector(tmp_vector, index_vector );
	}

	if (tmp_vector.empty())
		make_typed_int(tmp_vector, 0, true);

	out_vector.insert(out_vector.end(), tmp_vector.begin(), tmp_vector.end());

	int map_type, number;
	tmp_info = get_INFO_vector(INFO_to_keep, keep_all_INFO);

	for(unsigned int ui=0; ui<tmp_info.size(); ui++)
	{
		if (entry_header.INFO_reverse_map.find(tmp_info[ui].first) == entry_header.INFO_reverse_map.end())
		{
			LOG.one_off_warning("INFO value " + tmp_info[ui].first + " is not defined in the header and will not be encoded.");
			N_INFO_removed++;
			continue;
		}

		tmp_vector.resize(0);
		index = entry_header.INFO_reverse_map[ tmp_info[ui].first ];
		make_typed_int(tmp_vector, index, true);
		out_vector.insert(out_vector.end(), tmp_vector.begin(), tmp_vector.end());

		tmp_vector.resize(0);
		map_type = entry_header.INFO_map[ index ].Type;
		number = entry_header.INFO_map[ index ].N_entries;

		if (map_type == Integer)
			make_typed_int_vector(tmp_vector, tmp_info[ui].second, number );
		else if (map_type == Float)
			make_typed_float_vector(tmp_vector, tmp_info[ui].second, number );
		else if ( (map_type == Character) or (map_type == String) )
			make_typed_string(tmp_vector, tmp_info[ui].second, true );
		else if (map_type == Flag)
			make_typed_int(tmp_vector, 1, true );
		else
			LOG.error("Invalid type in INFO definition");

		out_vector.insert(out_vector.end(), tmp_vector.begin(), tmp_vector.end());
	}
	tmp_vector.resize(0);
	uint32_t l_shared = (uint32_t)out_vector.size() - (uint32_t)(2*sizeof(uint32_t));
	memcpy(&out_vector[0], &l_shared, sizeof(l_shared));

	tmp_vector.resize(0);
	get_n_allele_info(tmp_vector);
	memcpy(&out_vector[vector_pos], &tmp_vector[0], tmp_vector.size());
	vector_pos += tmp_vector.size();

	tmp_vector.resize(0);
	// The encoded FORMAT bytes are read-only here; do not duplicate the payload.
	assert(parsed_FORMAT_binary == true);
	const vector<char> &format_binary = FORMAT_binary;
	unsigned int key_size, size, type, old_pos, out_size, format_pos = 0;
	unsigned int skip_size = 0;
	for (unsigned int ui=0; ui<(FORMAT.size()-N_FORMAT_removed); ui++)
	{
		format_pos = FORMAT_positions[ui];
		old_pos = format_pos;

		get_typed_int(&format_pos, format_binary, type, size);
		get_type(&format_pos, format_binary, type, size);
		key_size = format_pos - old_pos;
		out_size = out_vector.size();
		out_vector.resize( out_size + key_size );
		memcpy(&out_vector[out_size], &format_binary[old_pos], key_size );

		skip_size = FORMAT_skip[ui];
		for (unsigned int uj=0; uj<N_indv; uj++)
		{
			if (include_indv[uj] == false)
				continue;

			format_pos = FORMAT_positions[ui]+key_size+skip_size*uj;
			out_size = out_vector.size();
			out_vector.resize( out_size + skip_size );
			if ( ((int)ui == GT_idx) and (include_genotype[ui] == false) )
			{
				for (int p = 0; p < (int)skip_size; p++)
				{
					if (p < ploidy[uj])
						out_vector[out_size] = (int8_t)0x80;
					else
						out_vector[out_size] = (int8_t)0x81;
					out_size++;
				}
			}
			else
			{
				memcpy(&out_vector[out_size], &format_binary[format_pos], skip_size);
				out_size += skip_size;
			}
		}
	}
	tmp_vector.resize(0);
	get_n_fmt_sample(tmp_vector);
	memcpy(&out_vector[vector_pos], &tmp_vector[0], tmp_vector.size());

	uint32_t l_indv = (uint32_t)out_vector.size() - l_shared - (uint32_t)(2*sizeof(uint32_t));
	memcpy(&out_vector[sizeof(l_shared)], &l_indv, sizeof(l_indv));
	bgzf_write(out, &out_vector[0], out_vector.size());
}

// Set the include_genotype flag on the basis of depth
void vcf_entry::filter_genotypes_by_depth(int min_depth, int max_depth)
{
	if (fully_parsed == false)
		parse_full_entry();

	if (DP_idx != -1)
	{	// Have depth info
		int depth;
		for (unsigned int ui=0; ui<N_indv; ui++)
		{
			if (parsed_DP[ui] == false)
				parse_genotype_entry(ui, false, false, true);
			depth = get_indv_DEPTH(ui);
			if ((depth < min_depth) || (depth > max_depth))
				include_genotype[ui] = false;
		}
	}
}

// Filter specific genotypes by quality
void vcf_entry::filter_genotypes_by_quality(double min_genotype_quality)
{
	if (fully_parsed == false)
		parse_full_entry();

	if (GQ_idx != -1)
	{	// Have quality info
		double quality;
		for (unsigned int ui=0; ui<N_indv; ui++)
		{
			if (parsed_GQ[ui] == false)
				parse_genotype_entry(ui, false, true);
			quality = get_indv_GQUALITY(ui);
			if (quality < min_genotype_quality)
				include_genotype[ui] = false;
		}
	}
}

// Exclude genotypes with a filter flag.
void vcf_entry::filter_genotypes_by_filter_status(const set<string> &filter_flags_to_remove, bool remove_all)
{
	if (fully_parsed == false)
		parse_full_entry();

	vector<string> GFILTERs;
	if (FT_idx != -1)
	{	// Have GFilter info
		for (unsigned int ui=0; ui<N_indv; ui++)
		{
			if (parsed_FT[ui] == false)
				parse_genotype_entry(ui, false, false, false, true);
			get_indv_GFILTER_vector(ui, GFILTERs);

			if (remove_all == true)
			{	// If removing all filters, only keep things with label PASS
				if (!GFILTERs.empty())
					if ((GFILTERs[0] != "PASS") && (GFILTERs[0] != "."))
						include_genotype[ui] = false;
			}
			else
			{	// Only removing specific filters
				for (unsigned int uj=0; uj<GFILTERs.size(); uj++)
					if (filter_flags_to_remove.find(GFILTERs[uj]) != filter_flags_to_remove.end())
							include_genotype[ui] = false;
			}
		}
	}
}

void vcf_entry::read_indv_generic_entry(unsigned int indv, const string &FORMAT_id, string &out)
{
	if (fully_parsed == false)
		parse_full_entry(true);

	if (parsed_FORMAT == false)
		set_FORMAT(FORMAT_str);

	out = ".";

	map<string, unsigned int>::const_iterator field = FORMAT_to_idx.find(FORMAT_id);
	if (field == FORMAT_to_idx.end())
		return;

	// Locate the requested field without copying the sample or its preceding
	// fields. A missing field stays "."; an existing empty field stays empty.
	const string &genotype = GENOTYPE_str[indv];
	string::size_type start = 0;
	for (unsigned int ui=0; ui<field->second; ui++)
	{
		const string::size_type end = genotype.find(':', start);
		if (end == string::npos)
			return;
		start = end + 1;
	}
	const string::size_type end = genotype.find(':', start);
	out.assign(genotype, start, end == string::npos ? string::npos : end-start);
}
