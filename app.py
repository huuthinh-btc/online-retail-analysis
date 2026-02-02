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
st.caption("Full EDA + Visualization + RFM Segmentation (Colab-equivalent, Big Data Demo)")

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
    df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
    df = standardize_columns(df)

    required = ["InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {missing}")

    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    raw_rows = len(df)

    # Clean
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


def safe_top_n(df, by, metric, n=10):
    if by not in df.columns or metric not in df.columns:
        return None
    return (
        df.groupby(by, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .head(n)
    )


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    if "CustomerID" not in df.columns:
        raise ValueError("Thiếu CustomerID")

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
        if r >= 4 and f <= 2:
            return "New Customers"
        if r <= 2 and f >= 4:
            return "At Risk (High F)"
        if r <= 2 and m >= 4:
            return "At Risk (High M)"
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
    ["Upload Data", "Data Quality", "EDA", "Visualization", "RFM Segmentation", "Conclusion"]
)

uploaded = st.sidebar.file_uploader("Upload Online Retail CSV", type=["csv"])

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
    c3.metric("Min date", meta["min_date"].strftime("%Y-%m-%d"))
    c4.metric("Max date", meta["max_date"].strftime("%Y-%m-%d"))
    st.dataframe(pdf.head(50), use_container_width=True)

elif page == "Data Quality":
    st.subheader("Data Quality & Schema")
    miss = (pdf.isna().mean() * 100).round(2)
    miss_df = miss.reset_index()
    miss_df.columns = ["Column", "Missing %"]
    st.dataframe(miss_df, use_container_width=True)
    st.dataframe(pdf.describe(include="all"), use_container_width=True)

elif page == "EDA":
    st.subheader("Exploratory Data Analysis")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"{pdf['Revenue'].sum():,.2f}")
    k2.metric("Orders", f"{pdf['InvoiceNo'].nunique():,}")
    k3.metric("Customers", f"{pdf['CustomerID'].nunique():,}" if "CustomerID" in pdf.columns else "N/A")
    k4.metric("Products", f"{pdf['StockCode'].nunique():,}" if "StockCode" in pdf.columns else "N/A")

    pdf["Month"] = pdf["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    mrev = pdf.groupby("Month", as_index=False)["Revenue"].sum()
    st.plotly_chart(px.line(mrev, x="Month", y="Revenue", title="Monthly Revenue"), use_container_width=True)

elif page == "Visualization":
    st.subheader("Visualization Dashboard")

    if "Country" in pdf.columns:
        top_c = safe_top_n(pdf, "Country", "Revenue", 10)
        st.plotly_chart(px.bar(top_c, x="Revenue", y="Country", orientation="h",
                               title="Top 10 Countries by Revenue"),
                        use_container_width=True)

    if "Description" in pdf.columns:
        top_p = safe_top_n(pdf, "Description", "Revenue", 15)
        st.plotly_chart(px.bar(top_p, x="Revenue", y="Description", orientation="h",
                               title="Top Products by Revenue"),
                        use_container_width=True)

    basket = pdf.groupby("InvoiceNo", as_index=False).agg(
        Items=("Quantity", "sum"),
        Lines=("InvoiceNo", "size"),
        Revenue=("Revenue", "sum"),
    )

    c1, c2 = st.columns(2)
    c1.plotly_chart(px.histogram(basket, x="Revenue", nbins=50,
                                 title="Order Revenue Distribution"),
                    use_container_width=True)
    c2.plotly_chart(px.histogram(basket, x="Lines", nbins=50,
                                 title="Lines per Order"),
                    use_container_width=True)

    c3, c4 = st.columns(2)
    c3.plotly_chart(px.box(pdf, y="UnitPrice", title="UnitPrice Boxplot"),
                    use_container_width=True)
    c4.plotly_chart(px.box(pdf, y="Quantity", title="Quantity Boxplot"),
                    use_container_width=True)

    st.plotly_chart(
        px.scatter(
            pdf.sample(min(len(pdf), 20000)),
            x="UnitPrice",
            y="Quantity",
            title="UnitPrice vs Quantity (sample)"
        ),
        use_container_width=True
    )

elif page == "RFM Segmentation":
    st.subheader("RFM Customer Segmentation")

    if st.button("Compute RFM"):
        rfm = compute_rfm(df)
        st.dataframe(rfm.head(50), use_container_width=True)

        seg = rfm.groupby("Segment", as_index=False).agg(
            Customers=("CustomerID", "count"),
            Revenue=("Monetary", "sum"),
        )

        st.plotly_chart(px.bar(seg, x="Revenue", y="Segment",
                               orientation="h", title="Revenue by Segment"),
                        use_container_width=True)

        st.plotly_chart(px.pie(seg, names="Segment", values="Customers",
                               title="Customer Distribution by Segment"),
                        use_container_width=True)

elif page == "Conclusion":
    st.subheader("Conclusion & Insights")
    st.write(
        """
        - Phân tích dữ liệu bán lẻ quy mô lớn với pipeline thống nhất.
        - EDA cho thấy doanh thu tập trung vào một số ít sản phẩm, quốc gia và khách hàng.
        - RFM segmentation hỗ trợ xác định Champions, Loyal và At Risk customers.
        """
    )
