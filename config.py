"""Configuration management for LogDetective application."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Splunk Configuration
    splunk_host: str = Field(default="localhost", env="SPLUNK_HOST")
    splunk_port: int = Field(default=8089, env="SPLUNK_PORT")
    splunk_username: str = Field(default="admin", env="SPLUNK_USERNAME")
    splunk_password: str = Field(default="password", env="SPLUNK_PASSWORD")
    splunk_scheme: str = Field(default="https", env="SPLUNK_SCHEME")
    splunk_index: str = Field(default="104118", env="SPLUNK_INDEX")
    
    # AWS Bedrock Configuration
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        env="BEDROCK_MODEL_ID"
    )
    
    # Application Configuration
    app_title: str = Field(default="LogDetective - Splunk Assistant", env="APP_TITLE")
    max_search_results: int = Field(default=1000, env="MAX_SEARCH_RESULTS")
    chart_theme: str = Field(default="plotly_white", env="CHART_THEME")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings() 