#ifndef VCFTOOLS_TAB_FIELD_READER_H
#define VCFTOOLS_TAB_FIELD_READER_H

#include <string>

// Own the row so readers for different VCF files may be interleaved. The
// output mutation rules match getline(stream, value, '\t'), including EOF:
// the first read at the end clears value; reads after EOF leave it alone.
class tab_field_reader
{
    std::string row;
    std::string::size_type position;
    bool readable;
public:
    tab_field_reader() : position(0), readable(true) {}

    void reset(const std::string &text)
    {
        row.assign(text);
        position = 0;
        readable = true;
    }

    void read(std::string &value)
    {
        if (!readable)
            return;
        const std::string::size_type end = row.find('\t', position);
        if (end == std::string::npos)
        {
            value.assign(row, position, std::string::npos);
            position = row.size();
            readable = false;
        }
        else
        {
            value.assign(row, position, end-position);
            position = end+1;
        }
    }
};

#endif
