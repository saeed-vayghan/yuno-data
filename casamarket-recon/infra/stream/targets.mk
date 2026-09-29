# Local streaming path (Redpanda + Flink SQL), off by default. Owner: STREAM. See docs/STREAM.md.
# make stream-up stream-job stream-replay   (wait ~20 s for a checkpoint)   make stream-compare stream-down
STREAM_SVC   = redpanda jobmanager taskmanager
STREAM_LIMIT ?= 20000
STREAM_SPEED ?= 86400
KAFKA_PY     = uv run --with kafka-python

.PHONY: stream-up stream-job stream-replay stream-compare stream-tail stream-down
stream-up:
	mkdir -p data/lake/stream/matched
	docker compose --profile stream up -d --build --wait $(STREAM_SVC)
	docker compose --profile stream run --rm redpanda-init
# Submit infra/stream/sql/match.sql (one-shot SQL client container; the job keeps running).
stream-job:
	docker compose run --rm sql-client
stream-replay:
	$(KAFKA_PY) recon stream replay --limit $(STREAM_LIMIT) --speed $(STREAM_SPEED)
stream-compare:
	uv run recon stream compare
stream-tail:
	$(KAFKA_PY) recon stream tail
# Stops and removes only the stream containers (topics and job state go with them; the sink CSVs stay).
stream-down:
	docker compose --profile stream rm -fsv $(STREAM_SVC) redpanda-init
