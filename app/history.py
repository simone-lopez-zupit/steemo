import os
import pandas as pd
from app.models import ChartDataRequest, ChartType

INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "tutto.json")
FIBONACCI_SCALE = [0, 0.5, 1, 2, 3, 5, 8, 13, 21, 34]
PROJECT_COLORS = [
    
    "#1f77b4",  # blu brillante
    "#2ca02c",  # verde intenso
    "#d62728",  # rosso vivo
    "#9467bd",  # viola
    "#8c564b",  # marrone caldo
    "#17becf",  # azzurro
    "#e377c2",  # rosa
    "#7f7f7f",  # grigio medio
    "#bcbd22",  # verde oliva
    "#aec7e8",  # blu chiaro
    "#98df8a",  # verde chiaro
    "#ffbb78",  # arancio chiaro
    "#ff9896",  # salmone
    "#c5b0d5",  # lilla
    "#c49c94",  # beige
    "#9edae5",  # azzurro polvere
    "#393b79",  # indaco scuro
    "#637939",  # verde bosco
    "#8c6d31",  # senape scura
    "#843c39",  # mattone
    "#7b4173",  # melanzana
    "#3182bd",  # azzurro cielo
    "#6baed6",  # azzurro pastello
    "#31a354",  # smeraldo
    "#74c476",  # verde menta
    "#fd8d3c",  # arancio bruciato
    "#fdd0a2",  # pesca
    "#e6550d",  # arancio scuro
    "#756bb1",  # violetto
    "#9e9ac8",  # lavanda
    "#636363",  # grigio antracite
    "#969696",  # grigio chiaro
    "#5254a3",  # blu pervinca
    "#8ca252",  # verde salvia
]

