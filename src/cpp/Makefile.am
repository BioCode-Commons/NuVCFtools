bin_PROGRAMS = vcftools

vcftools_CPPFLAGS = $(ZLIB_CFLAGS)
vcftools_LDADD = $(ZLIB_LIBS)
vcftools_CXXFLAGS = $(AM_CXXFLAGS) -std=c++11 -pthread
vcftools_LDFLAGS = -pthread

vcftools_SOURCES = \
	bcf_entry.cpp \
	bcf_entry.h \
	bcf_entry_setters.cpp \
	bcf_file.cpp \
	bcf_file.h \
	bgzf.c \
	bgzf.h \
	dgeev.cpp \
	dgeev.h \
	entry.cpp \
	entry_filters.cpp \
	entry_getters.cpp \
	entry.h \
	entry_setters.cpp \
	gamma.cpp \
	gamma.h \
	header.cpp \
	header.h \
	khash.h \
	knetfile.c \
	knetfile.h \
	ld_bitsets.cpp \
	ld_bitsets.h \
	ld_chisq.h \
	output_log.cpp \
	output_log.h \
	parameters.cpp \
	parameters.h \
	variant_file.cpp \
	variant_file_diff.cpp \
	variant_file_filters.cpp \
	variant_file_format_convert.cpp \
	variant_file.h \
	variant_file_output.cpp \
	variant_file_ld_parallel.cpp \
	tab_field_reader.h \
	vcf_entry.cpp \
	vcf_entry.h \
	vcf_entry_setters.cpp \
	vcf_file.cpp \
	vcf_file.h \
	vcftools.cpp \
	vcftools.h

dist_man_MANS = vcftools.1

check_PROGRAMS = ld-bitsets-test
TESTS = ld-bitsets-test
ld_bitsets_test_SOURCES = tests/ld_bitsets_test.cpp ld_bitsets.cpp ld_bitsets.h

EXTRA_DIST = tests/tab_field_reader_fuzz.cpp
