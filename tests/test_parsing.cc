// Unit tests for EBLParsing.hh (composition parsing + PSF log binning).
// Plain assert-based tests - no framework dependency, no Geant4 required.

#include "EBLParsing.hh"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

static int g_badTokens = 0;
static void countBadToken(const std::string&) { ++g_badTokens; }

static void test_parse_basic()
{
    std::map<std::string, double> el;
    EBL::ParseComposition("Al:1,C:5,H:4,O:2", el);
    assert(el.size() == 4);
    assert(el["Al"] == 1.0 && el["C"] == 5.0 && el["H"] == 4.0 && el["O"] == 2.0);
}

static void test_parse_decimal_stoichiometry()
{
    // HSQ - the case that used to truncate O to 1
    std::map<std::string, double> el;
    EBL::ParseComposition("Si:1,H:1,O:1.5", el);
    assert(el.size() == 3);
    assert(el["O"] == 1.5);
}

static void test_parse_whitespace_tolerant()
{
    std::map<std::string, double> el;
    EBL::ParseComposition(" Sn : 1 , C:8 ,H:8, O:4", el);
    assert(el.size() == 4);
    assert(el["Sn"] == 1.0 && el["O"] == 4.0);
}

static void test_parse_malformed_tokens_skipped()
{
    g_badTokens = 0;
    std::map<std::string, double> el;
    EBL::ParseComposition("Si:1,bogus,O:x,C:-2,H:2", el, &countBadToken);
    // "bogus" has no colon (silently skipped); "O:x" and "C:-2" are reported
    assert(el.size() == 2);
    assert(el.count("Si") == 1 && el.count("H") == 1);
    assert(g_badTokens == 2);
}

static void test_parse_empty()
{
    std::map<std::string, double> el;
    EBL::ParseComposition("", el);
    assert(el.empty());
}

static void test_logbin_edges()
{
    const double rmin = 0.5, rmax = 100000.0;  // 0.5 nm .. 100 um (in nm)
    const int n = 150;

    assert(EBL::LogBin(-1.0, rmin, rmax, n) == -1);      // invalid
    assert(EBL::LogBin(0.0, rmin, rmax, n) == 0);        // on-axis -> bin 0
    assert(EBL::LogBin(0.25, rmin, rmax, n) == 0);       // below min -> bin 0
    assert(EBL::LogBin(rmin, rmin, rmax, n) == 0);       // exactly min
    assert(EBL::LogBin(rmax, rmin, rmax, n) == -1);      // overflow, not clamped
    assert(EBL::LogBin(2.0 * rmax, rmin, rmax, n) == -1);
    // just below max lands in the last bin
    assert(EBL::LogBin(rmax * 0.999, rmin, rmax, n) == n - 1);
}

static void test_logbin_monotonic_and_covering()
{
    const double rmin = 0.5, rmax = 100000.0;
    const int n = 150;

    int prev = 0;
    for (double r = rmin; r < rmax; r *= 1.02) {
        const int bin = EBL::LogBin(r, rmin, rmax, n);
        assert(bin >= 0 && bin < n);
        assert(bin >= prev);  // monotonic in r
        prev = bin;
    }
    assert(prev == n - 1);  // full range covered
}

static void test_logbin_matches_boundaries()
{
    // A radius reconstructed from a bin's log-space center must map back to
    // that bin (round-trip consistency with RunAction::GetBinRadius logic)
    const double rmin = 0.5, rmax = 100000.0;
    const int n = 150;
    const double logStep = std::log(rmax / rmin) / (n - 1);

    for (int bin = 0; bin < n - 1; ++bin) {
        const double rCenter = rmin * std::exp((bin + 0.49) * logStep);
        const int back = EBL::LogBin(rCenter, rmin, rmax, n);
        assert(back == bin);
    }
}

int main()
{
    test_parse_basic();
    test_parse_decimal_stoichiometry();
    test_parse_whitespace_tolerant();
    test_parse_malformed_tokens_skipped();
    test_parse_empty();
    test_logbin_edges();
    test_logbin_monotonic_and_covering();
    test_logbin_matches_boundaries();

    std::printf("all parsing/binning tests passed\n");
    return 0;
}
