"""Smart Mapper service that sends Document AI JSON to GPT/Claude for structured mapping."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"openai", "anthropic"}


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"⚠️ Smart Mapper template not found: {path}")
    except json.JSONDecodeError as exc:
        logger.error(f"❌ Invalid JSON in template {path}: {exc}")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"❌ Failed to load template {path}: {exc}")
    return None


class SmartMapper:
    """LLM-powered smart mapping for Document AI outputs."""

    def __init__(self) -> None:
        self.provider = (os.getenv("SMART_MAPPER_PROVIDER") or settings.smart_mapper_provider or "openai").lower()
        self.model = os.getenv("SMART_MAPPER_MODEL") or settings.smart_mapper_model or "gpt-4o"
        self.api_key = os.getenv("SMART_MAPPER_API_KEY") or settings.smart_mapper_api_key
        self.timeout = int(os.getenv("SMART_MAPPER_TIMEOUT", str(settings.smart_mapper_timeout or 60)))
        self.temperature = float(os.getenv("SMART_MAPPER_TEMPERATURE", "0.1"))  # Lower for GPT-4o precision
        self.max_tokens = int(os.getenv("SMART_MAPPER_MAX_TOKENS", "2500"))  # Higher for GPT-4o capability
        self.enabled = (settings.smart_mapper_enabled or os.getenv("SMART_MAPPER_ENABLED", "true").lower() in {"1", "true", "yes"})

        if self.provider not in SUPPORTED_PROVIDERS:
            logger.error(f"❌ Unsupported Smart Mapper provider: {self.provider}")
            self.enabled = False

        if not self.api_key:
            logger.warning("⚠️ SMART_MAPPER_API_KEY not configured. Smart mapping disabled.")
            self.enabled = False

        self._client = None
        if self.enabled:
            try:
                if self.provider == "openai":
                    from openai import OpenAI  # type: ignore

                    self._client = OpenAI(api_key=self.api_key)
                elif self.provider == "anthropic":
                    import anthropic  # type: ignore

                    self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"🤖 Smart Mapper initialized with provider {self.provider} and model {self.model}")
            except Exception as exc:  # pragma: no cover - initialization failure
                logger.error(f"❌ Failed to initialize Smart Mapper client: {exc}")
                self.enabled = False

        template_dir_env = os.getenv("SMART_MAPPER_TEMPLATE_DIR")
        self.template_dir = Path(template_dir_env) if template_dir_env else Path(__file__).resolve().parent / "templates"

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------
    def load_template(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """Load mapping template for the specified document type."""
        template_path = self.template_dir / f"{doc_type}_template.json"
        return _load_json_file(template_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def map_document(
        self,
        *,
        doc_type: str,
        document_json: Dict[str, Any],
        template: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]] = None,
        fallback_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send document JSON + template to the configured LLM and return structured output."""
        if not self.enabled or not self._client:
            logger.debug("Smart Mapper disabled or not initialized; skipping LLM mapping")
            return None

        try:
            prompt_payload = self._build_payload(document_json, extracted_fields, fallback_fields)
            instructions = self._build_instructions(doc_type, template)

            raw_response = self._invoke_llm(prompt_payload, instructions)
            if not raw_response:
                return None

            parsed = self._safe_json_loads(raw_response)
            if not parsed:
                logger.error("❌ Smart Mapper returned non-JSON content. Check prompt alignment.")
                return None

            parsed["_mapper_metadata"] = {
                "provider": self.provider,
                "model": self.model,
            }
            return parsed
        except Exception as exc:
            logger.error(f"❌ Smart Mapper failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_payload(
        self,
        document_json: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]],
        fallback_fields: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Cull Document AI JSON to a compact payload safe for prompting."""
        payload: Dict[str, Any] = {}
        payload["document_preview"] = document_json.get("text", "")[:8000]

        entities = document_json.get("entities")
        if isinstance(entities, list):
            compact_entities = []
            for entity in entities[:200]:  # limit to avoid token explosion
                compact_entities.append(
                    {
                        "type": entity.get("type_", entity.get("type")),
                        "mention": entity.get("mention_text", entity.get("mentionText")),
                        "normalized": entity.get("normalized_value", {}).get("text"),
                        "confidence": entity.get("confidence"),
                    }
                )
            payload["entities"] = compact_entities

        if extracted_fields:
            payload["document_ai_fields"] = extracted_fields

        if fallback_fields:
            payload["parser_fields"] = fallback_fields

        return payload

    def _build_instructions(self, doc_type: str, template: Dict[str, Any]) -> str:
        sections = template.get("sections", [])
        output_schema = template.get("output_schema", {})
        validation = template.get("validation_rules", {})

        section_text = json.dumps(sections, ensure_ascii=False, indent=2)
        schema_text = json.dumps(output_schema, ensure_ascii=False, indent=2)
        rules_text = json.dumps(validation, ensure_ascii=False, indent=2)

        return (
            "Anda adalah asisten AI untuk memetakan dokumen pajak Indonesia. "
            "Gunakan data dari Document AI dan hasil parser fallback bila tersedia. "
            "Keluarkan JSON sesuai schema berikut tanpa komentar tambahan.\n\n"
            f"Dokumen: {doc_type}\n"
            f"Bagian dan field yang harus diisi:\n{section_text}\n\n"
            f"Schema output final:\n{schema_text}\n\n"
            f"Aturan validasi:\n{rules_text}\n\n"
            "Jika informasi tidak ditemukan, berikan string kosong. Pastikan format NPWP mengikuti standar XX.XXX.XXX.X-XXX.XXX."
        )

    def _invoke_llm(self, payload: Dict[str, Any], instructions: str) -> Optional[str]:
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)

        if self.provider == "openai":
            return self._invoke_openai(payload_text, instructions)
        if self.provider == "anthropic":
            return self._invoke_anthropic(payload_text, instructions)
        return None

    def _invoke_openai(self, payload_text: str, instructions: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            logger.info(f"🤖 Calling OpenAI API with model: {self.model}")
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise data-mapping assistant that outputs strict JSON."},
                    {
                        "role": "user",
                        "content": f"{instructions}\n\nDocument payload:\n{payload_text}\n\nKeluarkan hanya JSON valid sesuai schema output."
                    },
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.info(f"✅ OpenAI response received: {len(content) if content else 0} characters")
                logger.debug(f"📝 Raw response: {content[:500] if content else 'None'}")
                return content
            return None
        except Exception as exc:
            logger.error(f"❌ OpenAI Smart Mapper error: {exc}")
            return None

    def _invoke_anthropic(self, payload_text: str, instructions: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="You are a precise data-mapping assistant that outputs strict JSON.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instructions},
                            {"type": "text", "text": f"Document payload:\n{payload_text}"},
                            {"type": "text", "text": "Keluarkan hanya JSON valid sesuai schema output."},
                        ],
                    }
                ],
            )
            if response and getattr(response, "content", None):
                parts = []
                for item in response.content:
                    if getattr(item, "type", "") == "text":
                        parts.append(getattr(item, "text", ""))
                return "".join(parts) if parts else None
            return None
        except Exception as exc:
            logger.error(f"❌ Anthropic Smart Mapper error: {exc}")
            return None

    @staticmethod
    def _safe_json_loads(value: str) -> Optional[Dict[str, Any]]:
        try:
            # Strip markdown code fences if present (GPT-4o often adds ```json ... ```)
            cleaned = value.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]  # Remove ```json
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]  # Remove ```
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]  # Remove trailing ```
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"❌ Smart Mapper JSON decode error: {exc}")
            logger.error(f"❌ Failed to parse: {value[:200]}")
            return None


smart_mapper_service = SmartMapper()

__all__ = ["smart_mapper_service", "SmartMapper"]
