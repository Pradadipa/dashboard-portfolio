# This file is part of the FastAPI framework and is used to define configuration settings for the application. It imports the necessary modules from Pydantic to create a settings class that can be used to manage application configuration in a structured way. The `BaseSettings` class allows for easy management of environment variables and other configuration sources, while `SettingsConfigDict` provides additional configuration options for the settings class.
# Import the necessary modules from Pydantic to create a settings class for managing application configuration.
from pydantic_settings import BaseSettings, SettingsConfigDict

# Create class `Settings` that inherits from `BaseSettings` to define application configuration settings.
class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables or .env file.
    Please refer to the documentation for more information on how to use this class and configure your application settings.
    Pydantic's `BaseSettings` class allows for easy management of environment variables and other configuration sources, while `SettingsConfigDict` provides additional configuration options for the settings class.
    """
    # Databases
    database_url: str

    # App
    app_name: str = "Business Dashboard API"
    debug: bool = False

    # Timezone (based on shopify schema: America/New_York)
    business_timezone: str = "America/New_York"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields in the .env file that are not defined in the Settings class
    )

# Singleton - Create a single instance of the `Settings` class to be used throughout the application.
settings = Settings()
