from shared_lib.database import create_db_engine, get_database_url


def test_process_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_USER=file-user\nPOSTGRES_PASSWORD=file-password\n"
        "DB_HOST=file-host\nPOSTGRES_PORT=5432\nACCOUNTING_DB=file-db\n"
    )
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    for name in ("POSTGRES_USER", "POSTGRES_PASSWORD", "DB_HOST", "POSTGRES_PORT", "ACCOUNTING_DB"):
        monkeypatch.delenv(name, raising=False)

    assert get_database_url("ACCOUNTING_DB", env_path=str(env_file)) == (
        "postgresql+psycopg2://file-user:file-password@file-host:5432/file-db"
    )

    monkeypatch.setenv("POSTGRES_USER", "process-user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "process-password")
    monkeypatch.setenv("DB_HOST", "process-host")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("ACCOUNTING_DB", "process-db")

    assert get_database_url("ACCOUNTING_DB", env_path=str(env_file)) == (
        "postgresql+psycopg2://process-user:process-password@process-host:6543/process-db"
    )

    engine = create_db_engine(get_database_url("ACCOUNTING_DB", env_path=str(env_file)))
    assert engine.dialect.driver == "psycopg2"
    engine.dispose()
