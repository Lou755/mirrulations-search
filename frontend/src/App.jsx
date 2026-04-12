import { useMemo, useState, useEffect } from "react";
import { Routes, Route, Navigate, Link } from "react-router-dom";
import Login from "./pages/Login";
import Home from "./pages/Home";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import Collections from "./pages/Collections";
import "./styles/app.css";
import { searchDockets, getAuthStatus } from "./api/searchApi";
import AdvancedSidebar from "./components/AdvancedSidebar";
import SearchBar from "./components/SearchBar";
import ResultsPanel from "./components/ResultsPanel";
import { motion } from "motion/react";
import { ArrowLeftIcon, ArrowRightIcon, BooksIcon } from "@phosphor-icons/react";
import DownloadStatusModal from "./components/DownloadStatusModal";


export default function App() {
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("");
  const [results, setResults] = useState([]);
  const [advOpen, setAdvOpen] = useState(true);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [agencySearch, setAgencySearch] = useState("");
  const [selectedAgencies, setSelectedAgencies] = useState(new Set());
  const [status, setStatus] = useState(new Set());
  const [selectedCfrParts, setSelectedCfrParts] = useState({});
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [unauthorized, setUnauthorized] = useState(false);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [openDownloadStatus, setOpenDownloadStatus] = useState(null);
  /** Passed as GET /search/?sort_by= (empty = server default relevance) */
  const [searchSortBy, setSearchSortBy] = useState("");

  useEffect(() => {
    getAuthStatus().then((data) => {
      if (data.logged_in) {
        setUser({ name: data.name, email: data.email });
      }
      setAuthLoading(false);
    });
  }, []);

  const TOP_AGENCIES = [
    { code: "EPA", name: "Environmental Protection Agency" },
    { code: "HHS", name: "Health and Human Services" },
    { code: "FDA", name: "Food and Drug Administration" },
    { code: "CMS", name: "Centers for Medicare & Medicaid Services" },
    { code: "DOT", name: "Department of Transportation" },
    { code: "FCC", name: "Federal Communications Commission" },
  ];

  const agenciesToShow = useMemo(() => {
    const q = agencySearch.toLowerCase();
    return q
      ? TOP_AGENCIES.filter(
          (a) =>
            a.code.toLowerCase().includes(q) ||
            a.name.toLowerCase().includes(q)
        )
      : TOP_AGENCIES;
  }, [agencySearch]);

  const activeCount =
    (yearFrom ? 1 : 0) +
    (yearTo ? 1 : 0) +
    selectedAgencies.size +
    status.size +
    Object.values(selectedCfrParts).reduce((sum, set) => sum + set.size, 0);

  const runSearch = async (newPage = 1, sortByOverride) => {
    const sortBy = sortByOverride !== undefined ? sortByOverride : searchSortBy;
    setLoading(true);
    setHasSearched(true);
    setUnauthorized(false);

    try {
      const selectedAgencyList = Array.from(selectedAgencies);

      const selectedCfrList = Object.entries(selectedCfrParts).flatMap(
        ([title, parts]) =>
          Array.from(parts).map((part) => ({
            title: Number(title),
            part,
          }))
      );

      const data = await searchDockets(
        query,
        docType,
        selectedAgencyList,
        selectedCfrList,
        newPage,
        yearFrom,
        yearTo,
        sortBy
      );

      setResults(data.results);
      setPagination(data.pagination);
      setPage(newPage);
    } catch (err) {
      if (err.message === "UNAUTHORIZED") {
        setUnauthorized(true);
      }
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const advancedPayload = {
    yearFrom,
    yearTo,
    agencies: Array.from(selectedAgencies),
    status: Array.from(status),
  };

  const clearAdvanced = () => {
    setYearFrom("");
    setYearTo("");
    setAgencySearch("");
    setSelectedAgencies(new Set());
    setStatus(new Set());
    setSelectedCfrParts({});
  };

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />

      <Route path="/login" element={<Login />} />
      <Route
        path="/collections"
        element={
          user === null && !authLoading ? (
            <Navigate to="/login" replace />
          ) : (
            <div className="page">
              <header className="topbar">
                <Link to="/" className="brand brand-link">
                  Mirrulations
                </Link>
                <div className="topbar-right">
                  <span className="topbar-privacy">
                    <Link to="/privacy">Privacy</Link>
                  </span>
                  {user ? (
                    <div className="auth-section">
                      <span className="auth-name">{user.name}</span>
                      <Link to="/explorer" className="btn btn-primary">
                        Search
                      </Link>
                      <a href="/logout" className="btn btn-primary">
                        Log Out
                      </a>
                      <button className="btn btn-primary" onClick={() => setOpenDownloadStatus(true)}>Check Downloads</button>
                    </div>
                  ) : (
                    <a href="/login" className="btn btn-primary">
                      Log In
                    </a>
                  )}
                </div>
              </header>
              <div className="layout layout-single">
                <main className="main">
                  <Collections />
                </main>
              </div>
              {openDownloadStatus && (
              <DownloadStatusModal onClose={() => setOpenDownloadStatus(null)} />
              )}
            </div>
          )
        }
      />
      <Route
        path="/explorer"
        element={
          user === null && !authLoading ? (
            <Navigate to="/login" replace />
          ) : (
            <div className="page">
              <header className="topbar">
                <Link to="/" className="brand brand-link">
                  Mirrulations
                </Link>
                <div className="topbar-right">
                  <span className="topbar-privacy">
                    <Link to="/privacy">Privacy</Link>
                  </span>
                  {user ? (
                    <div className="auth-section">
                      <span className="auth-name">{user.name}</span>
                      <Link to="/collections" className="btn btn-primary collections-nav-btn">
                        <BooksIcon size={24} weight="duotone" />
                        My Collections
                      </Link>
                      <a href="/logout" className="btn btn-primary">
                        Log Out
                      </a>
                    </div>
                  ) : (
                    <a href="/login" className="btn btn-primary">
                      Log In
                    </a>
                  )}
                </div>
              </header>
              <div className="layout">
                <AdvancedSidebar
                  advOpen={advOpen}
                  setAdvOpen={setAdvOpen}
                  yearFrom={yearFrom}
                  setYearFrom={setYearFrom}
                  yearTo={yearTo}
                  setYearTo={setYearTo}
                  agencySearch={agencySearch}
                  setAgencySearch={setAgencySearch}
                  agenciesToShow={agenciesToShow}
                  selectedAgencies={selectedAgencies}
                  setSelectedAgencies={setSelectedAgencies}
                  docType={docType}
                  setDocType={setDocType}
                  status={status}
                  setStatus={setStatus}
                  selectedCfrParts={selectedCfrParts}
                  setSelectedCfrParts={setSelectedCfrParts}
                  clearAdvanced={clearAdvanced}
                  applyAdvanced={() => runSearch(1)}
                  activeCount={activeCount}
                />
                <main className="main">
                  <motion.h1
                    className="title"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8, duration: 0.9, ease: "easeInOut" }}
                  >
                    Mirrulations Explorer
                  </motion.h1>
                  <SearchBar
                    query={query}
                    setQuery={setQuery}
                    onSubmit={(e) => {
                      e.preventDefault();
                      runSearch(1);
                    }}
                  />
                  <div className="search-sort-row">
                    <label htmlFor="search-sort-by" className="search-sort-label">
                      Sort by
                    </label>
                    <select
                      id="search-sort-by"
                      className="search-sort-select"
                      value={searchSortBy}
                      onChange={(e) => {
                        const v = e.target.value;
                        setSearchSortBy(v);
                        if (hasSearched) {
                          runSearch(1, v);
                        }
                      }}
                    >
                      <option value="">Relevance (default)</option>
                      <option value="document_count">Total documents in docket</option>
                      <option value="comment_count">Total comments in docket</option>
                      <option value="modify_date">Last modified date</option>
                    </select>
                  </div>
                  <ResultsPanel
                    advancedPayload={advancedPayload}
                    results={results}
                    loading={loading}
                    hasSearched={hasSearched}
                    query={query}
                    unauthorized={unauthorized}
                  />
                  <div className="pagination-div">
                    <button
                      className="page-button"
                      disabled={!pagination?.hasPrev}
                      onClick={() => runSearch(page - 1)}
                    >
                      <ArrowLeftIcon color="white" size={32} />
                    </button>
                    <span className="page-info">
                      Page {pagination?.page} of {pagination?.totalPages}
                    </span>
                    <button
                      className="page-button"
                      disabled={!pagination?.hasNext}
                      onClick={() => runSearch(page + 1)}
                    >
                      <ArrowRightIcon color="white" size={32} />
                    </button>
                  </div>
                </main>
              </div>
            </div>
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
