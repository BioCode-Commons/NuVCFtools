#include "variant_file.h"
#include "ld_chisq.h"

#include <atomic>
#include <exception>
#include <memory>
#include <stdexcept>
#include <thread>
#include <unistd.h>

namespace {
// Each temporary file has one owner; workers never share streams or seek state.
class ld_spool_file
{
public:
	explicit ld_spool_file(const string &directory)
	{
		const string pattern = directory + "/vcftools-ld.XXXXXX";
		vector<char> name(pattern.begin(), pattern.end());
		name.push_back('\0');
		const int fd = mkstemp(&name[0]);
		if (fd == -1) throw runtime_error("Could not create LD worker output");
		path = &name[0];
		::close(fd);
	}
	~ld_spool_file() { remove(path.c_str()); }
	string path;
private:
	ld_spool_file(const ld_spool_file &);
	ld_spool_file &operator=(const ld_spool_file &);
};

// Frames avoid retaining a site's potentially unbounded result rows in RAM.
// Backpatching the length only seeks within this worker's private file.
class ld_frame_writer
{
public:
	explicit ld_frame_writer(const string &path)
	{
		stream.exceptions(ios::badbit | ios::failbit);
		stream.open(path.c_str(), ios::binary | ios::in | ios::out | ios::trunc);
	}
	void begin(uint64_t site)
	{
		stream.write(reinterpret_cast<const char *>(&site), sizeof(site));
		length_offset = stream.tellp();
		const uint64_t length = 0;
		stream.write(reinterpret_cast<const char *>(&length), sizeof(length));
		payload_offset = stream.tellp();
	}
	void finish()
	{
		const streampos end = stream.tellp();
		const uint64_t length = static_cast<uint64_t>(end - payload_offset);
		stream.seekp(length_offset);
		stream.write(reinterpret_cast<const char *>(&length), sizeof(length));
		stream.seekp(end);
	}
	void close() { stream.close(); }
	fstream stream;
private:
	streampos length_offset, payload_offset;
};
}

void variant_file::output_genotype_chisq_parallel(const parameters &params,
	const string &staged_file, size_t samples, double min_pval, ostream &out)
{
	const unsigned int rows = N_kept_entries - 1;
	const unsigned int workers = min(static_cast<unsigned int>(params.ld_threads), rows);
	const unsigned int skip = static_cast<unsigned int>(max(1, params.ld_snp_window_min));
	vector<unique_ptr<ld_spool_file> > files;
	for (unsigned int worker = 0; worker < workers; ++worker)
		files.emplace_back(new ld_spool_file(params.temp_dir));

	vector<int> unsorted(workers, 0);
	vector<exception_ptr> errors(workers);
	atomic<bool> cancelled(false);
	vector<thread> threads;
	threads.reserve(workers);
	try
	{
		for (unsigned int worker = 0; worker < workers; ++worker)
		{
			threads.emplace_back([&, worker]() {
				try
				{
					ifstream input;
					input.exceptions(ios::badbit | ios::failbit);
					input.open(staged_file.c_str(), ios::binary);
					ld_frame_writer result(files[worker]->path);
					ld_chisq_workspace workspace;
					vector<ld_genotype> first(samples), second(samples);
					string chromosome, other_chromosome;
					int position, other_position, alleles, other_alleles;
					// Striping balances triangular work without an input-dependent cutoff.
					for (unsigned int i = 0; i < rows && !cancelled.load(); ++i)
					{
						read_big_temp_site_header(input, chromosome, position, alleles);
						if (i % workers != worker)
						{
							input.seekg(static_cast<streamoff>(samples) * 2, ios::cur);
							continue;
						}
						read_big_temp_site_payload(input, first);
						const streampos next_site = input.tellg();
						result.begin(i);
						for (unsigned int j = i + 1; j < N_kept_entries; ++j)
						{
							if (int(j-i) > params.ld_snp_window_size) break;
							read_big_temp_site_header(input, other_chromosome, other_position, other_alleles);
							const bool decode = j >= i+skip && chromosome == other_chromosome
								&& other_position-position >= params.ld_bp_window_min
								&& other_position-position <= params.ld_bp_window_size;
							if (decode) read_big_temp_site_payload(input, second);
							else input.seekg(static_cast<streamoff>(samples) * 2, ios::cur);
							if (j < i+skip || chromosome != other_chromosome) continue;
							if (other_position < position) unsorted[worker] = 1;
							if (other_position-position < params.ld_bp_window_min) continue;
							if (other_position-position > params.ld_bp_window_size) break;
							double chisq, dof, pval;
							int individuals;
							workspace.calculate(first, second, alleles, other_alleles, chisq, dof, pval, individuals);
							if (min_pval > 0 && (pval < min_pval || pval != pval)) continue;
							result.stream << chromosome << '\t' << position << '\t' << other_position
								<< '\t' << individuals << '\t' << chisq << '\t' << dof << '\t' << pval << '\n';
						}
						result.finish();
						input.seekg(next_site);
					}
					result.close();
				}
				catch (...)
				{
					errors[worker] = current_exception();
					cancelled.store(true);
				}
			});
		}
	}
	catch (...)
	{
		cancelled.store(true);
		for (size_t i = 0; i < threads.size(); ++i) threads[i].join();
		throw;
	}
	for (size_t i = 0; i < threads.size(); ++i) threads[i].join();
	for (unsigned int worker = 0; worker < workers; ++worker)
		if (errors[worker]) rethrow_exception(errors[worker]);
	if (find(unsorted.begin(), unsorted.end(), 1) != unsorted.end())
		LOG.one_off_warning("Warning: Input is unsorted, results may not be complete.");

	vector<unique_ptr<ifstream> > inputs;
	for (unsigned int worker = 0; worker < workers; ++worker)
	{
		inputs.emplace_back(new ifstream);
		inputs.back()->exceptions(ios::badbit | ios::failbit);
		inputs.back()->open(files[worker]->path.c_str(), ios::binary);
	}
	char buffer[64 * 1024];
	for (unsigned int i = 0; i < rows; ++i)
	{
		ifstream &input = *inputs[i % workers];
		uint64_t site, remaining;
		input.read(reinterpret_cast<char *>(&site), sizeof(site));
		input.read(reinterpret_cast<char *>(&remaining), sizeof(remaining));
		if (site != i) throw runtime_error("LD worker output is out of order");
		while (remaining)
		{
			const streamsize count = static_cast<streamsize>(min<uint64_t>(remaining, sizeof(buffer)));
			input.read(buffer, count);
			out.write(buffer, count);
			if (!out) throw runtime_error("Could not write LD output");
			remaining -= count;
		}
	}
	out.flush();
	if (!out) throw runtime_error("Could not flush LD output");
}
