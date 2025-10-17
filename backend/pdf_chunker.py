"""
PDF Chunker for Multi-Page Bank Statements
Handles large PDF files (20+ pages) by splitting into manageable chunks
Optimized for rekening koran / bank statements
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2

logger = logging.getLogger(__name__)

class PDFChunker:
    """Split large PDF files into chunks for processing"""

    def __init__(self, max_pages_per_chunk: int = 10):
        """
        Initialize PDF chunker

        Args:
            max_pages_per_chunk: Maximum pages to process in one chunk (default: 10)
        """
        self.max_pages_per_chunk = max_pages_per_chunk
        logger.info(f"📄 PDF Chunker initialized (max {max_pages_per_chunk} pages/chunk)")

    def get_page_count(self, pdf_path: str) -> int:
        """Get total page count of PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"❌ Failed to get page count from {pdf_path}: {e}")
            return 0

    def needs_chunking(self, pdf_path: str, threshold: int = 10) -> bool:
        """
        Check if PDF needs to be chunked

        Args:
            pdf_path: Path to PDF file
            threshold: Page count threshold for chunking (default: 10)

        Returns:
            True if PDF has more pages than threshold
        """
        page_count = self.get_page_count(pdf_path)
        needs_split = page_count > threshold

        if needs_split:
            logger.info(f"📚 PDF has {page_count} pages - chunking required")
        else:
            logger.info(f"📄 PDF has {page_count} pages - no chunking needed")

        return needs_split

    def split_pdf_to_chunks(self, pdf_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Split PDF into multiple chunk files

        Args:
            pdf_path: Path to source PDF
            output_dir: Directory for chunk files (default: same as source)

        Returns:
            List of dicts with chunk info: {
                'path': str,
                'start_page': int,
                'end_page': int,
                'total_pages': int
            }
        """
        try:
            page_count = self.get_page_count(pdf_path)
            if page_count == 0:
                logger.error(f"❌ Cannot split PDF with 0 pages: {pdf_path}")
                return []

            # Prepare output directory
            if output_dir is None:
                output_dir = str(Path(pdf_path).parent / "chunks")

            os.makedirs(output_dir, exist_ok=True)

            # Read source PDF
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                chunks = []
                chunk_num = 1

                # Split into chunks
                for start_page in range(0, total_pages, self.max_pages_per_chunk):
                    end_page = min(start_page + self.max_pages_per_chunk, total_pages)

                    # Create chunk PDF
                    pdf_writer = PyPDF2.PdfWriter()

                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    # Generate chunk filename
                    base_name = Path(pdf_path).stem
                    chunk_filename = f"{base_name}_chunk{chunk_num}_p{start_page+1}-{end_page}.pdf"
                    chunk_path = os.path.join(output_dir, chunk_filename)

                    # Write chunk file
                    with open(chunk_path, 'wb') as chunk_file:
                        pdf_writer.write(chunk_file)

                    chunk_info = {
                        'path': chunk_path,
                        'start_page': start_page + 1,  # 1-indexed
                        'end_page': end_page,
                        'chunk_number': chunk_num,
                        'pages_in_chunk': end_page - start_page
                    }

                    chunks.append(chunk_info)
                    logger.info(f"✅ Created chunk {chunk_num}: pages {start_page+1}-{end_page} → {chunk_filename}")

                    chunk_num += 1

                logger.info(f"📚 Split {pdf_path} into {len(chunks)} chunks")
                return chunks

        except Exception as e:
            logger.error(f"❌ Failed to split PDF {pdf_path}: {e}", exc_info=True)
            return []

    def cleanup_chunks(self, chunk_paths: List[str]):
        """Delete chunk files after processing"""
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.info(f"🗑️ Deleted chunk: {chunk_path}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete chunk {chunk_path}: {e}")

    def get_optimal_chunk_size(self, page_count: int) -> int:
        """
        Calculate optimal chunk size based on page count

        Args:
            page_count: Total pages in document

        Returns:
            Optimal pages per chunk
        """
        if page_count <= 10:
            return page_count  # No chunking needed
        elif page_count <= 20:
            return 10  # 2 chunks
        elif page_count <= 50:
            return 10  # 5 chunks
        else:
            return 15  # Larger chunks for very big files

    def merge_extracted_data(self, chunk_results: List[Dict[str, Any]], document_type: str = "rekening_koran") -> Dict[str, Any]:
        """
        Merge extracted data from multiple chunks

        Args:
            chunk_results: List of extraction results from each chunk
            document_type: Type of document being processed

        Returns:
            Merged extraction result
        """
        if not chunk_results:
            return {}

        if len(chunk_results) == 1:
            return chunk_results[0]

        logger.info(f"🔗 Merging data from {len(chunk_results)} chunks")

        # For rekening koran, merge transactions
        if document_type == "rekening_koran":
            return self._merge_rekening_koran_chunks(chunk_results)
        else:
            # For other types, just take the first chunk's main data
            # and concatenate raw text
            merged = chunk_results[0].copy()
            all_text = []

            for chunk in chunk_results:
                raw_text = chunk.get('raw_text', '') or chunk.get('extracted_text', '')
                if raw_text:
                    all_text.append(raw_text)

            merged['raw_text'] = '\n\n=== PAGE BREAK ===\n\n'.join(all_text)
            merged['extracted_text'] = merged['raw_text']

            return merged

    def _merge_rekening_koran_chunks(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge rekening koran chunks - combine transactions and preserve bank_info/saldo_info"""
        merged = chunk_results[0].copy()

        # Collect bank_info and saldo_info from all chunks (prefer first chunk with data)
        merged_bank_info = {}
        merged_saldo_info = {}
        all_transactions = []
        all_raw_text = []

        for i, chunk in enumerate(chunk_results):
            logger.info(f"Processing chunk {i+1}/{len(chunk_results)}")

            # Get raw text
            raw_text = chunk.get('raw_text', '') or chunk.get('extracted_text', '')
            if raw_text:
                all_raw_text.append(f"\n=== CHUNK {i+1} ===\n{raw_text}")

            # Get extracted_data
            extracted_data = chunk.get('extracted_data', {})
            logger.info(f"  🔍 DEBUG MERGE: extracted_data type = {type(extracted_data)}")
            if isinstance(extracted_data, dict):
                logger.info(f"  🔍 DEBUG MERGE: extracted_data keys = {list(extracted_data.keys())}")

            if isinstance(extracted_data, dict):
                # ✅ FIX: Check for transactions at ROOT LEVEL first (from enhanced_bank_processor)
                # Enhanced processor returns: {'transactions': [...], 'bank_info': {...}, ...}
                transactions_direct = extracted_data.get('transactions', [])
                if transactions_direct and isinstance(transactions_direct, list):
                    all_transactions.extend(transactions_direct)
                    logger.info(f"  ✅ Found {len(transactions_direct)} transactions at root level")

                    # Also get bank_info and saldo_info from root level
                    bank_info = extracted_data.get('bank_info', {})
                    if bank_info and not merged_bank_info:
                        merged_bank_info = bank_info.copy()
                        logger.info(f"  ✅ Found bank_info at root level in chunk {i+1}")

                    saldo_info = extracted_data.get('saldo_info', {})
                    if saldo_info:
                        if 'saldo_awal' in saldo_info and not merged_saldo_info.get('saldo_awal'):
                            merged_saldo_info['saldo_awal'] = saldo_info['saldo_awal']
                            logger.info(f"  ✅ Found saldo_awal at root level in chunk {i+1}: {saldo_info['saldo_awal']}")
                        if 'saldo_akhir' in saldo_info:
                            merged_saldo_info['saldo_akhir'] = saldo_info['saldo_akhir']
                            logger.info(f"  ✅ Found saldo_akhir at root level in chunk {i+1}: {saldo_info['saldo_akhir']}")
                        for key in ['total_kredit', 'total_debet', 'mata_uang']:
                            if key in saldo_info and not merged_saldo_info.get(key):
                                merged_saldo_info[key] = saldo_info[key]
                    continue

                # Extract bank_info and saldo_info from smart_mapped (fallback)
                smart_mapped = extracted_data.get('smart_mapped', {})
                if smart_mapped and isinstance(smart_mapped, dict):
                    # Get bank_info (prefer first non-empty)
                    bank_info = smart_mapped.get('bank_info', {})
                    if bank_info and not merged_bank_info:
                        merged_bank_info = bank_info.copy()
                        logger.info(f"  ✅ Found bank_info in chunk {i+1}")

                    # Get saldo_info (prefer last chunk for saldo_akhir, first for saldo_awal)
                    saldo_info = smart_mapped.get('saldo_info', {})
                    if saldo_info:
                        # Always take saldo_awal from first chunk if not set
                        if 'saldo_awal' in saldo_info and not merged_saldo_info.get('saldo_awal'):
                            merged_saldo_info['saldo_awal'] = saldo_info['saldo_awal']
                            logger.info(f"  ✅ Found saldo_awal in chunk {i+1}: {saldo_info['saldo_awal']}")

                        # Always update saldo_akhir from each chunk (last one wins)
                        if 'saldo_akhir' in saldo_info:
                            merged_saldo_info['saldo_akhir'] = saldo_info['saldo_akhir']
                            logger.info(f"  ✅ Found saldo_akhir in chunk {i+1}: {saldo_info['saldo_akhir']}")

                        # Merge other saldo fields
                        for key in ['total_kredit', 'total_debet', 'mata_uang']:
                            if key in saldo_info and not merged_saldo_info.get(key):
                                merged_saldo_info[key] = saldo_info[key]

                    # Get transactions
                    transactions = smart_mapped.get('transactions', [])
                    if transactions:
                        all_transactions.extend(transactions)
                        logger.info(f"  ✅ Found {len(transactions)} transactions in smart_mapped")
                        continue

                # Try structured_data
                structured = extracted_data.get('structured_data', {})
                if structured and isinstance(structured, dict):
                    transactions = structured.get('transaksi', [])
                    if transactions:
                        all_transactions.extend(transactions)
                        logger.info(f"  ✅ Found {len(transactions)} transactions in structured_data")
                        continue

                # Try direct transaksi field
                transactions = extracted_data.get('transaksi', [])
                if transactions:
                    all_transactions.extend(transactions)
                    logger.info(f"  ✅ Found {len(transactions)} transactions")

        # Update merged result
        merged['raw_text'] = '\n'.join(all_raw_text)
        merged['extracted_text'] = merged['raw_text']

        # Update extracted_data with merged transactions, bank_info, and saldo_info
        if 'extracted_data' in merged and isinstance(merged['extracted_data'], dict):
            # Update smart_mapped if it exists
            if 'smart_mapped' in merged['extracted_data']:
                if not isinstance(merged['extracted_data']['smart_mapped'], dict):
                    merged['extracted_data']['smart_mapped'] = {}

                # Set transactions
                merged['extracted_data']['smart_mapped']['transactions'] = all_transactions

                # Set bank_info and saldo_info
                if merged_bank_info:
                    merged['extracted_data']['smart_mapped']['bank_info'] = merged_bank_info
                if merged_saldo_info:
                    merged['extracted_data']['smart_mapped']['saldo_info'] = merged_saldo_info

            # Update structured_data if it exists
            if 'structured_data' in merged['extracted_data']:
                if not isinstance(merged['extracted_data']['structured_data'], dict):
                    merged['extracted_data']['structured_data'] = {}
                merged['extracted_data']['structured_data']['transaksi'] = all_transactions

            # Also set at root level
            merged['extracted_data']['transaksi'] = all_transactions

        logger.info(f"✅ Merged {len(chunk_results)} chunks → {len(all_transactions)} total transactions")
        logger.info(f"✅ Bank info preserved: {bool(merged_bank_info)}")
        logger.info(f"✅ Saldo info preserved: saldo_awal={merged_saldo_info.get('saldo_awal', 'NOT SET')}, saldo_akhir={merged_saldo_info.get('saldo_akhir', 'NOT SET')}")

        return merged


# Global instance - 3 pages per chunk for better detail extraction
pdf_chunker = PDFChunker(max_pages_per_chunk=3)
