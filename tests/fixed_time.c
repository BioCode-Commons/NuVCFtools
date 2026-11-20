/* Linked ONLY into differential-test executables, never the production build.
 * Both versions see the same clock, including random sample-selection seeds.
 * This allows byte comparisons of complete logs without deleting runtime lines.
 */
#include <time.h>

time_t time(time_t *result)
{
    const time_t epoch = (time_t)1700000000;
    if (result != 0)
        *result = epoch;
    return epoch;
}
