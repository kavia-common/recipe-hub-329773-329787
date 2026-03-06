import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from environment variables.

    Contract:
      - Inputs: environment variables (see fields below)
      - Outputs: strongly typed Settings object
      - Errors: raises ValueError if required values are missing
      - Side effects: none (pure configuration loading)
    """

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expires_minutes: int
    cors_allow_origins: list[str]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """
    Load Settings from environment variables.

    Required env:
      - POSTGRES_URL: Postgres connection string (e.g. postgresql://user:pass@host:port/db)

    Optional env:
      - JWT_SECRET_KEY (default: "dev-secret-change-me")
      - JWT_ALGORITHM (default: "HS256")
      - JWT_ACCESS_TOKEN_EXPIRES_MINUTES (default: 60)
      - CORS_ALLOW_ORIGINS (default: "*", comma-separated)

    Returns:
      Settings: parsed settings object.

    Raises:
      ValueError: if POSTGRES_URL is missing/empty or if numeric parsing fails.
    """
    database_url = os.getenv("POSTGRES_URL", "").strip()
    if not database_url:
        raise ValueError("Missing required env var POSTGRES_URL")

    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    try:
        expires_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    except ValueError as e:
        raise ValueError("JWT_ACCESS_TOKEN_EXPIRES_MINUTES must be an integer") from e

    origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if origins_raw == "*":
        cors_allow_origins = ["*"]
    else:
        cors_allow_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    return Settings(
        database_url=database_url,
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=jwt_algorithm,
        jwt_access_token_expires_minutes=expires_minutes,
        cors_allow_origins=cors_allow_origins,
    )
