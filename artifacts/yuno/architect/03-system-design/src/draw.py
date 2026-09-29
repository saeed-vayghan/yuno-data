"""Draw the CasaMarket system-design diagrams as self-contained SVG files.

Run:  uv run --with diagrams python src/draw.py   (needs Graphviz `dot` on PATH)
Output: SVG files next to this `src/` folder. Icons are inlined, so each SVG works on its own.
"""

import base64
import re
from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import GlueDataCatalog, KinesisDataAnalytics, ManagedStreamingForKafka
from diagrams.aws.compute import ECR, EKS, Fargate
from diagrams.aws.integration import SNS, Eventbridge
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import ALB
from diagrams.aws.security import IAM, KMS, SecretsManager
from diagrams.aws.storage import S3
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage
from diagrams.onprem.analytics import Dbt, Superset
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import User, Users
from diagrams.onprem.container import Docker
from diagrams.onprem.database import Duckdb
from diagrams.onprem.workflow import Airflow
from diagrams.programming.language import Python
from diagrams.saas.alerting import Pagerduty
from diagrams.saas.chat import Slack

OUT = Path(__file__).resolve().parent.parent

FONT = "Helvetica"
GRAPH = {
    "fontname": FONT,
    "fontsize": "22",
    "bgcolor": "white",
    "pad": "0.6",
    "nodesep": "0.7",
    "ranksep": "1.0",
    "splines": "spline",
    "labelloc": "t",
}
NODE = {"fontname": FONT, "fontsize": "12"}
EDGE = {"fontname": FONT, "fontsize": "10", "color": "#5b6770"}

# Soft cluster styles (fill, border)
BLUE = {"bgcolor": "#eef4fb", "pencolor": "#8fb3de", "style": "rounded", "fontname": FONT, "fontsize": "14"}
GREEN = {"bgcolor": "#eef8f1", "pencolor": "#8cc7a0", "style": "rounded", "fontname": FONT, "fontsize": "14"}
ORANGE = {"bgcolor": "#fdf4e9", "pencolor": "#e5b07a", "style": "rounded", "fontname": FONT, "fontsize": "14"}
PURPLE = {"bgcolor": "#f4f0fb", "pencolor": "#b19ad8", "style": "rounded", "fontname": FONT, "fontsize": "14"}
GREY = {"bgcolor": "#f5f6f7", "pencolor": "#b8bec4", "style": "rounded", "fontname": FONT, "fontsize": "14"}
RED = {"bgcolor": "#fcefef", "pencolor": "#e29a9a", "style": "rounded", "fontname": FONT, "fontsize": "14"}


def e(label: str = "", color: str = "#5b6770", style: str = "solid") -> Edge:
    return Edge(label=label, color=color, style=style, fontname=FONT, fontsize="10")


DASH = "dashed"


def diagram(name: str, title: str, direction: str = "LR") -> Diagram:
    return Diagram(
        title,
        filename=str(OUT / name),
        outformat="svg",
        show=False,
        direction=direction,
        graph_attr=GRAPH,
        node_attr=NODE,
        edge_attr=EDGE,
    )


def inline_icons(svg_path: Path) -> None:
    """Replace icon file paths with base64 data URIs so the SVG is portable."""
    text = svg_path.read_text()

    def repl(match: re.Match) -> str:
        src = Path(match.group(2))
        if not src.exists():
            return match.group(0)
        data = base64.b64encode(src.read_bytes()).decode()
        return f'{match.group(1)}="data:image/png;base64,{data}"'

    text = re.sub(r'(xlink:href|href)="([^"]+\.png)"', repl, text)
    svg_path.write_text(text)


