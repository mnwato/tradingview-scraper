import pandera as pa

# L0-L4 Data Contract Definitions (Phase 620-630)

# Use Regex pattern to match all symbols for returns matrix
ReturnsSchema = pa.DataFrameSchema(columns={"^(.*)$": pa.Column(float, checks=[pa.Check.greater_than_or_equal_to(-1.0), pa.Check.less_than_or_equal_to(1.0)], regex=True)}, index=pa.Index(pa.DateTime))

# Feature Store Schema for PIT Validation
FeatureStoreSchema = pa.DataFrameSchema(
    columns={
        "recommend_all": pa.Column(float, checks=[pa.Check.in_range(-1.0, 1.0)], nullable=True),
        "recommend_ma": pa.Column(float, checks=[pa.Check.in_range(-1.0, 1.0)], nullable=True),
        "recommend_other": pa.Column(float, checks=[pa.Check.in_range(-1.0, 1.0)], nullable=True),
        "adx": pa.Column(float, checks=[pa.Check.in_range(0, 100)], nullable=True),
        "rsi": pa.Column(float, checks=[pa.Check.in_range(0, 100)], nullable=True),
    },
    index=pa.Index(pa.DateTime),
    strict=False,  # Allow other technical features
)

WeightsSchema = pa.DataFrameSchema(
    columns={
        "Symbol": pa.Column(str),
        "Weight": pa.Column(float, checks=[pa.Check.greater_than_or_equal_to(0.0), pa.Check.less_than_or_equal_to(1.0)]),
        "Net_Weight": pa.Column(float, required=False),
    },
    checks=[
        # Simplex constraint (Sum of absolute weights <= 1.0 + tolerance)
        pa.Check(lambda df: df["Weight"].sum() <= 1.05, name="simplex_sum_constraint")
    ],
)
