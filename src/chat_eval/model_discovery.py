"""Discover available models from each provider's API."""

from __future__ import annotations

import os


def list_openai_models(api_key: str | None = None) -> list[dict[str, str]]:
    """List available OpenAI models."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY", ""))
    models = client.models.list()
    # Filter to chat-capable models, sorted by ID
    chat_models = []
    for m in sorted(models.data, key=lambda x: x.id):
        model_id = m.id
        # Include GPT models and o-series, skip embeddings/whisper/dall-e/tts
        if any(model_id.startswith(p) for p in ("gpt-", "o1", "o3", "o4")):
            chat_models.append({"id": model_id, "provider": "openai"})
    return chat_models


def list_google_models(api_key: str | None = None) -> list[dict[str, str]]:
    """List available Google Gemini models."""
    import google.generativeai as genai

    genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY", ""))
    models = []
    for m in genai.list_models():
        # Only include generateContent-capable models
        if "generateContent" in (m.supported_generation_methods or []):
            name = m.name.replace("models/", "")
            models.append({"id": name, "provider": "google"})
    return sorted(models, key=lambda x: x["id"])


def list_bedrock_models(region: str = "us-west-2") -> list[dict[str, str]]:
    """List available Bedrock models."""
    import boto3

    client = boto3.client("bedrock", region_name=region)
    response = client.list_foundation_models()
    models = []
    for m in response.get("modelSummaries", []):
        model_id = m["modelId"]
        # Include text-generation models
        if "TEXT" in m.get("outputModalities", []):
            models.append({
                "id": model_id,
                "provider": "bedrock",
                "name": m.get("modelName", ""),
            })
    return sorted(models, key=lambda x: x["id"])


def list_bedrock_inference_profiles(region: str = "us-west-2") -> list[dict[str, str]]:
    """List available Bedrock cross-region inference profiles."""
    import boto3

    client = boto3.client("bedrock", region_name=region)
    try:
        response = client.list_inference_profiles()
    except Exception:
        return []
    profiles = []
    for p in response.get("inferenceProfileSummaries", []):
        profiles.append({
            "id": p["inferenceProfileId"],
            "provider": "bedrock",
            "name": p.get("inferenceProfileName", ""),
            "type": "inference-profile",
        })
    return sorted(profiles, key=lambda x: x["id"])


def discover_models(providers: list[str] | None = None) -> dict[str, list[dict]]:
    """Discover available models across all configured providers.

    Args:
        providers: List of providers to check. None = check all with available keys.

    Returns:
        Dict of provider -> list of model info dicts.
    """
    results: dict[str, list[dict]] = {}
    providers = providers or []

    if not providers:
        # Auto-detect based on available credentials
        if os.environ.get("OPENAI_API_KEY"):
            providers.append("openai")
        if os.environ.get("GOOGLE_API_KEY"):
            providers.append("google")
        # Bedrock uses AWS credentials (always try)
        providers.append("bedrock")

    for provider in providers:
        try:
            if provider == "openai":
                results["openai"] = list_openai_models()
            elif provider == "google":
                results["google"] = list_google_models()
            elif provider == "bedrock":
                foundation = list_bedrock_models()
                profiles = list_bedrock_inference_profiles()
                results["bedrock"] = foundation
                if profiles:
                    results["bedrock-profiles"] = profiles
        except Exception as e:
            results[provider] = [{"error": str(e)}]

    return results
