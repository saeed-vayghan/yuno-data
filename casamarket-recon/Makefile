.PHONY: all smoke generate build validate analyze alerts report app test clean
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
clean:    ; rm -rf data/raw data/truth data/*.duckdb data/*.duckdb.wal data/.dbt dbt/target dbt/logs
