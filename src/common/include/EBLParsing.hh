// EBLParsing.hh - Pure-logic helpers shared by the simulation and unit tests
#ifndef EBLPARSING_HH
#define EBLPARSING_HH

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <map>
#include <sstream>
#include <string>

namespace EBL {

// Parse a resist composition string like "Al:1,C:5,H:4,O:2" (decimal counts
// allowed, e.g. HSQ "Si:1,H:1,O:1.5") into element -> count. Malformed tokens
// are skipped and reported through onBadToken (may be null).
inline void ParseComposition(const std::string& composition,
                             std::map<std::string, double>& elements,
                             void (*onBadToken)(const std::string&) = nullptr)
{
    elements.clear();

    std::stringstream ss(composition);
    std::string token;
    while (std::getline(ss, token, ',')) {
        const auto colon = token.find(':');
        if (colon == std::string::npos) continue;

        std::string element = token.substr(0, colon);
        element.erase(std::remove(element.begin(), element.end(), ' '), element.end());
        if (element.empty()) continue;

        char* parseEnd = nullptr;
        const std::string countStr = token.substr(colon + 1);
        const double count = std::strtod(countStr.c_str(), &parseEnd);
        if (parseEnd == countStr.c_str() || count <= 0.0) {
            if (onBadToken) onBadToken(token);
            continue;
        }

        elements[element] = count;
    }
}

// Logarithmic radial bin index for the PSF.
//   r <  0        -> -1 (invalid)
//   0 <= r < min  ->  0 (bin 0's area normalization uses rInner = 0, so the
//                       on-axis point-source deposits belong here)
//   r >= max      -> -1 (overflow; caller accounts for it separately -
//                       clamping into the last bin would inflate the tail)
inline int LogBin(double radius, double minRadius, double maxRadius, int numBins)
{
    if (radius < 0.0) return -1;
    if (radius < minRadius) return 0;
    if (radius >= maxRadius) return -1;

    const double logRatio = std::log(radius / minRadius) / std::log(maxRadius / minRadius);
    int bin = static_cast<int>(logRatio * (numBins - 1));

    if (bin < 0) bin = 0;
    if (bin >= numBins) bin = numBins - 1;
    return bin;
}

} // namespace EBL

#endif // EBLPARSING_HH