# ---------------------------------------------------------------- 01 high level
def high_level() -> None:
    with diagram("01-high-level", "CasaMarket Settlement Discrepancies: High-Level View"):
        users = Users("Ops analyst · Finance\nPSP ops · Reviewer")

        with Cluster("Run layer", graph_attr=GREY):
            run = Python("recon CLI\n(make · uv · docker compose)")

        with Cluster("Config", graph_attr=GREY):
            cfg = Storage("generator.yaml\nthresholds.yaml\nalerts.yaml")

        with Cluster("1 · Data generation", graph_attr=ORANGE):
            gen = Python("Seeded generator\n+ validation gate")
            raw = Storage("data/raw\n(CSV + FX table)")
            truth = Storage("data/truth\n(labels, not a source)")

        with Cluster("2 · Data pipeline (FR1)", graph_attr=BLUE):
            dbt = Dbt("dbt build\nstaging → marts + tests")
            db = Duckdb("casarecon.duckdb")

        with Cluster("3 · Analysis & reports (FR2, FR4)", graph_attr=GREEN):
            ana = Python("Stats · GLM\ncause labels · $ impact")
            rep = Storage("FINDINGS.md\nRECOMMENDATIONS.md\nfigures")

        with Cluster("4 · Monitoring (FR3)", graph_attr=PURPLE):
            alerts = Python("Alert evaluator\n6 rules")
            dash = Python("Streamlit dashboard\nlocalhost:8501")
            slack = Slack("Slack\n(optional, off)")

        users >> e("runs") >> run
        run >> e("generate") >> gen
        cfg >> e(style=DASH) >> gen
        gen >> raw
        gen >> e(style=DASH) >> truth
        raw >> dbt >> db
        cfg >> e("vars", style=DASH) >> dbt
        db >> e("read-only") >> ana >> rep
        truth >> e("score labels", style=DASH) >> ana
        db >> e("read-only") >> alerts
        cfg >> e(style=DASH) >> alerts
        alerts >> e("alerts.jsonl") >> dash
        alerts >> e(style=DASH) >> slack
        db >> e("read-only, per query") >> dash
        rep >> e(style=DASH) >> dash
        users >> e("explore") >> dash


# ---------------------------------------------------------------- 02 generator
def generator() -> None:
    with diagram("02-data-generation", "Detail · Data Generation & Validation"):
        spec = Storage("generator.yaml\nseed · shares · patterns")

        with Cluster("recon generate", graph_attr=ORANGE):
            fx = Python("fx.py\ndaily local_per_usd\n(capped moves)")
            rows = Python("rows.py\nbase rows: country, PSP,\namount, status, lag")
            with Cluster("patterns.py", graph_attr=RED):
                p4 = Python("1 · Fix P4 rows\n(PSP_D round down)")
                bucket = Python("2 · Bucket\n67/1/18/10/4")
                cause = Python("3 · Cause\nX1–X6, drift")
                size = Python("4 · Size\ninside bucket limits")
            writer = Python("writer.py")

        raw_tx = Storage("data/raw/transactions.csv")
        raw_fx = Storage("data/raw/fx_rates_daily.csv")
        truth = Storage("data/truth/labels.csv")

        with Cluster("recon validate", graph_attr=GREEN):
            val = Python("validate.py\nbucket shares (always)\npattern bands P1–P4")
            ok = Python("pass → exit 0")
            fail = Python("miss (full run) → exit 5\nsmoke run → warn")

        spec >> fx >> rows >> p4 >> bucket >> cause >> size >> writer
        writer >> raw_tx
        fx >> raw_fx
        writer >> e(style=DASH) >> truth
        raw_tx >> val
        truth >> e("check only", style=DASH) >> val
        val >> ok
        val >> e(color="#c0392b") >> fail


# ---------------------------------------------------------------- 03 pipeline
def pipeline() -> None:
    with diagram("03-data-pipeline", "Detail · dbt Pipeline in DuckDB (FR1)"):
        with Cluster("raw (sources)", graph_attr=GREY):
            s_tx = Storage("transactions.csv")
            s_fx = Storage("fx_rates_daily.csv")
        with Cluster("seeds", graph_attr=GREY):
            seeds = Storage("currency_exponents\npsp_fees · vat_rates")
        th = Storage("thresholds.yaml\n→ dbt vars")

        with Cluster("casarecon.duckdb  (full rebuild each run)", graph_attr=BLUE):
            with Cluster("staging", graph_attr=GREY):
                stg_tx = SQL("stg_transactions\ncontract + types")
                stg_fx = SQL("stg_fx_rates")
            with Cluster("intermediate", graph_attr=GREY):
                int_usd = SQL("int_transactions_usd\nexpected · residual · USD")
            with Cluster("marts", graph_attr=GREEN):
                fct = SQL("fct_transaction_discrepancy\n1 row / txn · category · cause")
                m_seg = SQL("mart_segment_rates")
                m_week = SQL("mart_psp_weekly\n(Thursday rule)")
                m_out = SQL("mart_outliers\n(large rows)")
                m_cause = SQL("mart_cause_summary\n($ Pareto)")

        tests = Dbt("dbt tests + unit tests\nfail → exit 5")

        s_tx >> stg_tx
        s_fx >> stg_fx
        [stg_tx, stg_fx] >> int_usd
        seeds >> e(style=DASH) >> int_usd
        int_usd >> fct
        th >> e("cut-offs", style=DASH) >> fct
        fct >> [m_seg, m_week, m_out, m_cause]
        tests >> e("guards every layer", style=DASH, color="#c0392b") >> fct


