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
        # GPT-4o Configuration (for Faktur Pajak, PPh21, PPh23)
        self.provider = (os.getenv("SMART_MAPPER_PROVIDER") or settings.smart_mapper_provider or "openai").lower()
        self.model = os.getenv("SMART_MAPPER_MODEL") or settings.smart_mapper_model or "gpt-4o"
        self.api_key = os.getenv("SMART_MAPPER_API_KEY") or settings.smart_mapper_api_key
        self.timeout = int(os.getenv("SMART_MAPPER_TIMEOUT", str(settings.smart_mapper_timeout or 60)))
        self.temperature = float(os.getenv("SMART_MAPPER_TEMPERATURE", "0.1"))  # Lower for GPT-4o precision
        self.max_tokens = int(os.getenv("SMART_MAPPER_MAX_TOKENS", "16000"))  # Increased to 16K for large rekening koran (100+ transactions)
        self.enabled = (settings.smart_mapper_enabled or os.getenv("SMART_MAPPER_ENABLED", "true").lower() in {"1", "true", "yes"})

        # Claude AI Configuration (specifically for Rekening Koran)
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.claude_max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "8000"))

        if self.provider not in SUPPORTED_PROVIDERS:
            logger.error(f"❌ Unsupported Smart Mapper provider: {self.provider}")
            self.enabled = False

        if not self.api_key:
            logger.warning("⚠️ SMART_MAPPER_API_KEY not configured. Smart mapping disabled.")
            self.enabled = False

        self._client = None
        self._claude_client = None

        if self.enabled:
            try:
                # Initialize primary client (GPT-4o)
                if self.provider == "openai":
                    from openai import OpenAI  # type: ignore

                    self._client = OpenAI(api_key=self.api_key)
                elif self.provider == "anthropic":
                    import anthropic  # type: ignore

                    self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"🤖 Smart Mapper initialized with provider {self.provider} and model {self.model}")
                logger.info(f"🎯 Max tokens configured: {self.max_tokens}")

                # Initialize Claude client for Rekening Koran (if API key provided)
                if self.claude_api_key:
                    try:
                        import anthropic  # type: ignore
                        self._claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                        logger.info(f"🧠 Claude AI initialized for Rekening Koran: {self.claude_model}")
                        logger.info(f"🎯 Claude max tokens: {self.claude_max_tokens}")
                    except Exception as exc:
                        logger.warning(f"⚠️ Failed to initialize Claude client: {exc}")
                        logger.warning("⚠️ Rekening Koran will fallback to GPT-4o")

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
            # ⚠️ PER-PAGE STRATEGY: Process rekening koran page by page
            if doc_type == "rekening_koran":
                pages = document_json.get("pages", [])
                if isinstance(pages, list) and len(pages) > 1:
                    # Multi-page rekening koran - process per page
                    logger.info(f"📄 Multi-page rekening koran detected: {len(pages)} pages")
                    logger.info(f"📄 Using PER-PAGE PROCESSING - each page processed separately")
                    return self._map_document_per_page(
                        doc_type=doc_type,
                        document_json=document_json,
                        template=template,
                        extracted_fields=extracted_fields,
                        fallback_fields=fallback_fields
                    )

            # Normal processing for small documents
            prompt_payload = self._build_payload(document_json, extracted_fields, fallback_fields)
            instructions = self._build_instructions(doc_type, template)

            raw_response = self._invoke_llm(prompt_payload, instructions, doc_type)
            if not raw_response:
                return None

            parsed = self._safe_json_loads(raw_response)
            if not parsed:
                logger.error("❌ Smart Mapper returned non-JSON content. Check prompt alignment.")
                return None

            # ⚠️ VALIDATION: Check transaction count for rekening_koran
            if doc_type == "rekening_koran" and isinstance(parsed, dict):
                transactions = parsed.get("transactions", [])
                if isinstance(transactions, list):
                    logger.info(f"📊 Smart Mapper extracted {len(transactions)} transactions")

                    # Compare with input table rows if available
                    if "tables" in prompt_payload:
                        input_tables = prompt_payload.get("tables", [])
                        total_input_rows = sum(len(table.get("rows", [])) for table in input_tables)
                        if total_input_rows > 0:
                            logger.info(f"📊 Input had {total_input_rows} table rows from Document AI")

                            # Warning if significant mismatch
                            if len(transactions) < total_input_rows * 0.7:  # Less than 70% extracted
                                logger.warning(f"⚠️ Potential data loss: Only {len(transactions)} transactions extracted from {total_input_rows} input rows")
                                logger.warning(f"⚠️ Missing approximately {total_input_rows - len(transactions)} transactions")
                                logger.warning("⚠️ This may indicate truncated response or parsing issues")

            parsed["_mapper_metadata"] = {
                "provider": self.provider,
                "model": self.model,
            }
            return parsed
        except Exception as exc:
            logger.error(f"❌ Smart Mapper failed: {exc}")
            return None

    def _map_document_per_page(
        self,
        *,
        doc_type: str,
        document_json: Dict[str, Any],
        template: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]] = None,
        fallback_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process rekening koran PAGE BY PAGE to avoid token limits.

        Strategy:
        1. Process each page separately with Smart Mapper
        2. First page: Extract bank_info + saldo_info + transactions
        3. Subsequent pages: Extract transactions only
        4. Merge all transactions into single response
        5. Export combines all pages into one Excel file
        """
        try:
            pages = document_json.get("pages", [])
            total_pages = len(pages)
            logger.info(f"📄 Starting per-page processing for {total_pages} pages")

            # Process first page (includes bank_info + saldo_info + transactions)
            first_page_json = {
                "text": document_json.get("text", ""),  # ✅ FIX: Include ALL text
                "pages": [pages[0]],  # Only first page
                "entities": document_json.get("entities", [])[:200]  # ✅ FIX: Increase from 50 to 200
            }

            logger.info(f"📄 Processing page 1/{total_pages} (with metadata)...")
            first_result = self._process_single_page(
                page_json=first_page_json,
                doc_type=doc_type,
                template=template,
                extracted_fields=extracted_fields,
                fallback_fields=fallback_fields,
                include_metadata=True,
                page_number=1,
                bank_context=None  # Will be detected from page 1
            )

            if not first_result:
                logger.error("❌ First page processing failed")
                return None

            # Initialize merged result with first page
            merged_result = first_result.copy()
            all_transactions = merged_result.get("transactions", [])
            bank_info = merged_result.get("bank_info", {})
            bank_name = bank_info.get("nama_bank", "Unknown Bank") if isinstance(bank_info, dict) else "Unknown Bank"

            logger.info(f"✅ Page 1: {len(all_transactions)} transactions extracted")
            logger.info(f"🏦 Detected bank: {bank_name}")

            # Process remaining pages (transactions only)
            full_document_text = document_json.get("text", "")

            for page_idx in range(1, total_pages):
                page_num = page_idx + 1

                # ✅ FIX: Extract text segments that belong to this specific page
                # Google Document AI stores text with page references
                logger.info(f"📄 Processing page {page_num}/{total_pages} (transactions only) for {bank_name}...")

                page_text = self._extract_text_for_page(
                    full_document_text,
                    pages[page_idx],
                    document_json
                )

                # Add bank context to text
                context_text = f"Bank: {bank_name}\nContinuation page {page_num}\n\n{page_text}"

                page_json = {
                    "text": context_text,
                    "pages": [pages[page_idx]],
                    "entities": []  # No entities needed for continuation
                }

                # DEBUG: Check page structure
                page_tables = pages[page_idx].get("tables", []) if isinstance(pages[page_idx], dict) else []
                page_lines = pages[page_idx].get("lines", []) if isinstance(pages[page_idx], dict) else []
                page_paragraphs = pages[page_idx].get("paragraphs", []) if isinstance(pages[page_idx], dict) else []

                logger.info(f"   📊 Page {page_num} structure: {len(page_tables)} tables, {len(page_lines)} lines, {len(page_paragraphs)} paragraphs")
                logger.info(f"   📝 Context text length: {len(context_text)} characters")
                page_result = self._process_single_page(
                    page_json=page_json,
                    doc_type=doc_type,
                    template=template,
                    extracted_fields=None,
                    fallback_fields=None,
                    include_metadata=False,
                    page_number=page_num,
                    bank_context=bank_name  # Pass bank info
                )

                if page_result and "transactions" in page_result:
                    page_transactions = page_result["transactions"]
                    if isinstance(page_transactions, list):
                        all_transactions.extend(page_transactions)
                        logger.info(f"✅ Page {page_num}: {len(page_transactions)} transactions extracted")
                else:
                    logger.warning(f"⚠️ Page {page_num} returned no transactions")

            # Update merged result with all transactions
            merged_result["transactions"] = all_transactions
            logger.info(f"✅ Per-page processing complete: {len(all_transactions)} total transactions from {total_pages} pages")

            return merged_result

        except Exception as exc:
            logger.error(f"❌ Per-page processing failed: {exc}", exc_info=True)
            return None

    def _map_document_chunked(
        self,
        *,
        doc_type: str,
        document_json: Dict[str, Any],
        template: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]] = None,
        fallback_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        [DEPRECATED] Process large rekening koran in chunks to avoid token limits.
        Now using _map_document_per_page instead.

        Strategy:
        1. Split table data into chunks of ~80 rows each
        2. Process each chunk separately with Smart Mapper
        3. Merge all results into single response
        4. Extract bank_info and saldo_info from first chunk only
        """
        try:
            logger.info("🔄 Starting chunked processing for large rekening koran")

            # Split tables into chunks
            chunks = self._split_tables_into_chunks(document_json, chunk_size=80)
            logger.info(f"📦 Split into {len(chunks)} chunks")

            # Process first chunk (includes bank_info + saldo_info + transactions)
            first_chunk_json = {
                "text": document_json.get("text", "")[:15000],  # Include text for metadata
                "pages": chunks[0] if chunks else [],
                "entities": document_json.get("entities", [])[:50]  # Limited entities
            }

            logger.info(f"🔄 Processing chunk 1/{len(chunks)} (with metadata)...")
            first_result = self._process_single_chunk(
                chunk_json=first_chunk_json,
                doc_type=doc_type,
                template=template,
                extracted_fields=extracted_fields,
                fallback_fields=fallback_fields,
                include_metadata=True
            )

            if not first_result:
                logger.error("❌ First chunk processing failed")
                return None

            # Initialize merged result with first chunk
            merged_result = first_result.copy()
            all_transactions = merged_result.get("transactions", [])

            # Process remaining chunks (transactions only)
            for i, chunk_pages in enumerate(chunks[1:], start=2):
                chunk_json = {
                    "text": "",  # No text needed for transaction-only chunks
                    "pages": chunk_pages,
                    "entities": []
                }

                logger.info(f"🔄 Processing chunk {i}/{len(chunks)} (transactions only)...")
                chunk_result = self._process_single_chunk(
                    chunk_json=chunk_json,
                    doc_type=doc_type,
                    template=template,
                    extracted_fields=None,
                    fallback_fields=None,
                    include_metadata=False
                )

                if chunk_result and "transactions" in chunk_result:
                    chunk_transactions = chunk_result["transactions"]
                    if isinstance(chunk_transactions, list):
                        all_transactions.extend(chunk_transactions)
                        logger.info(f"✅ Chunk {i} added {len(chunk_transactions)} transactions")
                else:
                    logger.warning(f"⚠️ Chunk {i} returned no transactions")

            # Update merged result with all transactions
            merged_result["transactions"] = all_transactions
            logger.info(f"✅ Chunked processing complete: {len(all_transactions)} total transactions")

            return merged_result

        except Exception as exc:
            logger.error(f"❌ Chunked processing failed: {exc}", exc_info=True)
            return None

    def _split_tables_into_chunks(self, document_json: Dict[str, Any], chunk_size: int = 80) -> List[List[Dict[str, Any]]]:
        """
        Split Document AI pages with tables into chunks.
        Each chunk contains pages with ~chunk_size total table rows.

        Returns: List of page lists, where each page list is a chunk
        """
        pages = document_json.get("pages", [])
        if not isinstance(pages, list):
            return []

        chunks = []
        current_chunk = []
        current_row_count = 0

        for page in pages:
            if not isinstance(page, dict):
                continue

            page_tables = page.get("tables", [])
            if not isinstance(page_tables, list):
                continue

            # Count rows in this page
            page_row_count = 0
            for table in page_tables:
                if isinstance(table, dict):
                    body_rows = table.get("body_rows", table.get("bodyRows", []))
                    if isinstance(body_rows, list):
                        page_row_count += len(body_rows)

            # If adding this page exceeds chunk_size, start new chunk
            if current_row_count > 0 and current_row_count + page_row_count > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [page]
                current_row_count = page_row_count
            else:
                current_chunk.append(page)
                current_row_count += page_row_count

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _process_single_page(
        self,
        *,
        page_json: Dict[str, Any],
        doc_type: str,
        template: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]],
        fallback_fields: Optional[Dict[str, Any]],
        include_metadata: bool,
        page_number: int,
        bank_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Process a single page of rekening koran"""
        try:
            # Build payload for this page
            prompt_payload = self._build_payload(page_json, extracted_fields, fallback_fields)

            # Build instructions (modify for transaction-only pages)
            instructions = self._build_instructions(doc_type, template)

            if not include_metadata:
                # For transaction-only pages, give very explicit instructions
                bank_hint = f" (Bank: {bank_context})" if bank_context else ""

                # Check if this page has table data
                has_tables = len(prompt_payload.get("tables", [])) > 0

                if has_tables:
                    # Page has structured table data
                    instructions += (
                        f"\n\n" + "="*60 + "\n"
                        f"📄 CONTINUATION PAGE MODE (Page {page_number}){bank_hint}\n"
                        + "="*60 + "\n"
                        "⚠️ CRITICAL INSTRUCTIONS FOR THIS PAGE:\n\n"
                        f"1. This is a CONTINUATION page of a multi-page {bank_context or 'bank'} rekening koran\n"
                        "2. Bank info and account info was extracted from page 1\n"
                        "3. YOUR ONLY JOB: Extract ALL transaction rows from the tables on THIS page\n"
                        "4. The 'tables' field in the payload contains structured table data for THIS page\n"
                        "5. Map each table row to a transaction following the same bank format as page 1\n"
                        "6. ⚠️ DO NOT SKIP DUPLICATE TRANSACTIONS! If you see 3 identical transactions, extract ALL 3!\n\n"
                        "🎯 OUTPUT FORMAT (STRICT):\n"
                        "{\n"
                        '  "transactions": [\n'
                        '    {"tanggal": "...", "keterangan": "...", "debet": "...", "kredit": "...", "saldo": "..."},\n'
                        '    {"tanggal": "...", "keterangan": "...", "debet": "...", "kredit": "...", "saldo": "..."}\n'
                        '  ]\n'
                        "}\n\n"
                        "⚠️ DO NOT return empty transactions array if table data exists!\n"
                        "⚠️ Extract EVERY row in the table - don't skip any!\n"
                        "⚠️ DO NOT include bank_info or saldo_info in output - only transactions!\n\n"
                    )
                else:
                    # Page has NO table data - fallback to text extraction
                    logger.warning(f"⚠️ Page {page_number} has NO table data! Using AGGRESSIVE text extraction fallback...")
                    instructions += (
                        f"\n\n" + "="*60 + "\n"
                        f"📄 AGGRESSIVE TEXT PARSING MODE (Page {page_number}){bank_hint}\n"
                        + "="*60 + "\n"
                        "⚠️ CRITICAL: This page has NO structured table data!\n"
                        "You MUST extract transactions from raw text!\n\n"
                        "CONTEXT:\n"
                        f"- This is continuation page {page_number} of {bank_context or 'bank'} rekening koran\n"
                        "- Previous pages had transactions successfully extracted\n"
                        "- This page MUST have transaction data (it's a bank statement page!)\n"
                        "- The 'document_preview' contains raw OCR text from this page\n\n"
                        "YOUR TASK:\n"
                        "1. Read the text carefully - look for ANY transaction patterns\n"
                        "2. Find date indicators: DD/MM/YYYY, DD/MM, DD MMM, numbers like 01, 02, 15, 31\n"
                        "3. Find transaction descriptions: TRANSFER, BIAYA, ATM, KLIRING, BUNGA, etc.\n"
                        "4. Find amounts: numbers with commas/dots (1,000,000 or 1.000.000)\n"
                        "5. Extract saldo (balance) - usually at end of each line\n\n"
                        "PARSING STRATEGY (try in order):\n"
                        "A. Look for table-like text with columns\n"
                        "B. Look for lines starting with dates\n"
                        "C. Look for repeated patterns across lines\n"
                        "D. If text is very messy, extract ANY lines with dates + amounts\n\n"
                        f"BANK-SPECIFIC HINTS for {bank_context or 'bank'}:\n"
                        "- Mandiri: 'DD MMM' dates, 'Keterangan' descriptions, Debet/Kredit columns\n"
                        "- BCA: 'DD/MM' dates, 'KETERANGAN' with reference codes, DB/CR columns\n"
                        "- BNI/BRI/others: Similar patterns with bank-specific formatting\n\n"
                        "⚠️⚠️⚠️ CRITICAL RULES:\n"
                        "1. DO NOT return empty transactions array unless page is TRULY blank!\n"
                        "2. If you find even 1-2 transactions, extract them!\n"
                        "3. Partial data is better than nothing!\n"
                        "4. Make reasonable guesses based on patterns!\n"
                        "5. ⚠️ DO NOT SKIP DUPLICATE TRANSACTIONS! Extract each row separately even if identical!\n\n"
                        "OUTPUT FORMAT (STRICT):\n"
                        "{\"transactions\": [{\"tanggal\": \"...\", \"keterangan\": \"...\", \"debet\": \"...\", \"kredit\": \"...\", \"saldo\": \"...\"}]}\n\n"
                        "EXAMPLE from messy text:\n"
                        "Text: '15 JAN TRANSFER 1000000 5000000'\n"
                        "Extract: {\"tanggal\": \"15 JAN\", \"keterangan\": \"TRANSFER\", \"kredit\": \"1000000\", \"saldo\": \"5000000\"}\n\n"
                    )

            # Invoke LLM (pass doc_type for routing)
            raw_response = self._invoke_llm(prompt_payload, instructions, doc_type)
            if not raw_response:
                return None

            # Parse response
            parsed = self._safe_json_loads(raw_response)
            if not parsed:
                logger.error(f"❌ Page {page_number} returned non-JSON content")
                logger.error(f"❌ Raw response: {raw_response[:200]}")
                return None

            # DEBUG: Log what we got
            if not include_metadata:
                trans_count = len(parsed.get("transactions", []))
                logger.info(f"🔍 Page {page_number} DEBUG: Received {trans_count} transactions")
                if trans_count == 0:
                    logger.warning(f"⚠️ Page {page_number} WARNING: GPT-4o returned empty transactions")
                    logger.warning(f"⚠️ Raw response: {raw_response}")
                    logger.warning(f"⚠️ Payload had {len(prompt_payload.get('tables', []))} tables")

            return parsed

        except Exception as exc:
            logger.error(f"❌ Page {page_number} processing failed: {exc}")
            return None

    def _process_single_chunk(
        self,
        *,
        chunk_json: Dict[str, Any],
        doc_type: str,
        template: Dict[str, Any],
        extracted_fields: Optional[Dict[str, Any]],
        fallback_fields: Optional[Dict[str, Any]],
        include_metadata: bool
    ) -> Optional[Dict[str, Any]]:
        """[DEPRECATED] Process a single chunk of tables. Use _process_single_page instead."""
        try:
            # Build payload for this chunk
            prompt_payload = self._build_payload(chunk_json, extracted_fields, fallback_fields)

            # Build instructions (modify for transaction-only chunks)
            instructions = self._build_instructions(doc_type, template)

            if not include_metadata:
                # For transaction-only chunks, simplify instructions
                instructions += (
                    "\n\n🔄 CHUNKED PROCESSING MODE:\n"
                    "This is a continuation chunk. Extract ONLY the transactions from the tables.\n"
                    "You do NOT need to extract bank_info or saldo_info - only transactions array.\n"
                    "Output format: {\"transactions\": [...]}\n"
                )

            # Invoke LLM (pass doc_type for routing)
            raw_response = self._invoke_llm(prompt_payload, instructions, doc_type)
            if not raw_response:
                return None

            # Parse response
            parsed = self._safe_json_loads(raw_response)
            if not parsed:
                logger.error("❌ Chunk returned non-JSON content")
                return None

            return parsed

        except Exception as exc:
            logger.error(f"❌ Chunk processing failed: {exc}")
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
        # ✅ FIX: Remove text limit - GPT-4o has 128K context window
        payload["document_preview"] = document_json.get("text", "")

        entities = document_json.get("entities")
        if isinstance(entities, list):
            compact_entities = []
            # ✅ FIX: Increase entity limit from 200 to 1000
            for entity in entities[:1000]:
                compact_entities.append(
                    {
                        "type": entity.get("type_", entity.get("type")),
                        "mention": entity.get("mention_text", entity.get("mentionText")),
                        "normalized": entity.get("normalized_value", {}).get("text"),
                        "confidence": entity.get("confidence"),
                    }
                )
            payload["entities"] = compact_entities

        # ⚠️ CRITICAL FIX: Extract ALL TABLES from Document AI (no limits!)
        pages = document_json.get("pages", [])
        if isinstance(pages, list) and len(pages) > 0:
            extracted_tables = []
            table_count = 0

            for page_idx, page in enumerate(pages):
                if not isinstance(page, dict):
                    continue

                page_tables = page.get("tables", [])
                if not isinstance(page_tables, list):
                    continue

                for table_idx, table in enumerate(page_tables):
                    # ✅ FIX: Remove table limit - extract ALL tables
                    # if table_count >= 50:  # REMOVED
                    #     break

                    if not isinstance(table, dict):
                        continue

                    # Extract header rows
                    header_rows = table.get("header_rows", table.get("headerRows", []))
                    body_rows = table.get("body_rows", table.get("bodyRows", []))

                    table_data = {
                        "page": page_idx + 1,
                        "table_index": table_idx + 1,
                        "headers": self._extract_table_rows(header_rows, document_json.get("text", "")),
                        # ✅ FIX: Remove row limit - extract ALL rows!
                        "rows": self._extract_table_rows(body_rows, document_json.get("text", ""), limit=None)
                    }

                    extracted_tables.append(table_data)
                    table_count += 1

            if extracted_tables:
                payload["tables"] = extracted_tables
                total_rows = sum(len(t.get("rows", [])) for t in extracted_tables)
                logger.info(f"✅ Extracted {len(extracted_tables)} tables with {total_rows} total rows from Document AI")

        if extracted_fields:
            payload["document_ai_fields"] = extracted_fields

        if fallback_fields:
            payload["parser_fields"] = fallback_fields

        return payload

    def _extract_table_rows(self, rows: list, full_text: str, limit: int = None) -> list:
        """Extract text from table rows using text anchors"""
        extracted_rows = []

        if not isinstance(rows, list):
            return extracted_rows

        for row_idx, row in enumerate(rows):
            if limit and row_idx >= limit:
                break

            if not isinstance(row, dict):
                continue

            cells = row.get("cells", [])
            if not isinstance(cells, list):
                continue

            row_cells = []
            for cell in cells:
                if not isinstance(cell, dict):
                    continue

                # Extract cell text using text anchor
                cell_text = self._get_text_from_layout(cell.get("layout", {}), full_text)
                row_cells.append(cell_text)

            if row_cells:  # Only add non-empty rows
                extracted_rows.append(row_cells)

        return extracted_rows

    def _extract_text_for_page(
        self,
        full_document_text: str,
        page: Dict[str, Any],
        document_json: Dict[str, Any]
    ) -> str:
        """
        ✅ FIX: Extract text content that belongs to a specific page from full document text.

        Google Document AI provides text with layout anchors that reference positions
        in the full document text. We use these anchors to extract page-specific text.
        """
        if not isinstance(page, dict):
            return ""

        if not full_document_text:
            return ""

        page_text_parts = []

        # Strategy 1: Extract from all paragraphs on this page
        paragraphs = page.get("paragraphs", [])
        if isinstance(paragraphs, list):
            for paragraph in paragraphs:
                if isinstance(paragraph, dict):
                    layout = paragraph.get("layout", {})
                    if isinstance(layout, dict):
                        para_text = self._get_text_from_layout(layout, full_document_text)
                        if para_text:
                            page_text_parts.append(para_text)

        # Strategy 2: Extract from all lines on this page
        lines = page.get("lines", [])
        if isinstance(lines, list):
            for line in lines:
                if isinstance(line, dict):
                    layout = line.get("layout", {})
                    if isinstance(layout, dict):
                        line_text = self._get_text_from_layout(layout, full_document_text)
                        if line_text:
                            page_text_parts.append(line_text)

        # Strategy 3: Extract from table cells if available
        tables = page.get("tables", [])
        if isinstance(tables, list):
            for table in tables:
                if isinstance(table, dict):
                    # Extract from header rows
                    header_rows = table.get("header_rows", table.get("headerRows", []))
                    if isinstance(header_rows, list):
                        for row in header_rows:
                            if isinstance(row, dict):
                                cells = row.get("cells", [])
                                if isinstance(cells, list):
                                    row_text = []
                                    for cell in cells:
                                        if isinstance(cell, dict):
                                            layout = cell.get("layout", {})
                                            if isinstance(layout, dict):
                                                cell_text = self._get_text_from_layout(layout, full_document_text)
                                                if cell_text:
                                                    row_text.append(cell_text)
                                    if row_text:
                                        page_text_parts.append(" | ".join(row_text))

                    # Extract from body rows
                    body_rows = table.get("body_rows", table.get("bodyRows", []))
                    if isinstance(body_rows, list):
                        for row in body_rows:
                            if isinstance(row, dict):
                                cells = row.get("cells", [])
                                if isinstance(cells, list):
                                    row_text = []
                                    for cell in cells:
                                        if isinstance(cell, dict):
                                            layout = cell.get("layout", {})
                                            if isinstance(layout, dict):
                                                cell_text = self._get_text_from_layout(layout, full_document_text)
                                                if cell_text:
                                                    row_text.append(cell_text)
                                    if row_text:
                                        page_text_parts.append(" | ".join(row_text))

        # Combine all extracted text
        if page_text_parts:
            extracted_text = "\n".join(page_text_parts)
            logger.info(f"   ✅ Extracted {len(extracted_text)} characters of text for this page")
            return extracted_text

        # Fallback: If no text extracted, return a helpful message
        logger.warning(f"   ⚠️ Could not extract text for this page using layout anchors")
        return "No text extracted. Please analyze any visible data in the page structure."

    def _get_text_from_page(self, page: Dict[str, Any]) -> str:
        """
        DEPRECATED: Old method that didn't properly extract text.
        Kept for compatibility but shouldn't be used anymore.
        """
        if not isinstance(page, dict):
            return ""

        table_count = len(page.get("tables", []))
        if table_count > 0:
            return f"Page contains {table_count} transaction table(s). Extract ALL transaction rows."

        return "Page contains transaction data. Extract ALL transactions."

    def _get_text_from_layout(self, layout: dict, full_text: str) -> str:
        """Extract text from layout using text anchor segments"""
        if not isinstance(layout, dict):
            return ""

        text_anchor = layout.get("text_anchor", layout.get("textAnchor", {}))
        if not isinstance(text_anchor, dict):
            return ""

        text_segments = text_anchor.get("text_segments", text_anchor.get("textSegments", []))
        if not isinstance(text_segments, list) or not text_segments:
            return ""

        # Combine all segments
        result_text = []
        for segment in text_segments:
            if not isinstance(segment, dict):
                continue

            start_index = segment.get("start_index", segment.get("startIndex", 0))
            end_index = segment.get("end_index", segment.get("endIndex", 0))

            if isinstance(start_index, (int, str)) and isinstance(end_index, (int, str)):
                try:
                    start = int(start_index)
                    end = int(end_index)
                    if 0 <= start < len(full_text) and start < end <= len(full_text):
                        result_text.append(full_text[start:end])
                except (ValueError, TypeError):
                    pass

        return "".join(result_text).strip()

    def _build_instructions(self, doc_type: str, template: Dict[str, Any]) -> str:
        sections = template.get("sections", [])
        output_schema = template.get("output_schema", {})
        validation = template.get("validation_rules", {})
        extraction_instructions = template.get("extraction_instructions", {})
        bank_hints = template.get("bank_specific_format_hints", {})
        final_reminders = template.get("final_reminders", {})

        section_text = json.dumps(sections, ensure_ascii=False, indent=2)
        schema_text = json.dumps(output_schema, ensure_ascii=False, indent=2)
        rules_text = json.dumps(validation, ensure_ascii=False, indent=2)

        # Build comprehensive instructions
        base_instructions = (
            "You are an expert AI assistant for extracting structured data from Indonesian financial documents, "
            "especially bank statements (rekening koran) from ALL Indonesian banks.\n\n"
            "Your task is to:\n"
            "1. IDENTIFY the bank from logo/header/text\n"
            "2. ADAPT your extraction strategy based on bank format\n"
            "3. EXTRACT ALL data with HIGH ACCURACY\n"
            "4. Be FLEXIBLE - every bank has different format\n\n"
        )

        # Add document type specific instructions
        if doc_type == "rekening_koran":
            base_instructions += (
                "⚠️⚠️⚠️ CRITICAL INSTRUCTIONS FOR BANK STATEMENTS ⚠️⚠️⚠️\n\n"
                "This is a REKENING KORAN (Bank Statement). Your PRIMARY goal is to:\n"
                "1. Identify which bank this statement is from (BCA, Mandiri, BNI, BRI, CIMB, Permata, BTN, BSI, Danamon, etc.)\n"
                "2. **USE THE STRUCTURED TABLE DATA** provided in the 'tables' field - this is pre-extracted by Google Document AI!\n"
                "3. Extract ALL transactions (every single row) from the table data - this is MOST IMPORTANT\n"
                "4. Extract bank info (account number, name, period) and balance info\n\n"
                "🎯 HOW TO USE TABLE DATA:\n"
                "The payload includes a 'tables' field with structured data like this:\n"
                "  tables: [\n"
                "    {\n"
                "      page: 1,\n"
                "      headers: [[\"TANGGAL\", \"KETERANGAN\", \"MUTASI\", \"SALDO\"]],\n"
                "      rows: [\n"
                "        [\"01/01\", \"TRANSFER\", \"CR\", \"5000000\", \"15000000\"],\n"
                "        [\"02/01\", \"BIAYA ADM\", \"DB\", \"15000\", \"14985000\"]\n"
                "      ]\n"
                "    }\n"
                "  ]\n\n"
                "⚠️ CRITICAL: Use the 'tables' data as your PRIMARY source for transactions!\n"
                "The table data is already structured with rows and cells - much more accurate than parsing text.\n\n"
                "🏦 BANK FORMAT DETECTION:\n"
                "Look at the table headers to identify bank format:\n"
                "- BCA: Has CBG column and DB/CR sub-columns under MUTASI\n"
                "- Mandiri/BNI/BTN: Standard Debet | Kredit columns\n"
                "- BRI: Single Mutasi column with +/- values\n"
                "- CIMB/OCBC: Often use English (Withdrawal | Deposit)\n\n"
                "Map the table columns to the output fields based on bank format.\n\n"
            )

        instructions = (
            base_instructions +
            f"Document Type: {doc_type}\n\n"
            f"Sections and Fields to Extract:\n{section_text}\n\n"
            f"Output JSON Schema (STRICT - follow this exactly):\n{schema_text}\n\n"
            f"Validation Rules:\n{rules_text}\n\n"
        )

        # Add extraction instructions if available
        if extraction_instructions:
            instructions += f"\n📋 STEP-BY-STEP EXTRACTION INSTRUCTIONS:\n{json.dumps(extraction_instructions, ensure_ascii=False, indent=2)}\n\n"

        # Add bank-specific hints if available
        if bank_hints:
            instructions += f"\n🏦 BANK-SPECIFIC FORMAT HINTS (for reference):\n{json.dumps(bank_hints, ensure_ascii=False, indent=2)}\n\n"

        # Add final reminders if available
        if final_reminders:
            instructions += f"\n⚠️ FINAL REMINDERS:\n{json.dumps(final_reminders, ensure_ascii=False, indent=2)}\n\n"
        else:
            instructions += (
                "\n⚠️⚠️⚠️ FINAL CRITICAL REMINDERS ⚠️⚠️⚠️:\n"
                "1. Output ONLY valid JSON matching the output_schema\n"
                "2. 🚨 Extract EVERY SINGLE transaction row from the tables data - DON'T STOP EARLY!\n"
                "3. 🚨 If tables array has 100 rows, your output MUST have 100 transactions!\n"
                "4. 🚨 Process ALL pages and ALL tables - don't truncate your response!\n"
                "5. If a field is not found, use empty string '' (not null, not 'N/A')\n"
                "6. Remove currency formatting - output plain numbers only\n"
                "7. Adapt to the bank format you detect in the document\n"
                "8. 🚨 COMPLETE YOUR JSON - ensure closing brackets ] and } are present!\n"
            )

        return instructions

    def _invoke_llm(self, payload: Dict[str, Any], instructions: str, doc_type: str = "") -> Optional[str]:
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)

        # 🧠 ROUTING LOGIC: Use Claude for Rekening Koran, GPT-4o for others
        if doc_type == "rekening_koran" and self._claude_client:
            logger.info("🧠 Using Claude AI for Rekening Koran processing")
            return self._invoke_claude_direct(payload_text, instructions)

        # Default: Use configured provider (GPT-4o for other documents)
        if self.provider == "openai":
            return self._invoke_openai(payload_text, instructions)
        if self.provider == "anthropic":
            return self._invoke_anthropic(payload_text, instructions)
        return None

    def _invoke_openai(self, payload_text: str, instructions: str) -> Optional[str]:
        """Invoke OpenAI API with automatic retry on rate limits"""
        if not self._client:
            return None

        import time
        max_retries = 5
        base_delay = 2  # Start with 2 seconds

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")

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
                    choice = response.choices[0]
                    content = choice.message.content
                    finish_reason = choice.finish_reason

                    logger.info(f"✅ OpenAI response received: {len(content) if content else 0} characters")
                    logger.info(f"🏁 Finish reason: {finish_reason}")

                    # ⚠️ CRITICAL: Check if response was truncated
                    if finish_reason == "length":
                        logger.error("🚨 RESPONSE TRUNCATED! GPT-4o hit max_tokens limit!")
                        logger.error(f"🚨 Current max_tokens: {self.max_tokens}")
                        logger.error("🚨 This means TRANSACTIONS ARE MISSING from the output!")
                        logger.error("🚨 Solution: Increase SMART_MAPPER_MAX_TOKENS in .env or split document into chunks")
                        # Still return the partial content, but log warning
                    elif finish_reason != "stop":
                        logger.warning(f"⚠️ Unusual finish reason: {finish_reason}")

                    logger.debug(f"📝 Raw response: {content[:500] if content else 'None'}")
                    return content
                return None

            except Exception as exc:
                error_str = str(exc)

                # Check if it's a rate limit error (429)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"⚠️ Rate limit hit! Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {max_retries} retries")
                        return None
                else:
                    # Other errors - don't retry
                    logger.error(f"❌ OpenAI Smart Mapper error: {exc}")
                    return None

        return None

    def _invoke_anthropic(self, payload_text: str, instructions: str) -> Optional[str]:
        """Invoke Anthropic (Claude) API with automatic retry on rate limits"""
        if not self._client:
            return None

        import time
        max_retries = 5
        base_delay = 2  # Start with 2 seconds

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")

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
                    # Check stop_reason for truncation
                    stop_reason = getattr(response, "stop_reason", None)
                    logger.info(f"🏁 Stop reason: {stop_reason}")

                    if stop_reason == "max_tokens":
                        logger.error("🚨 RESPONSE TRUNCATED! Claude hit max_tokens limit!")
                        logger.error(f"🚨 Current max_tokens: {self.max_tokens}")
                        logger.error("🚨 This means TRANSACTIONS ARE MISSING from the output!")
                        logger.error("🚨 Solution: Increase SMART_MAPPER_MAX_TOKENS in .env or split document into chunks")
                    elif stop_reason != "end_turn":
                        logger.warning(f"⚠️ Unusual stop reason: {stop_reason}")

                    parts = []
                    for item in response.content:
                        if getattr(item, "type", "") == "text":
                            parts.append(getattr(item, "text", ""))

                    content = "".join(parts) if parts else None
                    logger.info(f"✅ Anthropic response received: {len(content) if content else 0} characters")
                    return content
                return None

            except Exception as exc:
                error_str = str(exc)

                # Check if it's a rate limit error
                if "rate_limit" in error_str.lower() or "429" in error_str or "overloaded" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"⚠️ Rate limit hit! Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {max_retries} retries")
                        return None
                else:
                    # Other errors - don't retry
                    logger.error(f"❌ Anthropic Smart Mapper error: {exc}")
                    return None

        return None

    def _invoke_claude_direct(self, payload_text: str, instructions: str) -> Optional[str]:
        """Invoke Claude API directly (dedicated for Rekening Koran)"""
        if not self._claude_client:
            logger.warning("⚠️ Claude client not initialized, falling back to primary provider")
            return None

        import time
        max_retries = 5
        base_delay = 2  # Start with 2 seconds

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry attempt {attempt + 1}/{max_retries}")

                logger.info(f"🧠 Calling Claude API with model: {self.claude_model}")
                response = self._claude_client.messages.create(
                    model=self.claude_model,
                    max_tokens=self.claude_max_tokens,
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
                    # Check stop_reason for truncation
                    stop_reason = getattr(response, "stop_reason", None)
                    logger.info(f"🏁 Stop reason: {stop_reason}")

                    if stop_reason == "max_tokens":
                        logger.error("🚨 RESPONSE TRUNCATED! Claude hit max_tokens limit!")
                        logger.error(f"🚨 Current max_tokens: {self.claude_max_tokens}")
                        logger.error("🚨 This means TRANSACTIONS ARE MISSING from the output!")
                        logger.error("🚨 Solution: Increase CLAUDE_MAX_TOKENS in .env or split document into chunks")
                    elif stop_reason != "end_turn":
                        logger.warning(f"⚠️ Unusual stop reason: {stop_reason}")

                    parts = []
                    for item in response.content:
                        if getattr(item, "type", "") == "text":
                            parts.append(getattr(item, "text", ""))

                    content = "".join(parts) if parts else None
                    logger.info(f"✅ Claude response received: {len(content) if content else 0} characters")
                    return content
                return None

            except Exception as exc:
                error_str = str(exc)

                # Check if it's a rate limit error
                if "rate_limit" in error_str.lower() or "429" in error_str or "overloaded" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"⚠️ Rate limit hit! Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {max_retries} retries")
                        return None
                else:
                    # Other errors - don't retry
                    logger.error(f"❌ Claude Smart Mapper error: {exc}")
                    return None

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
            # Try to fix common JSON issues caused by unescaped control characters
            logger.warning(f"⚠️ Initial JSON parse failed: {exc}")
            logger.warning(f"⚠️ Attempting to fix control characters...")

            try:
                # Re-parse with strict=False to be more lenient
                cleaned_value = value.strip()
                if cleaned_value.startswith("```json"):
                    cleaned_value = cleaned_value[7:]
                elif cleaned_value.startswith("```"):
                    cleaned_value = cleaned_value[3:]
                if cleaned_value.endswith("```"):
                    cleaned_value = cleaned_value[:-3]
                cleaned_value = cleaned_value.strip()

                # Try parsing with strict=False (allows control characters in some cases)
                return json.loads(cleaned_value, strict=False)
            except json.JSONDecodeError as exc2:
                logger.error(f"❌ Smart Mapper JSON decode error (even after retry): {exc2}")
                logger.error(f"❌ Error position: line {exc2.lineno} column {exc2.colno}")
                logger.error(f"❌ Failed content around error: {value[max(0, exc2.pos-100):exc2.pos+100]}")

                # Log first 500 chars for debugging
                logger.error(f"❌ Response preview (first 500 chars): {value[:500]}")
                logger.error(f"❌ Response preview (last 500 chars): {value[-500:]}")
                return None

    def refine_adapter_result(
        self,
        adapter_result: Dict[str, Any],
        ocr_json: Dict[str, Any],
        doc_type: str = "rekening_koran"
    ) -> Optional[Dict[str, Any]]:
        """
        ✨ NEW: Lightweight refinement of bank adapter results using GPT-4o

        This method takes the result from bank adapters and asks GPT to:
        1. Validate extracted data
        2. Fill any missing fields
        3. Fix obvious errors
        4. Add missing transactions

        TOKEN SAVINGS: ~90% compared to full extraction
        - Full extraction: 15,000 input + 2,000 output = 17,000 tokens
        - Refinement: 500 input + 300 output = 800 tokens

        Args:
            adapter_result: Result from bank adapter (even if partial/empty)
            ocr_json: Full OCR JSON from Google Document AI
            doc_type: Document type (default: rekening_koran)

        Returns:
            Refinement suggestions (corrections, additions, etc.)
        """
        if not self.enabled or not self._client:
            logger.debug("Smart Mapper disabled - skipping refinement")
            return adapter_result

        try:
            logger.info("✨ Refining adapter result with GPT-4o...")

            # Build lightweight refinement prompt
            adapter_summary = {
                "bank_info": adapter_result.get("bank_info", {}),
                "saldo_info": adapter_result.get("saldo_info", {}),
                "transaction_count": len(adapter_result.get("transactions", [])),
                "transactions_sample": adapter_result.get("transactions", [])[:3],  # First 3 for context
                "processing_strategy": adapter_result.get("processing_strategy", [])
            }

            # Extract tables summary (not full tables - just headers and count)
            tables_summary = []
            for table in ocr_json.get("tables", [])[:3]:  # Max 3 tables for context
                tables_summary.append({
                    "page": table.get("page", 0),
                    "headers": table.get("headers", []),
                    "row_count": len(table.get("rows", []))
                })

            refinement_prompt = (
                f"🔍 TASK: Refine bank statement extraction\n\n"
                f"BANK ADAPTER EXTRACTED:\n"
                f"{json.dumps(adapter_summary, ensure_ascii=False, indent=2)}\n\n"
                f"AVAILABLE OCR DATA (summary):\n"
                f"- Total text length: {len(ocr_json.get('text', ''))} characters\n"
                f"- Tables available: {len(ocr_json.get('tables', []))} tables\n"
                f"- Sample tables:\n{json.dumps(tables_summary, ensure_ascii=False, indent=2)}\n\n"
                f"YOUR TASK:\n"
                f"1. Review the adapter's extraction\n"
                f"2. Check if transaction count matches table row counts\n"
                f"3. Identify any missing transactions\n"
                f"4. Suggest corrections for obvious errors\n"
                f"5. Fill any missing metadata fields\n\n"
                f"OUTPUT FORMAT (JSON only):\n"
                f"{{\n"
                f"  \"validation\": {{\n"
                f"    \"adapter_quality\": \"good|partial|poor\",\n"
                f"    \"missing_transaction_count\": 0,\n"
                f"    \"issues_found\": []\n"
                f"  }},\n"
                f"  \"corrections\": [\n"
                f"    {{\"field\": \"bank_info.nama_bank\", \"current\": \"...\", \"corrected\": \"...\"}}\n"
                f"  ],\n"
                f"  \"missing_transactions\": [\n"
                f"    {{\"tanggal\": \"...\", \"keterangan\": \"...\", \"debet\": \"...\", \"kredit\": \"...\", \"saldo\": \"...\"}}\n"
                f"  ],\n"
                f"  \"metadata_updates\": {{\n"
                f"    \"confidence\": 0.95\n"
                f"  }}\n"
                f"}}\n\n"
                f"⚠️ IMPORTANT:\n"
                f"- Only include actual corrections/additions needed\n"
                f"- If adapter result is perfect, return empty corrections\n"
                f"- Be concise - this should be much smaller than full extraction\n"
                f"- Focus on gaps and errors, not re-stating correct data\n"
            )

            # Call GPT with lightweight prompt (pass doc_type for routing)
            raw_response = self._invoke_llm(refinement_prompt, "Refine and validate the extraction", doc_type)

            if not raw_response:
                logger.warning("⚠️ GPT refinement returned no response - using adapter result as-is")
                return adapter_result

            refinement = self._safe_json_loads(raw_response)

            if not refinement:
                logger.warning("⚠️ GPT refinement returned invalid JSON - using adapter result as-is")
                return adapter_result

            # Apply refinements
            refined_result = self._apply_refinements(adapter_result, refinement)

            # Log refinement stats
            corrections_count = len(refinement.get("corrections", []))
            additions_count = len(refinement.get("missing_transactions", []))

            logger.info(f"✨ Refinement complete:")
            logger.info(f"   - Corrections applied: {corrections_count}")
            logger.info(f"   - Transactions added: {additions_count}")
            logger.info(f"   - Adapter quality: {refinement.get('validation', {}).get('adapter_quality', 'unknown')}")

            return refined_result

        except Exception as exc:
            logger.error(f"❌ Refinement error: {exc}")
            # Return original adapter result on error
            return adapter_result

    def _apply_refinements(
        self,
        adapter_result: Dict[str, Any],
        refinement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply GPT refinements to adapter result"""

        result = adapter_result.copy()

        # Apply field corrections
        for correction in refinement.get("corrections", []):
            field_path = correction.get("field", "").split(".")
            current_dict = result

            # Navigate to nested field
            for i, key in enumerate(field_path[:-1]):
                if key not in current_dict:
                    current_dict[key] = {}
                current_dict = current_dict[key]

            # Apply correction
            if field_path:
                current_dict[field_path[-1]] = correction.get("corrected")

        # Add missing transactions
        missing_transactions = refinement.get("missing_transactions", [])
        if missing_transactions:
            result.setdefault("transactions", [])
            result["transactions"].extend(missing_transactions)

            # Sort by date if possible
            try:
                result["transactions"].sort(key=lambda x: x.get("tanggal", ""))
            except:
                pass  # If sorting fails, keep as-is

        # Update metadata
        metadata_updates = refinement.get("metadata_updates", {})
        for key, value in metadata_updates.items():
            result[key] = value

        # Add refinement metadata
        result["refined_by_gpt"] = True
        result["refinement_stats"] = {
            "corrections": len(refinement.get("corrections", [])),
            "additions": len(missing_transactions),
            "adapter_quality": refinement.get("validation", {}).get("adapter_quality", "unknown")
        }

        return result


smart_mapper_service = SmartMapper()

__all__ = ["smart_mapper_service", "SmartMapper"]
