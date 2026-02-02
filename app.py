import io
import traceback
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# Streamlit config
# =========================
st.set_page_config(
    page_title="Online Retail Analysis System",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Online Retail Analysis System")
st.caption("Pandas-based EDA & RFM Customer Segmentation (Big Data Demo)")

# =========================
# Helpers
# =========================
def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Invoice": "InvoiceNo",
        "Invoice Date": "InvoiceDate",
        "Customer ID": "CustomerID",
        "Price": "UnitPrice",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def load_with_pandas(file_bytes: bytes):
    """
    Unified data loading & cleaning pipeline
    Used for BOTH uploaded files and sample dataset
    """
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
    df = standardize_columns(df)

    required_cols = ["InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {missing}")

    # Type casting
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    raw_rows = len(df)

    # Cleaning
    df = df[~df["InvoiceNo"].str.startswith("C")]
    df = df.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice"])
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    meta = {
        "raw_rows": raw_rows,
        "cleaned_rows": len(df),
        "dropped_rows": raw_rows - len(df),
        "min_date": df["InvoiceDate"].min(),
        "max_date": df["InvoiceDate"].max(),
    }

    return df, meta


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    if "CustomerID" not in df.columns:
        raise ValueError("Thiếu CustomerID để chạy RFM")

    ref_date = df["InvoiceDate"].max()

    rfm = (
        df.groupby("CustomerID", as_index=False)
        .agg(
            LastPurchase=("InvoiceDate", "max"),
            Frequency=("InvoiceNo", "nunique"),
            Monetary=("Revenue", "sum"),
        )
    )

    rfm["Recency"] = (ref_date - rfm["LastPurchase"]).dt.days

    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1])
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    rfm["M"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])

    rfm["RFM_Score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

    def segment(row):
        r, f, m = int(row["R"]), int(row["F"]), int(row["M"])
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        if r >= 4 and f >= 3:
            return "Loyal"
        if r >= 4:
            return "New Customers"
        if r <= 2 and f >= 4:
            return "At Risk"
        return "Others"

    rfm["Segment"] = rfm.apply(segment, axis=1)
    return rfm.sort_values("Monetary", ascending=False)

# =========================
# Session state
# =========================
if "df" not in st.session_state:
    st.session_state.df = None
if "meta" not in st.session_state:
    st.session_state.meta = None

# =========================
# Sidebar
# =========================
st.sidebar.header("Menu")

page = st.sidebar.radio(
    "Select Function",
    ["Upload Data", "Data Quality", "EDA", "RFM Segmentation", "Conclusion"]
)

uploaded = st.sidebar.file_uploader(
    "Upload Online Retail CSV",
    type=["csv"]
)

# ---- Sample dataset button ----
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Sample Dataset")

if st.sidebar.button("Load sample: Online Retail"):
    try:
        with open("data/online_retail_sample.csv", "rb") as f:
            df, meta = load_with_pandas(f.read())

        st.session_state.df = df
        st.session_state.meta = meta

        st.success("Sample dataset loaded successfully ✅")
    except Exception as e:
        st.error(f"Cannot load sample dataset: {e}")

# =========================
# Load uploaded data
# =========================
if uploaded is not None:
    try:
        df, meta = load_with_pandas(uploaded.getvalue())
        st.session_state.df = df
        st.session_state.meta = meta
        st.success("Dataset uploaded successfully ✅")
    except Exception as e:
        st.error(f"Upload error: {e}")
        st.code(traceback.format_exc())
        st.stop()

# =========================
# Use data
# =========================
df = st.session_state.df
meta = st.session_state.meta

if df is None:
    st.info("Upload CSV hoặc bấm **Load sample: Online Retail** để bắt đầu.")
    st.stop()

pdf = df.head(300_000)

# =========================
# Pages
# =========================
if page == "Upload Data":
    st.subheader("Dataset Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Dropped rows", f"{meta['dropped_rows']:,}")
    c3.metric("Min date", str(meta["min_date"].date()))
    c4.metric("Max date", str(meta["max_date"].date()))

    st.dataframe(pdf.head(50), use_container_width=True)

elif page == "Data Quality":
    st.subheader("Data Quality")

    miss = (pdf.isna().mean() * 100).round(2)
    miss_df = miss.reset_index()
    miss_df.columns = ["Column", "Missing %"]
    st.dataframe(miss_df, use_container_width=True)

elif page == "EDA":
    st.subheader("Exploratory Data Analysis")

    st.metric("Total Revenue", f"{pdf['Revenue'].sum():,.2f}")

    pdf["Month"] = pdf["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    mrev = pdf.groupby("Month", as_index=False)["Revenue"].sum()

    st.plotly_chart(
        px.line(mrev, x="Month", y="Revenue", title="Monthly Revenue Trend"),
        use_container_width=True
    )

elif page == "RFM Segmentation":
    st.subheader("RFM Customer Segmentation")

    if st.button("Compute RFM"):
        rfm = compute_rfm(df)

        st.dataframe(rfm.head(50), use_container_width=True)

        seg = rfm.groupby("Segment", as_index=False)["Monetary"].sum()
        st.plotly_chart(
            px.bar(seg, x="Monetary", y="Segment", orientation="h",
                   title="Revenue by Customer Segment"),
            use_container_width=True
        )

elif page == "Conclusion":
    st.subheader("Conclusion & Insights")

    st.write(
        """
        - Hệ thống cho phép phân tích **Big Data bán lẻ** ngay cả khi người dùng
          **không upload dữ liệu**, thông qua **sample dataset tích hợp sẵn**.
        - Cùng một pipeline xử lý được áp dụng cho cả dữ liệu upload và dữ liệu mẫu.
        - RFM giúp xác định **Champions / Loyal / At Risk customers**
          để hỗ trợ quyết định kinh doanh.
        """
    )