# ---------------------------------------------------------------- 04 analysis
def analysis() -> None:
    with diagram("04-analysis-reports", "Detail · Root-Cause Analysis & Reports (FR2, FR4)"):
        with Cluster("marts (read-only)", graph_attr=BLUE):
            fct = SQL("fct_transaction_discrepancy")
            seg = SQL("mart_segment_rates")
            cause = SQL("mart_cause_summary")
        truth = Storage("data/truth")

        with Cluster("recon analyze", graph_attr=GREEN):
            stats = Python("stats.py\nWilson · chi²/Fisher\nSpearman · Mann-Whitney\nBH-FDR")
            glm = Python("glm.py\nlogistic GLM\n(PSP × country)")
            rca = Python("rca.py\nQ1–Q5 · signature table\n$ Pareto · truth check")
            figs = Python("figures.py\none chart / finding")
            fj = Storage("findings.json\n(every number)")

        with Cluster("recon report", graph_attr=PURPLE):
            render = Python("render.py\n(Jinja templates)")
            f_md = Storage("FINDINGS.md")
            r_md = Storage("RECOMMENDATIONS.md\n3–5 actions + $ impact")
            fig = Storage("reports/figures")

        [fct, seg] >> stats
        fct >> glm
        [fct, cause] >> rca
        truth >> e("precision / recall", style=DASH) >> rca
        [stats, glm, rca] >> fj
        fj >> figs >> fig
        fj >> render
        render >> [f_md, r_md]


# ---------------------------------------------------------------- 05 alerts
def alerts() -> None:
    with diagram("05-alert-system", "Detail · Alert System (FR3)"):
        with Cluster("inputs", graph_attr=GREY):
            marts = SQL("mart_psp_weekly\nmart_segment_rates\nfct (pending, lag)")
            rules = Storage("alerts.yaml\nthresholds.yaml")

        with Cluster("recon alerts  (last closed week · n ≥ 50)", graph_attr=PURPLE):
            ev = Python("evaluate.py")
            with Cluster("6 rules", graph_attr=RED):
                r1 = Python("Peer\nPSP vs same-country PSPs\nBH q<0.05 & gap ≥ 2 pts")
                r2 = Python("Change\nweekly p-chart")
                r3 = Python("Money leak\nunder-settled % of $")
                r4 = Python("Large-rows\nsummary")
                r5 = Python("Pending\naging")
                r6 = Python("Settle\nlag")
            status = Python("status vs last closed week\nNEW · ONGOING · RESOLVED\n(no state file)")

        with Cluster("outputs", graph_attr=GREEN):
            jl = Storage("reports/alerts.jsonl")
            md = Storage("reports/alerts.md")
            dash = Python("Dashboard\nAlerts page")
            slack = Slack("Slack webhook\n(optional, off)")

        [marts, rules] >> ev
        ev >> [r1, r2, r3, r4, r5, r6]
        [r1, r2, r3, r4, r5, r6] >> status
        status >> [jl, md]
        jl >> dash
        jl >> e(style=DASH) >> slack


# ---------------------------------------------------------------- 06 serving
def serving() -> None:
    with diagram("06-cli-and-dashboard", "Detail · CLI & Dashboard on One Shared Core (FR3)"):
        analyst = User("Ops analyst")
        reviewer = User("Reviewer")

        with Cluster("recon CLI (Typer, thin shell)", graph_attr=ORANGE):
            q1 = Python("worst-week --month last")
            q2 = Python("query --min-usd 50\n--format csv")
            other = Python("generate · build · validate\nanalyze · alerts · report · all")

        with Cluster("Streamlit dashboard  ·  localhost:8501", graph_attr=PURPLE):
            ov = Python("Overview\nKPIs · trend · WoW\nworst-week card")
            dd = Python("Drill-down")
            ol = Python("Outliers\nmin $50 · CSV")
            rc = Python("Root causes\n& actions")
            al = Python("Alerts")

        with Cluster("casarecon.core (shared)", graph_attr=BLUE):
            q = Python("queries.py\nworst_week · query_transactions\nkpis · segment_rates")
            dbc = Python("db.py\nshort read-only connection\n'Rebuilding, retry'")

        db = Duckdb("casarecon.duckdb\n(marts)")
        files = Storage("alerts.jsonl\nRECOMMENDATIONS.md")

        reviewer >> [q1, q2]
        analyst >> [ov, ol]
        [q1, q2] >> q
        [ov, dd, ol, rc, al] >> q
        q >> dbc >> e("read-only") >> db
        q >> e(style=DASH) >> files
        other >> e("only build writes", style=DASH) >> db


