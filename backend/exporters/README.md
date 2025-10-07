# 📁 Exporters Module Documentation

## Overview
Modular export system untuk different document types dengan pattern yang clean dan extensible.

## Architecture

```
backend/exporters/
├── __init__.py                    # Module initialization
├── base_exporter.py               # Abstract base class
├── export_factory.py              # Factory pattern untuk auto-select exporter
├── faktur_pajak_exporter.py       # Faktur Pajak implementation
└── pph21_exporter.py              # PPh21 implementation (template)
```

## Design Patterns

### 1. **Factory Pattern** (`export_factory.py`)
- Auto-selects appropriate exporter based on document type
- Easy registration of new exporters
- Fallback to default exporter

### 2. **Template Method Pattern** (`base_exporter.py`)
- Abstract base class defines interface
- Concrete exporters implement specific logic
- Consistent API across all exporters

## Usage Examples

### Single Document Export

```python
from exporters import ExportFactory

# Get appropriate exporter
exporter = ExportFactory.get_exporter("faktur_pajak")

# Export to Excel
result = {
    'extracted_data': {...},
    'document_type': 'Faktur Pajak',
    'confidence': 0.95
}
exporter.export_to_excel(result, "output.xlsx")

# Export to PDF
exporter.export_to_pdf(result, "output.pdf")
```

### Batch Export

```python
# Export multiple documents
results = [result1, result2, result3]

exporter.batch_export_to_excel("batch_123", results, "batch.xlsx")
exporter.batch_export_to_pdf("batch_123", results, "batch.pdf")
```

### Integration with ai_processor.py

```python
from exporters import ExportFactory

# In export functions:
def create_enhanced_excel_export(result, output_path):
    doc_type = result.get('document_type', 'faktur_pajak')
    exporter = ExportFactory.get_exporter(doc_type)
    return exporter.export_to_excel(result, output_path)

def create_enhanced_pdf_export(result, output_path):
    doc_type = result.get('document_type', 'faktur_pajak')
    exporter = ExportFactory.get_exporter(doc_type)
    return exporter.export_to_pdf(result, output_path)
```

## Creating New Exporter

### Step 1: Create Exporter Class

```python
# backend/exporters/bukti_potong_exporter.py

from .base_exporter import BaseExporter

class BuktiPotongExporter(BaseExporter):
    def __init__(self):
        super().__init__("bukti_potong")
        self.columns = ["Nama", "NPWP", "Jumlah", ...]
    
    def export_to_excel(self, result, output_path):
        # Implementation
        pass
    
    def export_to_pdf(self, result, output_path):
        # Implementation
        pass
    
    def batch_export_to_excel(self, batch_id, results, output_path):
        # Implementation
        pass
    
    def batch_export_to_pdf(self, batch_id, results, output_path):
        # Implementation
        pass
```

### Step 2: Register in Factory

```python
# In export_factory.py
from .bukti_potong_exporter import BuktiPotongExporter

class ExportFactory:
    _exporters = {
        "faktur_pajak": FakturPajakExporter,
        "pph21": PPh21Exporter,
        "bukti_potong": BuktiPotongExporter,  # Add here
    }
```

### Step 3: Update __init__.py

```python
# In __init__.py
from .bukti_potong_exporter import BuktiPotongExporter

__all__ = ['ExportFactory', 'FakturPajakExporter', 'PPh21Exporter', 'BuktiPotongExporter']
```

## Current Implementations

### ✅ Faktur Pajak Exporter

**Columns**: 
- Nama, Tgl, NPWP, Nomor Faktur, Alamat
- DPP, PPN, Total, Invoice
- Nama Barang Kena Pajak / Jasa Kena Pajak

**Features**:
- ✅ Single Excel export (10-column table)
- ✅ Single PDF export (compact A4 layout)
- ✅ Batch Excel export (consolidated table)
- ✅ Batch PDF export (multi-row table)
- ✅ Blue navy theme (#1e40af)
- ✅ Alternating row colors
- ✅ Auto-width columns

### 🚧 PPh21 Exporter (Template)

**Columns**: 
- Nama Karyawan, NIK, NPWP, Periode
- Gaji Bruto, Potongan, Gaji Neto
- PTKP, PKP, PPh21, Tanggal

**Status**: Template ready, implementation needed

## Benefits of Modular Design

### 1. **Separation of Concerns**
- Each document type has its own file
- ai_processor.py stays clean and focused
- Easy to test individual exporters

### 2. **Extensibility**
- Add new document types without modifying existing code
- Register exporters dynamically
- Override specific methods as needed

### 3. **Maintainability**
- Changes to one exporter don't affect others
- Clear file structure
- Self-documenting code

### 4. **Reusability**
- Common logic in base class
- Specific logic in concrete classes
- Factory handles selection automatically

## File Size Comparison

### Before Refactor:
```
ai_processor.py: ~1800 lines (all export logic included)
```

### After Refactor:
```
ai_processor.py: ~1200 lines (export logic removed)
exporters/base_exporter.py: ~70 lines
exporters/export_factory.py: ~70 lines
exporters/faktur_pajak_exporter.py: ~600 lines
exporters/pph21_exporter.py: ~120 lines (template)
```

**Total Reduction**: ai_processor.py reduced by ~600 lines! ✨

## Future Exporters

### Planned:
- [ ] PPh21 (Employee Tax)
- [ ] PPh23 (Tax on Services)
- [ ] PPh26 (Foreign Tax)
- [ ] Bukti Potong (Tax Withholding Certificate)
- [ ] Surat Jalan (Delivery Note)
- [ ] Invoice Standar (Standard Invoice)
- [ ] Kwitansi (Receipt)

### Easy to Add:
1. Create new exporter file
2. Inherit from `BaseExporter`
3. Implement 4 required methods
4. Register in factory
5. Done! 🎉

## Error Handling

All exporters have built-in error handling:

```python
try:
    # Export logic
    logger.info("✅ Export successful")
    return True
except Exception as e:
    logger.error(f"❌ Export failed: {e}", exc_info=True)
    return False
```

## Logging

Consistent logging across all exporters:

```python
logger.info(f"✅ {doc_type} Excel export created: {output_path}")
logger.info(f"✅ Batch {doc_type} PDF created with {len(results)} documents")
logger.error(f"❌ {doc_type} export failed: {error}")
logger.warning(f"⚠️ {feature} not yet implemented")
```

## Testing

Each exporter can be tested independently:

```python
# test_faktur_pajak_exporter.py
from exporters import FakturPajakExporter

def test_single_excel_export():
    exporter = FakturPajakExporter()
    result = {...}
    assert exporter.export_to_excel(result, "test.xlsx") == True
```

## Migration from ai_processor.py

To migrate existing code:

1. ✅ Created exporters module structure
2. ✅ Moved Faktur Pajak export logic to dedicated file
3. ⏳ Update ai_processor.py to use ExportFactory
4. ⏳ Remove old export functions from ai_processor.py
5. ⏳ Test all export functionality

## Summary

✨ **Benefits**:
- Clean separation of concerns
- Easy to add new document types
- Reduced ai_processor.py complexity
- Better maintainability
- Self-documenting structure

🎯 **Next Steps**:
1. Update ai_processor.py to use ExportFactory
2. Test all export functions
3. Implement PPh21 exporter
4. Add more document types as needed

---

**Last Updated**: October 2025  
**Version**: 1.0.0  
**Status**: ✅ Ready for Integration
