import { useMemo, useState } from "react";
import "./styles/app.css";
import { searchDockets } from "./api/searchApi";
import AdvancedSidebar from "./components/AdvancedSidebar";
import SearchBar from "./components/SearchBar";
import ResultsPanel from "./components/ResultsPanel";
import { motion } from "motion/react"


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
const [selectedCfrParts, setSelectedCfrParts] = useState(new Set());
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
    selectedCfrParts.size;
const runSearch = async () => {
const firstAgency = Array.from(selectedAgencies)[0] || ""
const firstCfr = Array.from(selectedCfrParts)[0] || "";
const data = await searchDockets(query, docType, firstAgency, firstCfr)
    setResults(data);
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
    setSelectedCfrParts(new Set());
  };
return (
<div className="page">
<header className="topbar">
<div className="brand">Mirrulations</div>
<button className="btn btn-primary">Log Out</button>
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
applyAdvanced={runSearch}
activeCount={activeCount}
/>
<main className="main">
<motion.h1 className="title"
initial={{ opacity: 0, y: -20 }}   
animate={{ opacity: 1, y: 0 }}     
transition={{ delay: 0.8 ,duration: 0.9, ease: "easeInOut" }}
>Mirrulations Explorer</motion.h1>
<SearchBar
query={query}
setQuery={setQuery}
onSubmit={(e) => {
              e.preventDefault();
              runSearch();
            }}
/>
<ResultsPanel
advancedPayload={advancedPayload}
results={results}
/>
</main>
</div>
</div>
  );
}