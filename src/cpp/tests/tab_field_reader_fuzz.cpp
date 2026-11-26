#include "../tab_field_reader.h"
#include <sstream>
#include <vector>
#include <stdint.h>
#include <stdlib.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    const std::string input(reinterpret_cast<const char *>(data), size);
    std::vector<std::string> expected(64, "old field"), actual(expected);
    tab_field_reader reader;
    for (size_t round=0; round<3; ++round)
    {
        const size_t offset = size ? (round*size/3) : 0;
        const std::string row = input.substr(offset);
        std::istringstream stream(row);
        reader.reset(row);
        for (size_t i=0; i<expected.size(); ++i)
        {
            std::getline(stream, expected[i], '\t');
            reader.read(actual[i]);
            if (expected[i] != actual[i])
                abort();
        }
    }
    return 0;
}
