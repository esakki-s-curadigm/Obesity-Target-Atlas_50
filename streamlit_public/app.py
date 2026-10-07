from __future__ import annotations

import re
from pathlib import Path
from textwrap import shorten
from typing import Any
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
SOURCE_FILES = {
    "summary": "obesity_evidence_summary.csv",
    "scores": "obesity_evidence_heatmap_scores.csv",
    "master": "obesity_target_master.csv",
    "uniprot": "uniprot_filtered.csv",
    "open_targets": "open_targets.csv",
    "gwas": "gwas_filtered.csv",
    "gwas_summary": "gwas_summary.csv",
    "pubmed": "pubmed_filtered.csv",
    "reactome": "reactome.csv",
    "gtex": "gtex_obesity_filtered.csv",
    "gtex_summary": "gtex_next_filtered.csv",
    "chembl": "chembl_filtered.csv",
}
SOURCE_LABELS = {
    "UniProt obesity annotation": "UniProt",
    "Open Targets score": "Open Targets",
    "Significant GWAS": "GWAS Catalog",
    "Prioritized PubMed": "PubMed",
    "Metabolic Reactome": "Reactome",
    "Relevant GTEx tissues": "GTEx",
    "Prioritized ChEMBL": "ChEMBL",
}
SOURCE_METRICS = list(SOURCE_LABELS)
DATA_VIEWS = [
    ("Priority summary", "summary"),
    ("UniProt", "uniprot"),
    ("Open Targets", "open_targets"),
    ("GWAS Catalog", "gwas"),
    ("PubMed", "pubmed"),
    ("Reactome", "reactome"),
    ("GTEx", "gtex"),
    ("ChEMBL", "chembl"),
    ("Integrated master", "master"),
]
VIEW_DESCRIPTIONS = {
    "summary": "One obesity-focused row per candidate gene, with key identifiers and cross-database evidence signals.",
    "uniprot": "Curated protein annotations, function, localization, disease notes, and gene identifiers.",
    "open_targets": "Target–obesity association and evidence component scores.",
    "gwas": "Prioritized obesity-trait associations, significance, variants, sample size, and study details.",
    "gwas_summary": "One-row-per-gene summary of significant obesity-related GWAS associations, top traits, variants, and study coverage.",
    "pubmed": "Gene-specific obesity literature prioritized for direct relevance and evidence type.",
    "reactome": "Metabolic pathway names, hierarchy, and biological context.",
    "gtex": "Expression records in obesity-relevant tissues, plus the per-gene tissue summary.",
    "gtex_summary": "One-row-per-gene summary of the highest obesity-relevant GTEx tissue expression and tissue coverage.",
    "chembl": "Prioritized target–compound activity and development records; activity does not establish obesity efficacy.",
    "master": "Wide source-consolidated master table. Scroll horizontally to inspect all fields.",
}
DATASET_KEYS = {
    "summary": "summary",
    "uniprot": "uniprot",
    "open_targets": "open_targets",
    "gwas": "gwas",
    "pubmed": "pubmed",
    "reactome": "reactome",
    "gtex": "gtex",
    "chembl": "chembl",
    "master": "master",
}


