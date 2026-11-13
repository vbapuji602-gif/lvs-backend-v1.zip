import os


class BackendConfig:
    """LVS Secure Backend Gateway Configuration.

    Every secret below is read from an environment variable only.
    Nothing here is hardcoded - on Render (or any host) you set these
    as "Environment Variables" in the dashboard. The backend will run
    fine with any of them missing; that provider/tool is just disabled.
    """

    APP_NAME: str = "LVS-Secure-Backend"
    VERSION: str = "4.0.0"

    # Master secret used to sign session tokens. Set a long random value
    # in your host's environment variables. If left unset, a random one
    # is generated at startup (sessions won't survive a server restart).
    SECRET_KEY: str = os.getenv("BACKEND_SECRET_KEY", "")

    ALLOWED_ORIGINS: list = ["*"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ---- AI providers (all optional; router skips any that are unset) ----
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # ---- Voice ----
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # ---- Data tools ----
    COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")
    WEATHERAPI_KEY: str = os.getenv("WEATHERAPI_KEY", "")

    # ---- Data persistence ----
    # Where device registry / master-password hash are persisted as JSON.
    # On Render's free tier this disk is wiped on every redeploy - fine
    # for now, but means the master password has to be set again after
    # a redeploy. A paid persistent disk or a real database removes that.
    DATA_DIR: str = os.getenv("LVS_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
