"""Domain errors. The CLI maps them to exit codes; the dashboard maps them to messages."""


class CasaReconError(Exception):
    """Base class for every expected error in casarecon."""


class DataQualityError(CasaReconError):
    """A dbt test or a validation gate failed. CLI exit 5."""


class DbMissing(CasaReconError):
    """The DuckDB file does not exist yet. CLI exit 1: 'Run `make all` first'."""


class DbBusy(CasaReconError):
    """The DuckDB file is locked by `recon build`. CLI exit 1: 'rebuilding, retry'."""


class BadFilter(CasaReconError):
    """Unknown filter value or sort key. CLI exit 2."""


class InputMissing(CasaReconError):
    """A required input file is missing (e.g. data/raw before `recon build`). CLI exit 1."""
