.PHONY: all smoke generate build validate analyze alerts report app test clean check-idempotent
all:      ; uv run recon all
smoke:    ; uv run recon all --rows 500
generate: ; uv run recon generate
build:    ; uv run recon build
validate: ; uv run recon validate
analyze:  ; uv run recon analyze
alerts:   ; uv run recon alerts
report:   ; uv run recon report
app:      ; uv run recon dashboard
test:     ; uv run pytest -q
clean:    ; rm -rf data/raw data/truth data/lake data/*.duckdb data/*.duckdb.wal data/.dbt dbt/target dbt/logs

# Two full runs must give byte-identical data + reports (run_manifest.json holds timestamps; PNGs are not byte-stable).
HASHED = find data/raw/transactions.csv reports -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.md' -o -name '*.csv' \) ! -name run_manifest.json | sort
check-idempotent:
	@uv run recon all >/dev/null 2>&1 && $(HASHED) | xargs shasum -a 256 > data/.hash1
	@uv run recon all >/dev/null 2>&1 && $(HASHED) | xargs shasum -a 256 > data/.hash2
	@diff data/.hash1 data/.hash2 && echo "IDEMPOTENT ($$(wc -l < data/.hash1 | tr -d ' ') files)"; rc=$$?; rm -f data/.hash1 data/.hash2; exit $$rc

# ---- local dev tooling (DEV-OPS, M4) ----
.PHONY: lake dev-check
# Lake path: land raw -> per-PSP files, load -> staged parquet, DQ checks, then dbt reads the lake.
lake:
	uv run recon ingest land
	uv run recon ingest load
	uv run recon ingest check
	CASARECON_SOURCE=lake uv run recon build
# PII scan (exit 5 on a hit) + dbt lineage summary (reports/lineage/LINEAGE.md).
dev-check:
	uv run recon ops pii-scan
	uv run recon ops lineage
