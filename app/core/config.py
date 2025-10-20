from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    API_BASE_V1: str = "/v1"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    API_BEARER_TOKEN: str = "devtoken"


    HIGGSFIELD_API_KEY: str
    HIGGSFIELD_API_SECRET: str

    HF_PLATFORM_BASE: str
    HF_CLOUD_BASE: str
    HF_GENERATE_PATH: str = "/v1/job-sets"
    
    MODEL_T2I_ENDPOINT: str = "/v1/text2image/nano-banana"
    MODEL_T2V_ENDPOINT: str = "/generate/seedance-v1-lite-t2v"
    MODEL_I2V_ENDPOINT: str = "/v1/image2video/veo3"

    MOCK_MODE: bool
    SAVE_RESULTS: bool

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
