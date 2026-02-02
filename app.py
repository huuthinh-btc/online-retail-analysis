import io
import traceback
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# =========================
# Streamlit config
# =========================
st.set_page_config(page_title="Online Retail Analysis System", page_icon="📊", layout="wide")
st.title("📊 Online Retail Analysis System")
st.caption("Pandas + RFM Customer Segmentation (Colab, conda-forge, pydantic<2)")


# =========================
# Helpers
# =========================
CANON_COLS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]

def standardize_cols_pdf(pdf: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    cols = set(pdf.columns)

    if "Invoice" in cols and "InvoiceNo" not in cols:
        rename_map["Invoice"] = "InvoiceNo"
    if "Customer ID" in cols and "CustomerID" not in cols:
        rename_map["Customer ID"] = "CustomerID"
    if "Price" in cols and "UnitPrice" not in cols:
        rename_map["Price"] = "UnitPrice"
    if "InvoiceDate" not in cols and "Invoice Date" in cols:
        rename_map["Invoice Date"] = "InvoiceDate"

    if rename_map:
        pdf = pdf.rename(columns=rename_map)

    return pdf


def load_with_pandas(file_bytes: bytes):
    """
    Robust loader:
    - pandas read CSV (stable parsing)
    - parse InvoiceDate safely
    - clean data
    - return pandas DataFrame
    """
    pdf = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
    pdf = standardize_cols_pdf(pdf)

    required = ["InvoiceNo", "Quantity", "UnitPrice", "InvoiceDate"]
    missing = [c for c in required if c not in pdf.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {missing}")

    # dtypes
    pdf["InvoiceNo"] = pdf["InvoiceNo"].astype(str)
    pdf["Quantity"] = pd.to_numeric(pdf["Quantity"], errors="coerce")
    pdf["UnitPrice"] = pd.to_numeric(pdf["UnitPrice"], errors="coerce")

    # parse InvoiceDate (format hay gặp: 12/1/2010 8:26)
    pdf["InvoiceDate"] = pd.to_datetime(
        pdf["InvoiceDate"].astype(str),
        errors="coerce",
        dayfirst=False,
        infer_datetime_format=True
    )

    # stats before clean
    raw_rows = len(pdf)

    # remove cancel invoices
    pdf = pdf[~pdf["InvoiceNo"].str.startswith("C")]

    # drop NA critical + invalid values
    pdf = pdf.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice"])
    pdf = pdf[(pdf["Quantity"] > 0) & (pdf["UnitPrice"] > 0)]

    # revenue
    pdf["Revenue"] = pdf["Quantity"] * pdf["UnitPrice"]

    cleaned_rows = len(pdf)
    dropped = raw_rows - cleaned_rows

    # return pandas DataFrame
    df = pdf.copy()

    meta = {
        "raw_rows": raw_rows,
        "cleaned_rows": cleaned_rows,
        "dropped_rows": dropped,
        "min_date": pd.to_datetime(pdf["InvoiceDate"].min()),
        "max_date": pd.to_datetime(pdf["InvoiceDate"].max()),
    }
    return df, meta


def safe_top_n(pdf: pd.DataFrame, by: str, metric: str, n=10):
    if by not in pdf.columns or metric not in pdf.columns:
        return None
    out = (
        pdf.groupby(by, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .head(n)
    )
    return out


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    if "CustomerID" not in df.columns.tolist():
        raise ValueError("Thiếu CustomerID để chạy RFM")

    ref_date = pd.to_datetime(df["InvoiceDate"].max())

    rfm = df.groupby(
        by="CustomerID",
        agg={
            "LastPurchase": pd.NamedAgg(column=("InvoiceDate"),
            "Frequency": pd.NamedAgg(column=("InvoiceNo"),
            "Monetary": pd.NamedAgg(column=("Revenue"),
        }
    ).to_pandas_df()

    rfm["LastPurchase"] = pd.to_datetime(rfm["LastPurchase"])
    rfm["Recency"] = (ref_date - rfm["LastPurchase"]).dt.days

    # Score 1..5
    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    rfm["M"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])

    rfm["RFM_Score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

    # Segments (rule-based, dễ thuyết trình)
    def segment(row):
        r, f, m = int(row["R"]), int(row["F"]), int(row["M"])
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        if r >= 4 and f >= 3:
            return "Loyal"
        if r >= 4 and f <= 2:
            return "New Customers"
        if r <= 2 and f >= 4:
            return "At Risk (High F)"
        if r <= 2 and m >= 4:
            return "At Risk (High M)"
        if r == 3 and f == 3:
            return "Potential Loyalist"
        return "Others"

    rfm["Segment"] = rfm.apply(segment, axis=1)

    return rfm.sort_values("Monetary", ascending=False)


# =========================
# Sidebar
# =========================
st.sidebar.header("Menu")
page = st.sidebar.radio(
    "Select Function:",
    ["Upload Data", "Data Quality", "EDA", "Visualization", "RFM Segmentation", "Conclusion"]
)

uploaded = st.sidebar.file_uploader("Upload Online Retail CSV", type=["csv"])

if "vdf" not in st.session_state:
    st.session_state.df = None
if "meta" not in st.session_state:
    st.session_state.meta = None


# =========================
# Load
# =========================
if uploaded:
    try:
        vdf= load_with_pandas(uploaded.getvalue())
        st.session_state.df = vdf
        st.session_state.meta = meta
        st.success("Dataset loaded successfully ✅")
        st.caption(f"Rows: {len(df):,} | Date range: {meta['min_date']} → {meta['max_date']}")
        if meta["dropped_rows"] > 0:
            st.warning(f"Đã loại {meta['dropped_rows']:,} dòng lỗi/hoàn-huỷ/giá-trị âm hoặc thiếu.")
    except Exception as e:
        st.error(f"Load error: {e}")
        st.code(traceback.format_exc())
        st.stop()

df = st.session_state.vdf
meta = st.session_state.meta
if vdf is None:
    st.info("Upload CSV ở sidebar để bắt đầu.")
    st.stop()

# sample to display quickly (still big enough for charts)
pdf = df.head(300_000).to_pandas_df()
pdf["InvoiceDate"] = pd.to_datetime(pdf["InvoiceDate"], errors="coerce")


# =========================
# Pages
# =========================
if page == "Upload Data":
    st.subheader("1) Upload Data")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows (clean)", f"{len(df):,}")
    c2.metric("Dropped rows", f"{meta['dropped_rows']:,}")
    c3.metric("Min date", str(meta["min_date"].date()))
    c4.metric("Max date", str(meta["max_date"].date()))
    st.write("Preview:")
    st.dataframe(pdf.head(50), use_container_width=True)

elif page == "Data Quality":
    st.subheader("2) Data Quality & Schema")

    cols_present = list(pdf.columns)
    st.write("**Columns detected:**")
    st.code(", ".join(cols_present))

    # Missing values
    miss = pdf.isna().mean().sort_values(ascending=False)
    miss_df = (miss * 100).round(2).reset_index()
    miss_df.columns = ["Column", "Missing_%"]
    st.write("**Missing rate (%):**")
    st.dataframe(miss_df, use_container_width=True)

    # Basic stats
    st.write("**Numeric summary (Quantity / UnitPrice / Revenue):**")
    num_cols = [c for c in ["Quantity", "UnitPrice", "Revenue"] if c in pdf.columns]
    st.dataframe(pdf[num_cols].describe().T, use_container_width=True)

    # Duplicates
    dup_inv = pdf.duplicated(subset=[c for c in ["InvoiceNo", "StockCode", "Quantity", "UnitPrice", "InvoiceDate"] if c in pdf.columns]).mean()
    st.info(f"Tỷ lệ dòng trùng theo (InvoiceNo, StockCode, Quantity, UnitPrice, InvoiceDate): **{dup_inv*100:.2f}%**")

elif page == "EDA":
    st.subheader("3) Exploratory Data Analysis (EDA)")

    # KPIs
    total_rev = float(np.nan_to_num(pdf["Revenue"].sum()))
    total_orders = int(pdf["InvoiceNo"].nunique()) if "InvoiceNo" in pdf.columns else 0
    total_customers = int(pdf["CustomerID"].nunique()) if "CustomerID" in pdf.columns else 0
    total_products = int(pdf["StockCode"].nunique()) if "StockCode" in pdf.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"{total_rev:,.2f}")
    k2.metric("Orders (unique invoices)", f"{total_orders:,}")
    k3.metric("Customers", f"{total_customers:,}")
    k4.metric("Products (StockCode)", f"{total_products:,}")

    st.divider()

    # Time series (monthly)
    pdf_ts = pdf.dropna(subset=["InvoiceDate"]).copy()
    pdf_ts["Month"] = pdf_ts["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    mrev = pdf_ts.groupby("Month", as_index=False)["Revenue"].sum().sort_values("Month")
    fig = px.line(mrev, x="Month", y="Revenue", markers=True, title="Monthly Revenue Trend")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)

    # Basket size distribution
    if "InvoiceNo" in pdf.columns:
        basket = pdf.groupby("InvoiceNo", as_index=False).agg(
            Items=("Quantity", "sum"),
            Lines=("InvoiceNo", "size"),
            Revenue=("Revenue", "sum"),
        )
        c1.plotly_chart(px.histogram(basket, x="Revenue", nbins=60, title="Order Revenue Distribution"), use_container_width=True)
        c2.plotly_chart(px.histogram(basket, x="Lines", nbins=60, title="Lines per Order Distribution"), use_container_width=True)

    st.divider()

    # Top countries
    if "Country" in pdf.columns:
        top_c = safe_top_n(pdf, "Country", "Revenue", 10)
        if top_c is not None:
            fig = px.bar(top_c, x="Revenue", y="Country", orientation="h", title="Top 10 Countries by Revenue")
            st.plotly_chart(fig, use_container_width=True)

    # Top products
    if "Description" in pdf.columns:
        top_p = safe_top_n(pdf, "Description", "Revenue", 15)
        if top_p is not None:
            fig = px.bar(top_p, x="Revenue", y="Description", orientation="h", title="Top Products by Revenue (Top 15)")
            st.plotly_chart(fig, use_container_width=True)

elif page == "Visualization":
    st.subheader("4) Visualization Dashboard")

    # Filters
    colA, colB, colC = st.columns([2, 2, 2])
    country_opt = sorted(pdf["Country"].dropna().unique().tolist()) if "Country" in pdf.columns else []
    sel_country = colA.selectbox("Filter Country (optional)", ["All"] + country_opt)

    min_d = pd.to_datetime(meta["min_date"]).date()
    max_d = pd.to_datetime(meta["max_date"]).date()
    sel_range = colB.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)

    top_n = colC.slider("Top N", 5, 30, 10)

    dfv = pdf.copy()
    if sel_country != "All" and "Country" in dfv.columns:
        dfv = dfv[dfv["Country"] == sel_country]

    # date range filter
    if isinstance(sel_range, tuple) and len(sel_range) == 2:
        start, end = pd.to_datetime(sel_range[0]), pd.to_datetime(sel_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        dfv = dfv[(dfv["InvoiceDate"] >= start) & (dfv["InvoiceDate"] <= end)]

    # Tabs
    t1, t2, t3 = st.tabs(["Revenue over time", "Top entities", "Price/Quantity"])

    with t1:
        dfv_ts = dfv.dropna(subset=["InvoiceDate"]).copy()
        dfv_ts["Day"] = dfv_ts["InvoiceDate"].dt.date
        drev = dfv_ts.groupby("Day", as_index=False)["Revenue"].sum()
        st.plotly_chart(px.line(drev, x="Day", y="Revenue", title="Daily Revenue"), use_container_width=True)

    with t2:
        c1, c2 = st.columns(2)

        if "CustomerID" in dfv.columns:
            top_cus = dfv.groupby("CustomerID", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False).head(top_n)
            c1.plotly_chart(px.bar(top_cus, x="Revenue", y="CustomerID", orientation="h", title=f"Top {top_n} Customers by Revenue"), use_container_width=True)
        else:
            c1.info("Không có CustomerID.")

        if "Description" in dfv.columns:
            top_prod = dfv.groupby("Description", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False).head(top_n)
            c2.plotly_chart(px.bar(top_prod, x="Revenue", y="Description", orientation="h", title=f"Top {top_n} Products by Revenue"), use_container_width=True)
        else:
            c2.info("Không có Description.")

        if "Country" in dfv.columns:
            top_ctry = dfv.groupby("Country", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False).head(top_n)
            st.plotly_chart(px.pie(top_ctry, names="Country", values="Revenue", title=f"Revenue share (Top {top_n} Countries)"), use_container_width=True)

    with t3:
        c1, c2 = st.columns(2)
        if "UnitPrice" in dfv.columns:
            c1.plotly_chart(px.box(dfv, y="UnitPrice", title="UnitPrice (Boxplot)"), use_container_width=True)
        if "Quantity" in dfv.columns:
            c2.plotly_chart(px.box(dfv, y="Quantity", title="Quantity (Boxplot)"), use_container_width=True)

        st.plotly_chart(px.scatter(dfv.sample(min(len(dfv), 20000)), x="UnitPrice", y="Quantity", title="UnitPrice vs Quantity (sample)"),
                        use_container_width=True)

elif page == "RFM Segmentation":
    st.subheader("5) RFM Analysis (Customer Segmentation)")

    st.write("Chạy RFM trên **Pandas** (groupby) → xuất ra pandas để hiển thị/plot.")
    if st.button("Compute RFM"):
        try:
            rfm = compute_rfm(df)

            c1, c2, c3 = st.columns(3)
            c1.metric("Customers", f"{rfm['CustomerID'].nunique():,}")
            c2.metric("Avg Recency (days)", f"{rfm['Recency'].mean():.1f}")
            c3.metric("Avg Monetary", f"{rfm['Monetary'].mean():.2f}")

            st.dataframe(rfm.head(50), use_container_width=True)

            seg = rfm.groupby("Segment", as_index=False).agg(
                Customers=("CustomerID", "count"),
                Revenue=("Monetary", "sum"),
                AvgMonetary=("Monetary", "mean"),
                AvgRecency=("Recency", "mean"),
                AvgFrequency=("Frequency", "mean"),
            ).sort_values("Revenue", ascending=False)

            st.plotly_chart(px.bar(seg, x="Revenue", y="Segment", orientation="h", title="Revenue by Segment"),
                            use_container_width=True)
            st.plotly_chart(px.pie(seg, names="Segment", values="Customers", title="Customer distribution by Segment"),
                            use_container_width=True)

            st.download_button(
                "Download RFM CSV",
                rfm.to_csv(index=False).encode("utf-8"),
                "rfm_segmentation.csv",
                "text/csv"
            )
        except Exception as e:
            st.error(f"RFM error: {e}")
            st.code(traceback.format_exc())

elif page == "Conclusion":
    st.subheader("6) Conclusion & Insights")

    st.write("### Insight gợi ý (tự động theo logic dữ liệu)")
    st.write("- Doanh thu thường tập trung vào **một số sản phẩm/country/khách hàng** → ưu tiên tồn kho & marketing theo nhóm top.")
    st.write("- Revenue theo thời gian có thể có **mùa vụ** → tối ưu chiến dịch theo tháng/ngày.")
    st.write("- Đơn hàng có **outlier Quantity/UnitPrice** → kiểm tra data quality, hoàn/huỷ, sai giá.")
    st.write("- RFM giúp xác định **Champions / Loyal / At Risk** để retarget & giữ chân.")

    st.info("Nếu muốn nâng cấp tiếp: thêm Cohort Retention + Customer Lifetime Value (CLV) + Market Basket (Apriori).")