def _sort_grouped(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    if granularity == "week":
        tmp = df["group"].str.extract(r"W(?P<week>\d{2}) (?P<year>\d{4})").astype(int)
        df   = df.assign(_year=tmp["year"], _week=tmp["week"])\
                 .sort_values(["_year", "_week"])\
                 .drop(columns=["_year", "_week"])
    elif granularity == "month":
        tmp = df["group"].str.extract(r"(?P<month>\d{2})/(?P<year>\d{4})").astype(int)
        df  = df.assign(_year=tmp["year"], _month=tmp["month"])\
                .sort_values(["_year", "_month"])\
                .drop(columns=["_year", "_month"])
    else:                   
        df = df.sort_values("group")
    return df
# -------------------------------------------------

def fib_distance(true_val, est_val) -> int:
    try:
        idx_true = FIBONACCI_SCALE.index(true_val)
        idx_est  = FIBONACCI_SCALE.index(est_val)
        return abs(idx_true - idx_est)
    except ValueError:
        return 99


def prepare_chart_data(request: ChartDataRequest, df: pd.DataFrame):
    df = df[(df["created"] >= request.startDate) & (df["created"] < request.endDate)]

    if request.projects:
        df = df[df["project"].isin(request.projects)]

    df["created"] = pd.to_datetime(df["created"])

    if request.granularity == "week":
        iso = df["created"].dt.isocalendar()
        df["group"] = "W" + iso.week.astype(str).str.zfill(2) + " " + iso.year.astype(str)
    elif request.granularity == "month":
        df["group"] = df["created"].dt.strftime("%m/%Y")
    elif request.granularity == "year":
        df["group"] = df["created"].dt.strftime("%Y")

    grouped = (df.groupby("group")
                 .agg(team_total=("true_points", "sum"),
                      ai_total  =("stimated_points", "sum"))
                 .reset_index())

    return _sort_grouped(grouped, request.granularity)


def to_timechart_format(df: pd.DataFrame):
    return {
        "labels": df["group"].tolist(),
        "datasets": [
            {
                "label": "Team",
                "data": df["team_total"].tolist(),
                "borderColor": "blue",
                "backgroundColor": "blue",
                "fill": False,
            },
            {
                "label": "AI",
                "data": df["ai_total"].tolist(),
                "borderColor": "orange",
                "backgroundColor": "orange",
                "fill": False,
            },
        ],
    }

def prepare_total_bar_chart_data(request: ChartDataRequest, df: pd.DataFrame) -> pd.DataFrame:
    df = df[(df["created"] >= request.startDate) & (df["created"] <request.endDate)]

    if request.projects:
        df = df[df["project"].isin(request.projects)]

    grouped = (df.groupby("project")
                 .agg(team_total=("true_points", "sum"),
                      ai_total  =("stimated_points", "sum"))
                 .reset_index()
                 .sort_values("project"))

    return grouped


def prepare_outlier_tasks(request: ChartDataRequest, df: pd.DataFrame) -> pd.DataFrame:
    # filtro temporale
    df = df[(df["created"] >= request.startDate) & (df["created"] < request.endDate)]

    # filtro per progetto
    if request.projects:
        df = df[df["project"].isin(request.projects)]

    df = df.copy()

    # mappa valori Fibonacci → indice
    scale_map = {v: i for i, v in enumerate(FIBONACCI_SCALE)}

    idx_true = df["true_points"].map(scale_map)
    idx_est  = df["stimated_points"].map(scale_map)

    # tieni solo righe in cui entrambi i valori sono nella scala
    mask_ok = idx_true.notna() & idx_est.notna()
    df = df[mask_ok].copy()

    # distanza in passi Fibonacci
    df["fib_distance"] = (idx_true - idx_est).abs()

    # outlier = distanza > 1
    return df[df["fib_distance"] > 1]

def to_total_bar_chart_format(df: pd.DataFrame):
    labels = ["Team", "AI"]
    datasets = []

    for idx, row in df.iterrows():
        datasets.append({
            "label": row["project"],
            "data": [row["team_total"], row["ai_total"]],
            "backgroundColor": PROJECT_COLORS[idx % len(PROJECT_COLORS)],
            "stack": "totale",      
        })

    return {
        "labels": labels,
        "datasets": datasets,
    }
def prepare_scatter_data(request: ChartDataRequest, df: pd.DataFrame) -> pd.DataFrame:
   
    df = df[(df["created"] >= request.startDate) & (df["created"] < request.endDate)]

    if request.projects:
        df = df[df["project"].isin(request.projects)]

    return df.loc[:, ["issue_key", "project", "true_points", "stimated_points"]]
def to_scatter_format(df: pd.DataFrame):
    points = [
        {
            "x": float(r.true_points),
            "y": float(r.stimated_points),
            "issue": r.issue_key,
            "project": r.project,
        }
        for r in df.itertuples(index=False)
        if pd.notna(r.true_points) and pd.notna(r.stimated_points)
    ]

    ideal = [{"x": v, "y": v} for v in FIBONACCI_SCALE]

    return {
        "datasets": [
            {
                "type": "scatter",
                "label": "Stories",
                "data": points,
                "backgroundColor": "rgba(30,144,255,.6)",
                "pointRadius": 4,
            },
            {
                "type": "line",
                "label": "Ideale y = x",
                "data": ideal,
                "borderColor": "grey",
                "borderDash": [5, 5],
                "borderWidth": 1,
                "pointRadius": 0,
                "fill": False,
            },
        ]
    }
def load_df(filepath: str) -> pd.DataFrame:
    df = pd.read_json(filepath)
    df["created"] = pd.to_datetime(df["created"], errors="coerce", utc=True)
    df = df[df["created"].notna()]
    df["created"] = df["created"].dt.tz_convert(None).dt.date
    df["project"] = df["issue_key"].str.split("-").str[0]
    return df


def query_chart(request: ChartDataRequest, chartType: ChartType):
    df = load_df(INPUT_FILE)

    if chartType == ChartType.lineTimeSeries:
        grouped = prepare_chart_data(request, df)
        return to_timechart_format(grouped)

    elif chartType == ChartType.totalStacked:
        grouped = prepare_total_bar_chart_data(request, df)
        return to_total_bar_chart_format(grouped)
    
    elif chartType == ChartType.scatterAccuracy:
        data = prepare_scatter_data(request, df)
        return to_scatter_format(data)
   
    return {}

def query_outlier_tasks(request: ChartDataRequest):
    df = load_df(INPUT_FILE)
    grouped=prepare_outlier_tasks(request,df)
    payload = grouped.to_dict(orient="records")
    return payload

