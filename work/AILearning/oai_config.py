import os
from typing import Dict, Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.identity import InteractiveBrowserCredential

from autogen import config_list_from_json

from dotenv import load_dotenv, find_dotenv                                                                                                                                 
load_dotenv(find_dotenv())

class OAIConfig:
    def __init__(
        self,
        config_file: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:

        self.oai_auth_type = os.getenv("OPENAI_AUTH_TYPE") or "use_azure_openai_api_key"

        if self._use_openai_api_key():
            self.oai_config = {
                "oai_key": os.getenv("OPENAI_API_KEY"),
                "oai_model": os.getenv("OPENAI_API_MODEL"),
                "oai_version": os.getenv("OPENAI_API_VERSION")
            }
            return

        if self._use_azure_openai_api_key():
            self.oai_config = {
                "api_type": "azure",
                "api_version": api_version or os.getenv("OPENAI_API_VERSION"),

                "aoai_key": api_key or os.getenv("AZURE_OPENAI_API_KEY"),
                "aoai_endpoint": endpoint_url or os.getenv("AZURE_OPENAI_API_BASE"),
                "aoai_deploy": model_name or os.getenv("AZURE_OPENAI_API_DEPLOY")
            }
            return

        if self.oai_auth_type == "use_azure_managed_identity":
            token_provider = self._get_bearer_token_provider()
            self.oai_config = {
                "api_type": "azure",
                "api_version": api_version or os.getenv("OPENAI_API_VERSION"),

                "azure_ad_token_provider": token_provider,
                "aoai_endpoint": endpoint_url or os.getenv("AZURE_OPENAI_API_BASE"),
                "aoai_deploy": model_name or os.getenv("AZURE_OPENAI_API_DEPLOY")
            }
            return

    def _use_azure_openai_api_key(self):
        return self.oai_auth_type == "use_azure_openai_api_key"

    def _use_azure_managed_identity(self):
        return self.oai_auth_type == "use_azure_managed_identity"

    def _use_openai_api_key(self):
        return self.oai_auth_type == "use_openai_api_key"

    def _get_bearer_token_provider(self):
        credential = InteractiveBrowserCredential()
        bearer_token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        return bearer_token_provider()

    def get_config(self) -> Dict:

        if self._use_openai_api_key():
            return ({
                "type": "oai",
                "model": self.oai_config["oai_model"],
                "api_key": self.oai_config["oai_key"],
                "api_version": self.oai_config["oai_version"],
            })

        if self._use_azure_openai_api_key():
            return ({
                "type": "aoai",
                "aoai_args": {
                    "azure_endpoint": self.oai_config["aoai_endpoint"], 
                    "api_version": self.oai_config["api_version"],
                    "api_key": self.oai_config["aoai_key"]
                },
                "model": self.oai_config["aoai_deploy"],
            })
        elif self._use_azure_managed_identity():
            return ({
                "type": "aoai",
                "aoai_args": {
                    "azure_endpoint": self.oai_config["aoai_endpoint"], 
                    "api_version": self.oai_config["api_version"],
                    "azure_ad_token_provider": self.oai_config["azure_ad_token_provider"]
                },
                "model": self.oai_config["aoai_deploy"],
            })
        
        return {}

    def get_default_autogen_config(self) -> Dict:

        # handle if oai_auth_type is openai direct api key only
        if self._use_openai_api_key():
            llm_config = {
                "model": self.oai_config["oai_model"],
            }
            return llm_config

        if self._use_azure_openai_api_key() or self._use_azure_managed_identity():
            llm_config = {
                "config_list": [{
                    "api_type": self.oai_config["api_type"],
                    "api_version": self.oai_config["api_version"],
                    "base_url": self.oai_config["aoai_endpoint"],
                    "model": self.oai_config["aoai_deploy"],
                }], 
                "cache_seed": None
            }
            if self._use_azure_openai_api_key():
                llm_config["config_list"][0]["api_key"] = self.oai_config["aoai_key"]
            elif self._use_azure_managed_identity():
                llm_config["config_list"][0]["azure_ad_token_provider"] = self.oai_config["azure_ad_token_provider"]

            return llm_config

    def get_custom_autogen_config(
        self,
        seed: Optional[str] = 47,
        temperature: Optional[float] = 0.5,
        max_tokens: Optional[int] = -1,
        timeout: Optional[int] = 6000,
    ) -> Dict:
        llm_config = {
            "config_list": self.get_default_autogen_config()["config_list"],
            "seed": seed,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "cache_seed": None,
        }
        return llm_config
