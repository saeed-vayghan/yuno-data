# Flink 1.20 + the Kafka SQL connector (from Maven Central at build time).
# The filesystem connector and the CSV / JSON formats already ship in /opt/flink/lib.
FROM flink:1.20.3-java17
ARG KAFKA_CONNECTOR=3.4.0-1.20
RUN wget -q -O /opt/flink/lib/flink-sql-connector-kafka-${KAFKA_CONNECTOR}.jar \
      https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${KAFKA_CONNECTOR}/flink-sql-connector-kafka-${KAFKA_CONNECTOR}.jar
