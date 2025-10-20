"""
Tax Reconciliation API Router
Endpoints untuk rekonsiliasi Faktur Pajak dengan Rekening Koran
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from database import (
    get_db,
    ReconciliationProject,
    TaxInvoice,
    BankTransaction,
    ReconciliationMatch
)
from models import (
    ReconciliationProjectCreate,
    ReconciliationProjectResponse,
    TaxInvoiceCreate,
    TaxInvoiceResponse,
    BankTransactionCreate,
    BankTransactionResponse,
    ReconciliationMatchCreate,
    ReconciliationMatchResponse,
    AutoMatchRequest,
    AutoMatchResponse
)
from reconciliation_service import ReconciliationService
from reconciliation_export import ReconciliationExporter
from auth import get_current_user
from fastapi.responses import FileResponse
from pathlib import Path
import uuid as uuid_lib

router = APIRouter(
    prefix="/api/reconciliation",
    tags=["reconciliation"]
)


# ==================== Projects ====================

@router.post("/projects", response_model=ReconciliationProjectResponse)
async def create_project(
    project: ReconciliationProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create new reconciliation project
    """
    db_project = ReconciliationProject(
        id=str(uuid.uuid4()),
        name=project.name,
        description=project.description,
        period_start=project.period_start,
        period_end=project.period_end,
        status="active",
        user_id=current_user.id
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@router.get("/projects", response_model=List[ReconciliationProjectResponse])
async def list_projects(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List reconciliation projects
    """
    query = db.query(ReconciliationProject)

    # Filter by user (unless admin)
    if not current_user.is_admin:
        query = query.filter(ReconciliationProject.user_id == current_user.id)

    # Filter by status
    if status:
        query = query.filter(ReconciliationProject.status == status)

    # Order by created_at desc
    query = query.order_by(ReconciliationProject.created_at.desc())

    projects = query.offset(skip).limit(limit).all()

    return projects


@router.get("/projects/{project_id}", response_model=ReconciliationProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get project details
    """
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if not current_user.is_admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete project (soft delete - mark as archived)
    """
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if not current_user.is_admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Soft delete
    project.status = "archived"
    db.commit()

    return {"message": "Project archived successfully"}


# ==================== Tax Invoices ====================

@router.post("/invoices", response_model=TaxInvoiceResponse)
async def create_invoice(
    invoice: TaxInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create tax invoice
    """
    # Verify project exists
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == invoice.project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_invoice = TaxInvoice(
        id=str(uuid.uuid4()),
        project_id=invoice.project_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        invoice_type=invoice.invoice_type,
        vendor_name=invoice.vendor_name,
        vendor_npwp=invoice.vendor_npwp,
        dpp=invoice.dpp,
        ppn=invoice.ppn,
        total_amount=invoice.total_amount,
        notes=invoice.notes
    )

    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(invoice.project_id)

    return db_invoice


@router.get("/projects/{project_id}/invoices", response_model=List[TaxInvoiceResponse])
async def list_invoices(
    project_id: str,
    match_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List invoices in project
    """
    query = db.query(TaxInvoice).filter(TaxInvoice.project_id == project_id)

    # Filter by match status
    if match_status:
        query = query.filter(TaxInvoice.match_status == match_status)

    # Order by invoice_date desc
    query = query.order_by(TaxInvoice.invoice_date.desc())

    invoices = query.offset(skip).limit(limit).all()

    return invoices


@router.get("/invoices/{invoice_id}", response_model=TaxInvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get invoice details
    """
    invoice = db.query(TaxInvoice).filter(TaxInvoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete invoice
    """
    invoice = db.query(TaxInvoice).filter(TaxInvoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    project_id = invoice.project_id

    # Delete related matches
    db.query(ReconciliationMatch).filter(
        ReconciliationMatch.invoice_id == invoice_id
    ).delete()

    # Delete invoice
    db.delete(invoice)
    db.commit()

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(project_id)

    return {"message": "Invoice deleted successfully"}


# ==================== Bank Transactions ====================

@router.post("/transactions", response_model=BankTransactionResponse)
async def create_transaction(
    transaction: BankTransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create bank transaction
    """
    # Verify project exists
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == transaction.project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_transaction = BankTransaction(
        id=str(uuid.uuid4()),
        project_id=transaction.project_id,
        bank_name=transaction.bank_name,
        account_number=transaction.account_number,
        account_holder=transaction.account_holder,
        transaction_date=transaction.transaction_date,
        posting_date=transaction.posting_date,
        effective_date=transaction.effective_date,
        description=transaction.description,
        transaction_type=transaction.transaction_type,
        reference_number=transaction.reference_number,
        debit=transaction.debit,
        credit=transaction.credit,
        balance=transaction.balance,
        notes=transaction.notes
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(transaction.project_id)

    return db_transaction


@router.get("/projects/{project_id}/transactions", response_model=List[BankTransactionResponse])
async def list_transactions(
    project_id: str,
    match_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List transactions in project
    """
    query = db.query(BankTransaction).filter(BankTransaction.project_id == project_id)

    # Filter by match status
    if match_status:
        query = query.filter(BankTransaction.match_status == match_status)

    # Order by transaction_date desc
    query = query.order_by(BankTransaction.transaction_date.desc())

    transactions = query.offset(skip).limit(limit).all()

    return transactions


@router.get("/transactions/{transaction_id}", response_model=BankTransactionResponse)
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get transaction details
    """
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete transaction
    """
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    project_id = transaction.project_id

    # Delete related matches
    db.query(ReconciliationMatch).filter(
        ReconciliationMatch.transaction_id == transaction_id
    ).delete()

    # Delete transaction
    db.delete(transaction)
    db.commit()

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(project_id)

    return {"message": "Transaction deleted successfully"}


# ==================== Matching ====================

@router.post("/auto-match", response_model=AutoMatchResponse)
async def auto_match(
    request: AutoMatchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Auto-match invoices with transactions
    """
    service = ReconciliationService(db)

    try:
        result = service.auto_match_project(
            project_id=request.project_id,
            min_confidence=request.min_confidence or 0.70
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-match failed: {str(e)}")


@router.get("/invoices/{invoice_id}/suggestions")
async def get_suggestions(
    invoice_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get suggested matches untuk invoice
    """
    # Get invoice
    invoice = db.query(TaxInvoice).filter(TaxInvoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    service = ReconciliationService(db)

    try:
        suggestions = service.suggest_matches(
            project_id=invoice.project_id,
            invoice_id=invoice_id,
            limit=limit
        )

        # Format response
        result = []
        for transaction, score_details in suggestions:
            result.append({
                'transaction': BankTransactionResponse.from_orm(transaction),
                'score_details': score_details
            })

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/matches", response_model=ReconciliationMatchResponse)
async def create_match(
    match: ReconciliationMatchCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manual match antara invoice dan transaction
    """
    service = ReconciliationService(db)

    try:
        result = service.manual_match(
            project_id=match.project_id,
            invoice_id=match.invoice_id,
            transaction_id=match.transaction_id,
            user_id=current_user.id,
            notes=match.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Match failed: {str(e)}")


@router.get("/projects/{project_id}/matches", response_model=List[ReconciliationMatchResponse])
async def list_matches(
    project_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List matches in project
    """
    query = db.query(ReconciliationMatch).filter(
        ReconciliationMatch.project_id == project_id
    )

    # Filter by status
    if status:
        query = query.filter(ReconciliationMatch.status == status)

    # Order by created_at desc
    query = query.order_by(ReconciliationMatch.created_at.desc())

    matches = query.offset(skip).limit(limit).all()

    return matches


@router.delete("/matches/{match_id}")
async def delete_match(
    match_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Unmatch/reject a match
    """
    # Get match
    match = db.query(ReconciliationMatch).filter(
        ReconciliationMatch.id == match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    service = ReconciliationService(db)

    try:
        service.unmatch(
            project_id=match.project_id,
            match_id=match_id,
            reason=reason
        )
        return {"message": "Match rejected successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/matches/{match_id}/confirm")
async def confirm_match(
    match_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm a match
    """
    match = db.query(ReconciliationMatch).filter(
        ReconciliationMatch.id == match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Update match
    match.confirmed = True
    match.confirmed_by = current_user.id
    match.confirmed_at = datetime.now()

    db.commit()
    db.refresh(match)

    return ReconciliationMatchResponse.from_orm(match)


# ==================== Bulk Import (V2.0 - Enhanced) ====================

@router.post("/projects/{project_id}/import/batch/invoices")
async def import_invoices_from_batch(
    project_id: str,
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Import tax invoices from entire batch (V2.0 - reuses OCR results)
    """
    service = ReconciliationService(db)

    try:
        result = service.import_invoices_from_batch(project_id, batch_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/projects/{project_id}/import/batch/transactions")
async def import_transactions_from_batch(
    project_id: str,
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Import bank transactions from entire batch (V2.0 - reuses OCR results)
    """
    service = ReconciliationService(db)

    try:
        result = service.import_transactions_from_batch(project_id, batch_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/projects/{project_id}/import/invoices")
async def import_invoices_from_scan(
    project_id: str,
    scan_result_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Import invoices dari scan results (faktur pajak yang sudah di-scan)
    """
    from database import ScanResult

    # Verify project
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    imported = 0
    errors = []

    for scan_id in scan_result_ids:
        try:
            # Get scan result
            scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()

            if not scan or scan.document_type != "faktur_pajak":
                errors.append(f"Invalid scan result: {scan_id}")
                continue

            # Extract data
            data = scan.extracted_data or {}

            # Create invoice
            invoice = TaxInvoice(
                id=str(uuid.uuid4()),
                project_id=project_id,
                scan_result_id=scan_id,
                invoice_number=data.get('nomor_faktur', ''),
                invoice_date=datetime.fromisoformat(data.get('tanggal_faktur')) if data.get('tanggal_faktur') else datetime.now(),
                invoice_type=data.get('jenis_transaksi', ''),
                vendor_name=data.get('nama_penjual', ''),
                vendor_npwp=data.get('npwp_penjual', ''),
                dpp=float(data.get('dpp', 0)),
                ppn=float(data.get('ppn', 0)),
                total_amount=float(data.get('total', 0))
            )

            db.add(invoice)
            imported += 1

        except Exception as e:
            errors.append(f"Error importing {scan_id}: {str(e)}")

    db.commit()

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(project_id)

    return {
        'imported': imported,
        'errors': errors,
        'total_requested': len(scan_result_ids)
    }


@router.post("/projects/{project_id}/import/transactions")
async def import_transactions_from_scan(
    project_id: str,
    scan_result_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Import transactions dari scan results (rekening koran yang sudah di-scan)
    """
    from database import ScanResult

    # Verify project
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    imported = 0
    errors = []

    for scan_id in scan_result_ids:
        try:
            # Get scan result
            scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()

            if not scan or scan.document_type != "rekening_koran":
                errors.append(f"Invalid scan result: {scan_id}")
                continue

            # Extract transactions
            data = scan.extracted_data or {}
            transactions_data = data.get('transactions', [])

            for trans_data in transactions_data:
                try:
                    transaction = BankTransaction(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        scan_result_id=scan_id,
                        bank_name=trans_data.get('Bank', ''),
                        account_number=trans_data.get('No Rekening', ''),
                        account_holder=trans_data.get('Nama Pemegang', ''),
                        transaction_date=datetime.strptime(trans_data.get('Tanggal Transaksi', ''), '%d/%m/%Y') if trans_data.get('Tanggal Transaksi') else datetime.now(),
                        posting_date=datetime.strptime(trans_data.get('Tanggal Posting', ''), '%d/%m/%Y') if trans_data.get('Tanggal Posting') else None,
                        description=trans_data.get('Keterangan', ''),
                        transaction_type=trans_data.get('Tipe Transaksi', ''),
                        reference_number=trans_data.get('No Referensi', ''),
                        debit=float(trans_data.get('Debit', 0)),
                        credit=float(trans_data.get('Kredit', 0)),
                        balance=float(trans_data.get('Saldo', 0)) if trans_data.get('Saldo') else None
                    )

                    db.add(transaction)
                    imported += 1

                except Exception as e:
                    errors.append(f"Error importing transaction from {scan_id}: {str(e)}")

        except Exception as e:
            errors.append(f"Error processing {scan_id}: {str(e)}")

    db.commit()

    # Update project statistics
    service = ReconciliationService(db)
    service._update_project_statistics(project_id)

    return {
        'imported': imported,
        'errors': errors,
        'total_requested': len(scan_result_ids)
    }


# ==================== AI-Powered Extraction (V2.0) ====================

@router.post("/projects/{project_id}/ai/extract-vendors")
async def ai_extract_vendors(
    project_id: str,
    batch_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Use GPT-4o to extract clean vendor names from bank transaction descriptions

    Example: "TRANSFER KE PT MAJU JAYA/REF123" -> "PT MAJU JAYA"
    """
    # Verify project
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = ReconciliationService(db)

    try:
        result = service.ai_extract_vendor_from_transactions(project_id, batch_size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")


@router.post("/projects/{project_id}/ai/extract-invoices")
async def ai_extract_invoices(
    project_id: str,
    batch_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Use Claude to extract invoice numbers from bank transaction descriptions/references

    Example: "TRANSFER/INV-2024-001/PT MAJU" -> "INV-2024-001"
    """
    # Verify project
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = ReconciliationService(db)

    try:
        result = service.ai_extract_invoice_from_transactions(project_id, batch_size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")


# ==================== Export ====================

@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Export reconciliation project to Excel
    """
    # Verify project exists
    project = db.query(ReconciliationProject).filter(
        ReconciliationProject.id == project_id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if not current_user.is_admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Get data for export
        invoices = db.query(TaxInvoice).filter(TaxInvoice.project_id == project_id).all()
        transactions = db.query(BankTransaction).filter(BankTransaction.project_id == project_id).all()
        matches = db.query(ReconciliationMatch).filter(
            ReconciliationMatch.project_id == project_id
        ).all()

        # Create exporter (V2.0 - new exporter with AI metadata)
        from exporters.reconciliation_exporter import ReconciliationExporter
        exporter = ReconciliationExporter()

        # Generate export directory if not exists
        from config import get_exports_dir
        exports_dir = Path(get_exports_dir())
        exports_dir.mkdir(exist_ok=True)

        # Generate filename
        filename = f"reconciliation_{project.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = exports_dir / filename

        # Export (V2.0 API)
        success = exporter.export_project_to_excel(
            project=project,
            invoices=invoices,
            transactions=transactions,
            matches=matches,
            output_path=str(output_path)
        )

        if not success:
            raise HTTPException(status_code=500, detail="Export generation failed")

        # Return file
        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