# ---------------------------------------------------------------- 07 run & CI
def run_ci() -> None:
    with diagram("07-run-and-ci", "Detail · Run Paths, Packaging & CI"):
        dev = User("Reviewer / dev")

        with Cluster("3 ways to run  (same result)", graph_attr=GREY):
            mk = Python("make all")
            uvr = Python("pip install uv\nuv run recon all")
            dc = Docker("docker compose up")

        with Cluster("recon all  (fixed order)", graph_attr=BLUE):
            s1 = Python("generate")
            s2 = Dbt("build")
            s3 = Python("validate")
            s4 = Python("analyze")
            s5 = Python("alerts")
            s6 = Python("report")

        with Cluster("outputs", graph_attr=GREEN):
            outs = Storage("casarecon.duckdb\nreports/ · run_manifest.json")
            app = Python("make app → dashboard")

        with Cluster("CI  (GitHub Actions)", graph_attr=PURPLE):
            ci = GithubActions("lint · pytest\n500-row smoke run\ndbt build + tests")

        codes = Storage("exit codes\n0 ok · 1 error\n2 usage · 5 DQ/validation")

        dev >> [mk, uvr, dc]
        [mk, uvr, dc] >> s1
        s1 >> s2 >> s3 >> s4 >> s5 >> s6 >> outs >> app
        s6 >> e(style=DASH) >> codes
        dev >> e("push", style=DASH) >> ci


# ---------------------------------------------------------------- AWS
def aws() -> None:
    with diagram("10-aws-solution", "Proposed Solution on AWS (scale path)", direction="LR"):
        with Cluster("Sources", graph_attr=GREY):
            psp = Storage("PSP settlement files\n(SFTP / API, daily)")
            events = Storage("Yuno auth events")

        with Cluster("AWS account · private VPC · KMS encryption", graph_attr={**BLUE, "bgcolor": "#f7fafd"}):
            with Cluster("Ingest", graph_attr=ORANGE):
                landing = S3("S3 landing\n(raw files)")
                msk = ManagedStreamingForKafka("Amazon MSK\nauth events")
                flink = KinesisDataAnalytics("Managed Flink\nauth ↔ settle match\n(pending tracking)")

            with Cluster("Lakehouse", graph_attr=GREEN):
                lake = S3("S3 + Apache Iceberg\n(source of truth)")
                catalog = GlueDataCatalog("Glue Data Catalog")

            with Cluster("Orchestration & compute", graph_attr=PURPLE):
                mwaa = Airflow("Amazon MWAA\n(Airflow DAG, daily)")
                ecr = ECR("ECR\nrecon image")
                tasks = Fargate("ECS Fargate tasks\nrecon build · analyze\nalerts · report")
                dbt = Dbt("dbt-starrocks")

            with Cluster("Serving  (EKS)", graph_attr=BLUE):
                starrocks = EKS("StarRocks on EKS\nprimary-key tables\n(marts)")
                superset = Superset("Superset\ndashboards")
                alb = ALB("Internal ALB\n+ SSO")
                reports = S3("S3 reports\nFINDINGS ·\nRECOMMENDATIONS")

            with Cluster("Alerting & observability", graph_attr=RED):
                cw = Cloudwatch("CloudWatch\nmetrics · logs")
                eb = Eventbridge("EventBridge")
                sns = SNS("SNS")

            with Cluster("Security  (applies to all)", graph_attr=GREY):
                SecretsManager("Secrets Manager")
                KMS("KMS keys")
                IAM("IAM least privilege")

        ops = Users("Ops · Finance\nPSP ops")
        slack = Slack("Slack")
        pager = Pagerduty("PagerDuty\n(SEV1 only)")
        ci = GithubActions("GitHub Actions\nbuild · test · push")

        psp >> landing >> e("load") >> lake
        events >> msk >> flink >> e("near real time") >> starrocks
        lake - e(style=DASH) - catalog
        ci >> e("image") >> ecr >> e(style=DASH) >> tasks
        mwaa >> e("runs daily") >> tasks
        tasks >> dbt >> starrocks
        lake >> e("external catalog") >> starrocks
        tasks >> reports
        starrocks >> superset >> alb
        alb >> Edge(label="HTTPS", dir="back", color="#5b6770", fontname=FONT, fontsize="10") >> ops
        tasks >> e("alert results") >> cw >> eb >> sns
        sns >> slack
        sns >> e(style=DASH) >> pager


def main() -> None:
    for draw in (high_level, generator, pipeline, analysis, alerts, serving, run_ci, aws):
        draw()
    for svg in sorted(OUT.glob("*.svg")):
        inline_icons(svg)
        print(f"wrote {svg.name} ({svg.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