st.set_page_config(
    page_title="Obesity Target Evidence Atlas",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {color-scheme:light; --atlas-ink:#172c28; --atlas-soft:#435a54;
        --atlas-muted:#71827d; --atlas-line:#e3ebe7; --atlas-paper:#f5f8f5;
        --atlas-green:#1e7964; --atlas-dark:#145b4d; --atlas-mint:#e9f4ef;}
      .stApp {background:var(--atlas-paper); color:var(--atlas-ink);}
      [data-testid="stSidebar"] {display:none;}
      [data-testid="stHeader"] {background:transparent;}
      .block-container {max-width:1440px; padding-top:1rem; padding-bottom:2rem;}
      .atlas-header {display:flex;justify-content:space-between;align-items:center;
        background:#fff;border:1px solid var(--atlas-line);border-radius:14px;
        padding:12px 18px;margin-bottom:24px;}
      .atlas-brand {display:flex;align-items:center;gap:11px;color:var(--atlas-ink);}
      .atlas-mark {width:38px;height:38px;border-radius:12px;display:grid;
        place-items:center;background:var(--atlas-green);color:#fff;font-weight:800;}
      .atlas-brand b,.atlas-brand small {display:block;}
      .atlas-brand small {color:var(--atlas-muted);font-size:11px;margin-top:2px;}
      .atlas-meta {color:var(--atlas-soft);font-size:12px;}
      .atlas-hero {display:flex;justify-content:space-between;align-items:flex-end;
        gap:18px;padding:15px 0 20px;}
      .atlas-eyebrow {color:var(--atlas-green);font-size:10px;font-weight:700;
        letter-spacing:1.65px;margin:0 0 9px;}
      .atlas-hero h1 {font-size:clamp(32px,4vw,50px);line-height:1.1;
        letter-spacing:-.04em;margin:0;color:var(--atlas-ink);}
      .atlas-hero h1 em {color:var(--atlas-green);font-style:normal;}
      .atlas-copy {color:var(--atlas-muted);font-size:14px;line-height:1.7;
        max-width:640px;margin:13px 0 0;}
      .atlas-chip {padding:12px 16px;border:1px solid #dbe8e1;background:#edf5f0;
        border-radius:12px;min-width:190px;}
      .atlas-chip small,.atlas-chip b {display:block;}
      .atlas-chip small {color:var(--atlas-muted);font-size:9px;font-weight:700;
        letter-spacing:1.2px;}
      .atlas-chip b {font-size:13px;margin-top:5px;}
      [data-testid="stMetric"] {background:#fff;border:1px solid var(--atlas-line);
        border-radius:12px;padding:14px 17px;box-shadow:0 8px 24px #2444390a;}
      [data-testid="stMetricLabel"] {color:var(--atlas-muted);}
      [data-testid="stMetricValue"] {color:var(--atlas-ink);}
      .atlas-panel {background:#fff;border:1px solid var(--atlas-line);
        border-radius:15px;padding:20px 22px;box-shadow:0 12px 35px #2444390a;
        margin:14px 0;}
      .atlas-panel h2 {font-size:21px;letter-spacing:-.035em;margin:0;color:var(--atlas-ink);}
      .atlas-panel p {color:var(--atlas-muted);font-size:11px;line-height:1.6;}
      .atlas-caveat {padding:11px 13px;border:1px solid var(--atlas-line);
        border-radius:9px;background:#f8fbf9;color:var(--atlas-soft);
        font-size:11px;line-height:1.65;margin:12px 0 2px;}
      .atlas-filter-panel {background:#fff;border:1px solid var(--atlas-line);
        border-radius:12px;padding:13px 16px;margin:16px 0 12px;}
      .atlas-view-heading {color:var(--atlas-green);font-size:10px;font-weight:700;
        letter-spacing:1.5px;margin:20px 0 5px;}
      [data-testid="stRadio"] > div {gap:5px;}
      [data-testid="stRadio"] label {border:1px solid var(--atlas-line);
        border-radius:8px;padding:7px 10px;background:#fff;color:var(--atlas-soft);
        font-size:11px;}
      [data-testid="stRadio"] label:has(input:checked) {background:var(--atlas-mint);
        border-color:#b8d7c8;color:var(--atlas-dark);font-weight:700;}
      [data-testid="stRadio"] input[type="radio"] {accent-color:var(--atlas-green);}
      [data-baseweb="tag"] {background:#e9f4ef!important;color:#145b4d!important;}
      [data-baseweb="tag"] span {color:#145b4d!important;}
      [data-baseweb="tag"] button {color:#145b4d!important;}
      [data-baseweb="input"] {background:#fff!important;}
      [data-testid="stDataFrame"] {border:1px solid var(--atlas-line);border-radius:9px;}
      div.stButton > button, div.stDownloadButton > button {
        border-radius:8px;font-size:11px;font-weight:700;}
      div.stDownloadButton > button {background:var(--atlas-dark);color:#fff;}
      div.stDownloadButton > button:hover {background:#0f493e;color:#fff;}
      @media (max-width:650px) {
        .atlas-header {padding:10px 12px;margin-bottom:14px;}
        .atlas-meta {font-size:10px;text-align:right;}
        .atlas-hero {padding-top:8px;}
        .atlas-chip {display:none;}
        .atlas-panel {padding:14px;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading curated evidence tables…")
def load_dataset(key: str) -> pd.DataFrame:
    filename = SOURCE_FILES[key]
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing curated app dataset: {path.name}. "
            "Rebuild the Streamlit package before deploying."
        )
    return pd.read_csv(path, low_memory=False)


def filtered_frame(
    frame: pd.DataFrame, gene: str, query: str
) -> pd.DataFrame:
    result = frame
    if gene and "Gene" in result.columns:
        result = result.loc[result["Gene"].astype(str) == gene]
    query = query.strip().casefold()
    if query:
        mask = result.astype("string").apply(
            lambda column: column.str.casefold().str.contains(
                query, regex=False, na=False
            )
        ).any(axis=1)
        result = result.loc[mask]
    return result.copy()


def source_score_table(summary: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    if scores.empty:
        return scores
    return scores.loc[scores["Gene"].isin(summary["Gene"])].copy()


def _selected_gene_from_chart(chart_event: Any) -> str:
    selection = getattr(chart_event, "selection", None)
    points = getattr(selection, "points", []) if selection is not None else []
    if points:
        point = points[0]
        return str(point.get("y", point.get("customdata", ""))).strip()
    return ""


def render_overview_charts(
    summary: pd.DataFrame,
    scores: pd.DataFrame,
    top_n: int,
    sort_mode: str,
    visible_sources: list[str],
) -> str:
    ordered = summary.copy()
    if sort_mode == "Alphabetical":
        ordered = ordered.sort_values("Gene", kind="stable")
    elif sort_mode == "Evidence domains":
        ordered = ordered.sort_values(
            ["Obesity_Evidence_Domain_Count", "Relative_Evidence_Index", "Gene"],
            ascending=[False, False, True],
            kind="stable",
        )
    else:
        ordered = ordered.sort_values(
            ["Relative_Evidence_Index", "Obesity_Evidence_Domain_Count", "Gene"],
            ascending=[False, False, True],
            kind="stable",
        )

    chart_genes = ordered.head(top_n)
    hover_cols = [
        column
        for column in [
            "Protein",
            "Obesity_Evidence_Domain_Count",
            "GWAS_Significant_Association_Count",
            "PubMed_Prioritized_Paper_Count",
        ]
        if column in chart_genes.columns
    ]
    bar = px.bar(
        chart_genes.sort_values("Relative_Evidence_Index", ascending=True),
        x="Relative_Evidence_Index",
        y="Gene",
        orientation="h",
        color="Obesity_Evidence_Domain_Count",
        color_continuous_scale=[
    "#e9f4ef",
    "#afd5bb",
    "#529b71",
    "#1e7964",
    "#2f7fae",
    "#174a6e",
],
        range_x=[0, 1],
        custom_data=hover_cols,
        labels={
            "Relative_Evidence_Index": "Relative evidence index",
            "Obesity_Evidence_Domain_Count": "Evidence domains",
        },
        title=f"Top {min(top_n, len(chart_genes))} candidates",
    )
    bar.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>Relative index: %{x:.3f}<br>"
            "Evidence domains: %{customdata[1]}/7<br>"
            "Significant GWAS: %{customdata[2]}<br>"
            "Prioritized papers: %{customdata[3]}<extra></extra>"
        ),
        marker_line_width=0,
    )
    bar.update_layout(
        height=max(350, len(chart_genes) * 31),
        margin=dict(l=12, r=12, t=48, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#fbfdfb",
        font=dict(color="#435a54", family="Segoe UI, sans-serif", size=11),
        coloraxis_showscale=False,
        clickmode="event+select",
        dragmode="select",
    )
    bar_event = st.plotly_chart(
        bar,
        width="stretch",
        key="candidate_rank_chart",
        on_select="rerun",
        selection_mode="points",
    )

    selected_scores = source_score_table(ordered, scores)
    visible_sources = [
        source for source in visible_sources if source in selected_scores.columns
    ]
    if selected_scores.empty or not visible_sources:
        st.info("Select at least one evidence source to draw the evidence heatmap.")
        return _selected_gene_from_chart(bar_event)

    selected_scores = selected_scores.set_index("Gene")[visible_sources]
    selected_scores = selected_scores.reindex(ordered["Gene"].tolist())
    selected_scores = selected_scores.dropna(how="all")
    heat_event = None
    with st.expander("Explore the interactive all-gene evidence heatmap"):
        heatmap = go.Figure(
            data=go.Heatmap(
                z=selected_scores.to_numpy(dtype=float),
                x=[SOURCE_LABELS.get(column, column) for column in visible_sources],
                y=selected_scores.index.tolist(),
                zmin=0,
                zmax=1,
                colorscale=[
    [0.0, "#f1f7f3"],
    [0.2, "#d7ebdd"],
    [0.4, "#afd5bb"], 
    [0.6, "#7fbb94"],
    [0.75, "#1e7964"],
    [0.9, "#2f7fae"],
    [1.0, "#174a6e"],
],
                colorbar=dict(title="Relative<br>signal"),
                hovertemplate=(
                    "<b>%{y}</b><br>%{x}<br>"
                    "Source-normalized signal: %{z:.0%}<extra></extra>"
                ),
            )
        )
        heatmap.update_layout(
            title="Interactive all-gene evidence heatmap",
            height=max(600, len(selected_scores) * 23),
            margin=dict(l=15, r=15, t=50, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#fbfdfb",
            font=dict(color="#435a54", family="Segoe UI, sans-serif", size=10),
            xaxis=dict(tickangle=-25, side="bottom", fixedrange=True),
            yaxis=dict(autorange="reversed", fixedrange=True),
            clickmode="event+select",
            dragmode="select",
        )
        heat_event = st.plotly_chart(
            heatmap,
            width="stretch",
            key="all_gene_heatmap",
            on_select="rerun",
            selection_mode="points",
        )
    return _selected_gene_from_chart(heat_event) or _selected_gene_from_chart(bar_event)


def reset_table_page() -> None:
    st.session_state["table_page"] = 1


def clear_filters() -> None:
    st.session_state["search_query"] = ""
    st.session_state["focus_gene"] = "All genes"
    st.session_state["table_page"] = 1


def change_table_page(delta: int) -> None:
    st.session_state["table_page"] = max(
        1, st.session_state.get("table_page", 1) + delta
    )


def format_p_value_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    parts = []
    for item in str(value).split("|"):
        item = item.strip()
        match = re.fullmatch(
            r"([<>]=?)?\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
            item,
        )
        if match:
            try:
                item = f"{match.group(1) or ''}{float(match.group(2)):.2e}"
            except (OverflowError, ValueError):
                pass
        parts.append(item)
    return " | ".join(parts)


def p_value_formatters(frame: pd.DataFrame) -> dict[str, Any]:
    formatters: dict[str, Any] = {}
    for column in frame.columns:
        if "p_value" not in str(column).casefold():
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            formatters[column] = lambda value: (
                "" if pd.isna(value) else f"{value:.2e}"
            )
    return formatters


def function_points(value: Any) -> list[tuple[str, list[str]]]:
    if pd.isna(value):
        return []

    points: dict[str, tuple[str, list[str]]] = {}
    for raw_point in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", str(value).strip()):
        point = raw_point.strip()
        if not point:
            continue
        pmids = list(dict.fromkeys(re.findall(r"\bPubMed:(\d+)\b", point)))
        text = re.sub(r"\(?\s*PubMed:\d+(?:,\s*PubMed:\d+)*\s*\)?", "", point)
        text = re.sub(r"\s+([,.;:])", r"\1", text).strip(" ,;")
        if not text:
            continue
        normalized = re.sub(r"[^a-z0-9]+", "", text.casefold())
        if normalized in points:
            existing_text, existing_pmids = points[normalized]
            points[normalized] = (
                existing_text,
                list(dict.fromkeys(existing_pmids + pmids)),
            )
        else:
            points[normalized] = (text, pmids)
    return list(points.values())


def compact_function(value: Any, max_point_chars: int = 100) -> str:
    compact_points = []
    for text, pmids in function_points(value):
        preview = shorten(text, width=max_point_chars, placeholder="…")
        if pmids:
            pmid_preview = ", ".join(pmids[:2])
            if len(pmids) > 2:
                pmid_preview += f", +{len(pmids) - 2}"
            preview = f"{preview} [PMID: {pmid_preview}]"
        compact_points.append(preview)
    return " · ".join(compact_points)


def is_function_annotation(column: str) -> bool:
    return column.casefold() in {"function", "uniprotevidence_function"}


def identifier_url(column: str, value: Any) -> str | None:
    if pd.isna(value):
        return None
    identifier = str(value).strip()
    column_name = column.casefold()
    if not identifier or "|" in identifier:
        return None

    if "ensembl" in column_name and "id" in column_name:
        if re.fullmatch(r"ENS[A-Z]*\d{11}", identifier):
            return f"https://www.ensembl.org/id/{identifier}"
    elif "uniprot" in column_name and "id" in column_name:
        if re.fullmatch(
            r"(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|"
            r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9])",
            identifier,
        ):
            return f"https://www.uniprot.org/uniprotkb/{identifier}"
    elif "ncbi_gene_id" in column_name:
        if identifier.isdigit():
            return f"https://www.ncbi.nlm.nih.gov/gene/{identifier}"
    elif "chembl" in column_name and "target" in column_name and "id" in column_name:
        if re.fullmatch(r"CHEMBL\d+", identifier):
            return f"https://www.ebi.ac.uk/chembl/target_report_card/{identifier}"
    elif "compound_id" in column_name and re.fullmatch(r"CHEMBL\d+", identifier):
        return f"https://www.ebi.ac.uk/chembl/molecule_report_card/{identifier}/"
    elif "pmid" in column_name or "pubmed_id" in column_name:
        identifier = re.sub(r"\.0+$", "", identifier)
        if identifier.isdigit():
            return f"https://pubmed.ncbi.nlm.nih.gov/{identifier}"
    elif "rsid" in column_name or (
        "variant" in column_name and re.fullmatch(r"rs\d+", identifier)
    ):
        if re.fullmatch(r"rs\d+", identifier):
            return f"https://www.ncbi.nlm.nih.gov/snp/{identifier}"
    elif "study_id" in column_name and re.fullmatch(r"GCST\d+", identifier):
        return f"https://www.ebi.ac.uk/gwas/studies/{identifier}"
    elif "efo_id" in column_name:
        match = re.fullmatch(r"(EFO|OBA)_(\d+)", identifier)
        if match:
            ontology = "efo" if match.group(1) == "EFO" else "oba"
            return (
                f"https://www.ebi.ac.uk/ols4/ontologies/{ontology}/classes"
                f"?obo_id={identifier}#{identifier}"
            )
    elif "reactome_id" in column_name and re.fullmatch(
        r"R-[A-Z]+-\d+", identifier
    ):
        return f"https://reactome.org/content/detail/{identifier}"
    elif "disease_id" in column_name and re.fullmatch(
        r"MONDO_\d+", identifier
    ):
        return f"https://platform.opentargets.org/disease/{identifier}"
    elif column_name == "gene" or column_name.endswith("_mapped_gene"):
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier):
            query = quote(f"{identifier}[Gene Name] AND Homo sapiens[Organism]")
            return (
                f"https://www.ncbi.nlm.nih.gov/gene/?term={query}"
                f"#{quote(identifier)}"
            )
    return None


def render_dataset_table(
    key: str, label: str, gene: str, query: str
) -> None:
    frame = load_dataset(key)
    filtered = filtered_frame(frame, gene, query)
    with st.container(border=True):
        st.markdown(f"### {label}")
        st.markdown(VIEW_DESCRIPTIONS[key])
        if filtered.empty:
            st.info("No records match the selected gene and search terms.")
            return
        count_col, page_size_col, download_col = st.columns([1.2, 0.7, 0.7])
        page_size = page_size_col.selectbox(
            "Rows per page",
            [25, 50, 100],
            index=0,
            key=f"page_size_{key}",
            on_change=reset_table_page,
        )
        page_count = max(1, (len(filtered) + page_size - 1) // page_size)
        st.session_state["table_page"] = min(
            max(st.session_state.get("table_page", 1), 1), page_count
        )
        page = st.session_state["table_page"]
        start = (page - 1) * page_size
        end = min(start + page_size, len(filtered))
        count_col.caption(
            f"{len(filtered):,} matching records from {len(frame):,} curated records · "
            f"showing {start + 1:,}–{end:,}"
        )
        download_col.download_button(
            f"Download {label} CSV",
            data=filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}_{gene or 'all_genes'}_filtered.csv",
            mime="text/csv",
            key=f"download_{key}",
            width="stretch",
        )
        page_data = filtered.iloc[start:end].copy()
        raw_page_data = page_data.copy()
        function_columns = [
            column for column in page_data.columns if is_function_annotation(column)
        ]
        duplicate_function_column = (
            "Function" in raw_page_data.columns
            and "UniProtEvidence_Function" in raw_page_data.columns
            and raw_page_data["Function"].fillna("").equals(
                raw_page_data["UniProtEvidence_Function"].fillna("")
            )
        )
        for column in function_columns:
            page_data[column] = page_data[column].map(compact_function)
        if duplicate_function_column:
            page_data = page_data.drop(columns=["UniProtEvidence_Function"])
            function_columns.remove("UniProtEvidence_Function")
        table_formatters = p_value_formatters(page_data)
        link_columns: dict[str, Any] = {}
        for column in page_data.columns:
            if "p_value" in str(column).casefold() and not pd.api.types.is_numeric_dtype(
                page_data[column]
            ):
                page_data[column] = page_data[column].map(format_p_value_text)
            if any(
                term in str(column).casefold()
                for term in (
                    "ensembl",
                    "uniprot",
                    "ncbi_gene_id",
                    "chembl",
                    "compound_id",
                    "pmid",
                    "pubmed_id",
                    "rsid",
                    "variant",
                    "study_id",
                    "efo_id",
                    "reactome_id",
                    "disease_id",
                )
            ) or str(column).casefold() in {"gene", "mapped_gene"}:
                urls = page_data[column].map(
                    lambda value, name=column: identifier_url(name, value)
                )
                non_empty = page_data[column].map(
                    lambda value: pd.notna(value) and bool(str(value).strip())
                )
                if non_empty.any() and urls[non_empty].notna().all():
                    link_columns[column] = st.column_config.LinkColumn(
                        column,
                        display_text=r".*(?:/|#)([^/?#]+)$",
                        help="Open this identifier in its source database.",
                    )
                    page_data[column] = urls
        table_event = st.dataframe(
            page_data.style.format(table_formatters, na_rep=""),
            column_config=link_columns,
            hide_index=True,
            width="stretch",
            height=min(560, 135 + page_size * 34),
            key=f"table_{key}",
            on_select="rerun" if function_columns else "ignore",
            selection_mode="single-row" if function_columns else "multi-row",
        )
        if function_columns:
            st.caption("Select a row to inspect full Function statements and citations.")
        if function_columns and table_event.selection.rows:
            selected_row = raw_page_data.iloc[table_event.selection.rows[0]]
            selected_gene = str(selected_row.get("Gene", "selected gene"))
            detail_points: dict[str, tuple[str, list[str]]] = {}
            for column in function_columns:
                for text, pmids in function_points(selected_row.get(column)):
                    normalized = re.sub(r"[^a-z0-9]+", "", text.casefold())
                    if normalized in detail_points:
                        existing_text, existing_pmids = detail_points[normalized]
                        detail_points[normalized] = (
                            existing_text,
                            list(dict.fromkeys(existing_pmids + pmids)),
                        )
                    else:
                        detail_points[normalized] = (text, pmids)
            if detail_points:
                st.markdown(f"#### Function details — {selected_gene}")
                st.caption(
                    "Distinct full statements from the source annotation. "
                    "PubMed references are linked where supplied by that source."
                )
                for text, pmids in detail_points.values():
                    st.markdown(f"- {text}")
                    if pmids:
                        sources = " · ".join(
                            f"[PMID:{pmid}]({identifier_url('PMID', pmid)})"
                            for pmid in pmids
                        )
                        st.markdown(f"  Sources: {sources}")
        previous_col, page_col, next_col = st.columns([1, 1, 1])
        with previous_col:
            st.button(
                "← Previous",
                disabled=page <= 1,
                on_click=change_table_page,
                args=(-1,),
                key=f"previous_{key}",
            )
        with page_col:
            st.caption(f"Page {page} of {page_count}")
        with next_col:
            st.button(
                "Next →",
                disabled=page >= page_count,
                on_click=change_table_page,
                args=(1,),
                key=f"next_{key}",
            )


def render_static_chart_downloads() -> None:
    with st.expander("Download publication-ready PNG charts"):
        first, second = st.columns(2)
        chart_files = [
            (
                first,
                "Top-10 prioritization chart",
                "top10_obesity_gene_prioritization.png",
            ),
            (second, "50-gene evidence heatmap", "obesity_evidence_heatmap.png"),
        ]
        for column, label, filename in chart_files:
            image_path = APP_DIR / "assets" / filename
            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Missing chart image {filename}; rebuild the Streamlit package."
                )
            column.download_button(
                f"Download {label}",
                data=image_path.read_bytes(),
                file_name=filename,
                mime="image/png",
                key=f"download_image_{filename}",
                width="stretch",
            )


def main() -> None:
    summary = load_dataset("summary").sort_values(
        ["Relative_Evidence_Index", "Gene"],
        ascending=[False, True],
        kind="stable",
    )
    scores = load_dataset("scores")
    st.markdown(
        """
        <header class="atlas-header">
          <div class="atlas-brand"><span class="atlas-mark">OA</span><span>
            <b>Obesity Target</b><small>Evidence Atlas</small></span></div>
          <div class="atlas-meta">● &nbsp;50 candidate genes &nbsp; | &nbsp;7 evidence sources</div>
        </header>
        <section class="atlas-hero">
          <div><p class="atlas-eyebrow">MULTI-SOURCE TARGET REVIEW</p>
            <h1>Explore obesity evidence,<br><em>gene by gene.</em></h1>
            <p class="atlas-copy">Search, filter, and compare curated summaries with
            database-level records. Keep the signal in view, and inspect the
            underlying evidence when needed.</p></div>
          <div class="atlas-chip"><small>DATA SNAPSHOT</small>
            <b>50 genes · 7 sources</b></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="atlas-eyebrow">PRIORITIZATION OVERVIEW</p>'
        '<h2 style="margin:0;color:#172c28">Evidence landscape</h2>'
        '<p style="margin:5px 0 12px;color:#71827d;font-size:11px">'
        "Hover for evidence details · use the controls to change ranking and sources · "
        "focus a gene below.</p>",
        unsafe_allow_html=True,
    )
    controls_col1, controls_col2 = st.columns([0.75, 1.5])
    with controls_col1:
        top_n = st.radio(
            "Genes in ranking",
            [10, 20, 50],
            horizontal=True,
            index=0,
            format_func=lambda value: f"Top {value}" if value < 50 else "All 50",
        )
    with controls_col2:
        sort_mode = st.selectbox(
            "Sort all-gene heatmap",
            ["Evidence index", "Evidence domains", "Alphabetical"],
            key="heatmap_sort_mode",
        )
    available_sources = [
        source for source in SOURCE_METRICS if source in scores.columns
    ]
    visible_sources = st.multiselect(
        "Evidence sources shown",
        options=available_sources,
        default=available_sources,
        format_func=lambda source: SOURCE_LABELS[source],
        key="visible_heatmap_sources",
    )
    clicked_gene = render_overview_charts(
        summary, scores, top_n, sort_mode, visible_sources
    )
    render_static_chart_downloads()
    valid_genes = set(summary["Gene"].astype(str))
    if clicked_gene in valid_genes and clicked_gene != st.session_state.get(
        "focus_gene", "All genes"
    ):
        st.session_state["focus_gene"] = clicked_gene
        st.session_state["search_query"] = ""
        st.session_state["table_page"] = 1

    st.markdown(
        """
        <div class="atlas-caveat"><b>Interpretation:</b> Relative evidence scores
        are normalized within each source. GTEx expression and Reactome pathways
        provide biological context; ChEMBL activity does not establish obesity
        efficacy. Inspect source records before drawing conclusions.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            '<p class="atlas-eyebrow">SEARCH AND FILTER</p>',
            unsafe_allow_html=True,
        )
        search_col, gene_col, clear_col = st.columns([1.2, 0.75, 0.3])
        query = search_col.text_input(
            "Search genes and evidence",
            placeholder="Try MC4R, BMI, leptin, adipose…",
            key="search_query",
            on_change=reset_table_page,
        )
        gene_choice = gene_col.selectbox(
            "Focus gene",
            ["All genes"] + sorted(summary["Gene"].astype(str).unique()),
            key="focus_gene",
            on_change=reset_table_page,
        )
        clear_col.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        clear_col.button("Clear filters", on_click=clear_filters, width="stretch")
    selected_gene = "" if gene_choice == "All genes" else gene_choice

    current_summary = filtered_frame(summary, selected_gene, query)
    metric_source = current_summary
    significant_total = pd.to_numeric(
        metric_source.get("GWAS_Significant_Association_Count", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0).sum()
    paper_total = pd.to_numeric(
        metric_source.get("PubMed_Prioritized_Paper_Count", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0).sum()
    compound_total = pd.to_numeric(
        metric_source.get("ChEMBL_Prioritized_Compound_Count", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0).sum()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Candidate genes", f"{len(current_summary):,}")
    col2.metric("Significant GWAS associations", f"{int(significant_total):,}")
    col3.metric("Prioritized PubMed papers", f"{int(paper_total):,}")
    col4.metric("Prioritized ChEMBL compounds", f"{int(compound_total):,}")

    st.markdown(
        '<p class="atlas-view-heading">DATABASE VIEWS</p>',
        unsafe_allow_html=True,
    )
    active_view = st.radio(
        "Database views",
        [label for label, _ in DATA_VIEWS],
        horizontal=True,
        label_visibility="collapsed",
        key="active_view",
    )
    view_key = dict((label, key) for label, key in DATA_VIEWS)[active_view]
    render_dataset_table(
        DATASET_KEYS[view_key], active_view, selected_gene, query
    )
    if view_key == "gwas":
        with st.expander("One-row-per-gene GWAS summary"):
            render_dataset_table(
                "gwas_summary", "GWAS gene summary", selected_gene, query
            )
    elif view_key == "gtex":
        with st.expander("One-row-per-gene GTEx tissue summary"):
            render_dataset_table(
                "gtex_summary", "GTEx gene summary", selected_gene, query
            )

    st.markdown(
        '<hr style="border:0;border-top:1px solid #e3ebe7;margin-top:26px">'
        '<p style="display:flex;justify-content:space-between;color:#87958f;'
        'font-size:10px"><span>Obesity Target Evidence Atlas</span>'
        '<span>Curated evidence browser · source CSV files remain unchanged</span></p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
