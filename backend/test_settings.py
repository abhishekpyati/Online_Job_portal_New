from app.core.config import settings

api_key = settings.OPENAI_API_KEY
if api_key:
    print(f"API Key loaded: True")
    print(f"API Key (first 20 chars): {api_key[:20]}")
else:
    print("API Key loaded: False")
print(f"AI Model: {settings.AI_MODEL}")
print(f"Env file path being used: {settings.model_config.get('env_file')}")
