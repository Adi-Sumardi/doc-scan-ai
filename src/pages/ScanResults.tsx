import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertCircle,
  Brain,
  Database,
  Share2
} from 'lucide-react';

const ScanResults = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { getBatch, getScanResultsByBatch, exportResult, exportBatch, saveToGoogleDrive, refreshBatch, loading } = useDocument();
  const [activeTab, setActiveTab] = useState(0);

  const batch = getBatch(batchId!);
  const scanResults = getScanResultsByBatch(batchId!);

  // Refresh batch data periodically if still processing
  useEffect(() => {
    if (!batch) return;
    
    if (batch.status === 'processing') {
      const interval = setInterval(() => {
        refreshBatch(batchId!);
      }, 3000);
      
      return () => clearInterval(interval);
    }
  }, [batch?.status, batchId, refreshBatch]);

  if (!batch) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Batch not found</h3>
          <p className="text-gray-600">The requested batch could not be found.</p>
        </div>
      </div>
    );
  }

  const handleDownload = async (format: 'excel' | 'pdf', result?: any) => {
    if (result) {
      await exportResult(result.id, format);
    } else {
      await exportBatch(batchId!, 'excel');
    }
  };

  const handleGoogleDriveShare = async (format: 'excel' | 'pdf', result?: any) => {
    if (result) {
      await saveToGoogleDrive(result.id, format);
    }
  };

  const renderExtractedData = (result: any) => {
    const data = result.extracted_data;
    
    if (result.document_type === 'faktur_pajak') {
      return (
        <div className="space-y-6">
          {/* A. Faktur Pajak Keluaran */}
          <div className="bg-green-50 p-6 rounded-lg border border-green-200">
            <h4 className="text-lg font-semibold text-green-900 mb-4">A. Faktur Pajak Keluaran (data pengusaha kena pajak)</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-green-700">Nama Lawan Transaksi</label>
                <p className="text-green-900">{data.keluaran?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">No Seri FP</label>
                <p className="text-green-900">{data.keluaran?.no_seri_fp || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-green-700">Alamat</label>
                <p className="text-green-900">{data.keluaran?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">NPWP</label>
                <p className="text-green-900">{data.keluaran?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Quantity</label>
                <p className="text-green-900">{data.keluaran?.quantity || 0}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Diskon</label>
                <p className="text-green-900">Rp {data.keluaran?.diskon?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Harga</label>
                <p className="text-green-900">Rp {data.keluaran?.harga?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">DPP</label>
                <p className="text-green-900">Rp {data.keluaran?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">PPN</label>
                <p className="text-green-900">Rp {data.keluaran?.ppn?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Tgl Faktur</label>
                <p className="text-green-900">{data.keluaran?.tgl_faktur || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-green-700">Keterangan Lain</label>
                <p className="text-green-900">{data.keluaran?.keterangan_lain || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Tgl Rekam</label>
                <p className="text-green-900">{data.keluaran?.tgl_rekam || 'N/A'}</p>
              </div>
            </div>
            
            {/* Keterangan Barang Table */}
            {data.keluaran?.keterangan_barang && data.keluaran.keterangan_barang.length > 0 && (
              <div className="mt-4">
                <h5 className="text-md font-semibold text-green-900 mb-2">Keterangan Barang</h5>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border border-green-300">
                    <thead className="bg-green-100">
                      <tr>
                        <th className="px-3 py-2 text-left border-r border-green-300">No.</th>
                        <th className="px-3 py-2 text-left border-r border-green-300">Kode Barang/Jasa</th>
                        <th className="px-3 py-2 text-left border-r border-green-300">Nama Barang kena pajak/Jasa kena pajak</th>
                        <th className="px-3 py-2 text-right">Harga Jual / Penggantian / Uang Muka / Termin (Rp)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.keluaran.keterangan_barang.map((item: any, index: number) => (
                        <tr key={index} className="border-t border-green-200">
                          <td className="px-3 py-2 border-r border-green-200">{item.no}</td>
                          <td className="px-3 py-2 border-r border-green-200">{item.kode_barang_jasa}</td>
                          <td className="px-3 py-2 border-r border-green-200">{item.nama_barang_kena_pajak_jasa_kena_pajak}</td>
                          <td className="px-3 py-2 text-right">Rp {item.harga_jual_penggantian_uang_muka_termin?.toLocaleString() || '0'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* B. Faktur Pajak Masukan */}
          <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
            <h4 className="text-lg font-semibold text-blue-900 mb-4">B. Faktur Pajak Masukan (data pembeli barang kena pajak / penerima jasa kena pajak)</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-blue-700">Nama Lawan Transaksi</label>
                <p className="text-blue-900">{data.masukan?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">No Seri FP</label>
                <p className="text-blue-900">{data.masukan?.no_seri_fp || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Alamat</label>
                <p className="text-blue-900">{data.masukan?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">NPWP</label>
                <p className="text-blue-900">{data.masukan?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Email</label>
                <p className="text-blue-900">{data.masukan?.email || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Quantity</label>
                <p className="text-blue-900">{data.masukan?.quantity || 0}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Diskon</label>
                <p className="text-blue-900">Rp {data.masukan?.diskon?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Harga</label>
                <p className="text-blue-900">Rp {data.masukan?.harga?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">DPP</label>
                <p className="text-blue-900">Rp {data.masukan?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">PPN</label>
                <p className="text-blue-900">Rp {data.masukan?.ppn?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tgl Faktur</label>
                <p className="text-blue-900">{data.masukan?.tgl_faktur || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Keterangan Lain</label>
                <p className="text-blue-900">{data.masukan?.keterangan_lain || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tgl Rekam</label>
                <p className="text-blue-900">{data.masukan?.tgl_rekam || 'N/A'}</p>
              </div>
            </div>
            
            {/* Keterangan Barang Table */}
            {data.masukan?.keterangan_barang && data.masukan.keterangan_barang.length > 0 && (
              <div className="mt-4">
                <h5 className="text-md font-semibold text-blue-900 mb-2">Keterangan Barang</h5>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border border-blue-300">
                    <thead className="bg-blue-100">
                      <tr>
                        <th className="px-3 py-2 text-left border-r border-blue-300">No.</th>
                        <th className="px-3 py-2 text-left border-r border-blue-300">Kode Barang/Jasa</th>
                        <th className="px-3 py-2 text-left border-r border-blue-300">Nama Barang kena pajak/Jasa kena pajak</th>
                        <th className="px-3 py-2 text-right">Harga Jual / Penggantian / Uang Muka / Termin (Rp)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.masukan.keterangan_barang.map((item: any, index: number) => (
                        <tr key={index} className="border-t border-blue-200">
                          <td className="px-3 py-2 border-r border-blue-200">{item.no}</td>
                          <td className="px-3 py-2 border-r border-blue-200">{item.kode_barang_jasa}</td>
                          <td className="px-3 py-2 border-r border-blue-200">{item.nama_barang_kena_pajak_jasa_kena_pajak}</td>
                          <td className="px-3 py-2 text-right">Rp {item.harga_jual_penggantian_uang_muka_termin?.toLocaleString() || '0'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    if (result.document_type === 'pph21') {
      return (
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <h4 className="text-lg font-semibold text-yellow-900 mb-4">PPh 21 Data</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-yellow-700">Nomor</label>
              <p className="text-yellow-900">{data.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Masa Pajak</label>
              <p className="text-yellow-900">{data.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Sifat Pemotongan</label>
              <p className="text-yellow-900">{data.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Status Bukti Pemotongan</label>
              <p className="text-yellow-900">{data.status_bukti_pemotongan || 'N/A'}</p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nama</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">NITKU</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* PPh Information */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Informasi PPh</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">Jenis PPh</label>
                <p className="text-yellow-900">{data.jenis_pph || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Kode Objek Pajak</label>
                <p className="text-yellow-900">{data.kode_objek_pajak || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-yellow-700">Objek Pajak</label>
                <p className="text-yellow-900">{data.objek_pajak || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Penghasilan Bruto</label>
                <p className="text-lg font-semibold text-yellow-900">
                  Rp {typeof data.penghasilan_bruto === 'number' && data.penghasilan_bruto > 0 
                    ? data.penghasilan_bruto.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">DPP</label>
                <p className="text-yellow-900">
                  Rp {typeof data.dpp === 'number' && data.dpp > 0 
                    ? data.dpp.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tarif</label>
                <p className="text-yellow-900">{data.tarif || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">PPh</label>
                <p className="text-lg font-bold text-yellow-900">
                  Rp {typeof data.pph === 'number' && data.pph > 0 
                    ? data.pph.toLocaleString() 
                    : '0'}
                </p>
              </div>
            </div>
          </div>
          
          {/* Dasar Dokumen */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Dasar Dokumen</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">Jenis Dokumen</label>
                <p className="text-yellow-900">{data.dasar_dokumen?.jenis_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nomor Dokumen</label>
                <p className="text-yellow-900">{data.dasar_dokumen?.nomor_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tanggal Dokumen</label>
                <p className="text-yellow-900">{data.dasar_dokumen?.tanggal_dokumen || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">NITKU</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.nitku || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nama Pemotong</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tanggal Pemotongan</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-yellow-700">Nama Penandatanganan</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.nama_penandatanganan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'pph23') {
      return (
        <div className="bg-orange-50 p-6 rounded-lg border border-orange-200">
          <h4 className="text-lg font-semibold text-orange-900 mb-4">PPh 23 Data</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-orange-700">Nomor</label>
              <p className="text-orange-900">{data.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Masa Pajak</label>
              <p className="text-orange-900">{data.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Sifat Pemotongan</label>
              <p className="text-orange-900">{data.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Status Bukti Pemotongan</label>
              <p className="text-orange-900">{data.status_bukti_pemotongan || 'N/A'}</p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nama</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">NITKU</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* PPh Information */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Informasi PPh</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">Jenis PPh</label>
                <p className="text-orange-900">{data.jenis_pph || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Kode Objek Pajak</label>
                <p className="text-orange-900">{data.kode_objek_pajak || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-orange-700">Objek Pajak</label>
                <p className="text-orange-900">{data.objek_pajak || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">DPP</label>
                <p className="text-orange-900">
                  Rp {typeof data.dpp === 'number' && data.dpp > 0 
                    ? data.dpp.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tarif</label>
                <p className="text-orange-900">{data.tarif || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">PPh</label>
                <p className="text-lg font-bold text-orange-900">
                  Rp {typeof data.pph === 'number' && data.pph > 0 
                    ? data.pph.toLocaleString() 
                    : '0'}
                </p>
              </div>
            </div>
          </div>
          
          {/* Dasar Dokumen */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Dasar Dokumen</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">Jenis Dokumen</label>
                <p className="text-orange-900">{data.dasar_dokumen?.jenis_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nomor Dokumen</label>
                <p className="text-orange-900">{data.dasar_dokumen?.nomor_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tanggal Dokumen</label>
                <p className="text-orange-900">{data.dasar_dokumen?.tanggal_dokumen || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{data.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">NITKU</label>
                <p className="text-orange-900">{data.identitas_pemotong?.nitku || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nama Pemotong</label>
                <p className="text-orange-900">{data.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tanggal Pemotongan</label>
                <p className="text-orange-900">{data.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-orange-700">Nama Penandatanganan</label>
                <p className="text-orange-900">{data.identitas_pemotong?.nama_penandatanganan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'rekening_koran') {
      return (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <h4 className="text-lg font-semibold text-blue-900 mb-4">Rekening Koran</h4>
          <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-blue-700">Tanggal</label>
                <p className="text-blue-900">{data.tanggal || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Nilai Uang Masuk</label>
                <p className="text-blue-900">Rp {data.nilai_uang_masuk?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Nilai Uang Keluar</label>
                <p className="text-blue-900">Rp {data.nilai_uang_keluar?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Saldo</label>
                <p className="text-blue-900">Rp {data.saldo?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Sumber Uang Masuk</label>
                <p className="text-blue-900">{data.sumber_uang_masuk || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tujuan Uang Keluar</label>
                <p className="text-blue-900">{data.tujuan_uang_keluar || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Keterangan</label>
                <p className="text-blue-900">{data.keterangan || 'N/A'}</p>
              </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'invoice') {
      return (
        <div className="bg-purple-50 p-6 rounded-lg border border-purple-200">
          <h4 className="text-lg font-semibold text-purple-900 mb-4">Invoice</h4>
          <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-purple-700">PO</label>
                <p className="text-purple-900">{data.po || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal PO</label>
                <p className="text-purple-900">{data.tanggal_po || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal Invoice</label>
                <p className="text-purple-900">{data.tanggal_invoice || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal</label>
                <p className="text-purple-900">{data.tanggal || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-purple-700">Keterangan</label>
                <p className="text-purple-900">{data.keterangan || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Nilai</label>
                <p className="text-lg font-bold text-purple-900">Rp {data.nilai?.toLocaleString() || '0'}</p>
              </div>
          </div>
        </div>
      );
    }

    // Default rendering for other document types
    return (
      <div className="bg-gray-50 p-6 rounded-lg">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Scan Results</h1>
              <p className="text-gray-600 mt-1">Batch #{batchId?.slice(-8)} - {batch.total_files} files</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {batch.status === 'completed' ? (
              <div className="flex items-center space-x-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Completed</span>
              </div>
            ) : batch.status === 'processing' ? (
              <div className="flex items-center space-x-2 text-yellow-600">
                <Clock className="w-5 h-5 processing-animation" />
                <span className="font-medium">Processing...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-red-600">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">Error</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Processing Status */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Processing Progress</h3>
          <span className="text-sm text-gray-600">{batch.processed_files}/{batch.total_files} completed</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${(batch.processed_files / batch.total_files) * 100}%` }}
          ></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-blue-600" />
            <span className="text-sm text-blue-700">AI Analysis Complete</span>
          </div>
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-green-600" />
            <span className="text-sm text-green-700">Data Extracted</span>
          </div>
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-purple-600" />
            <span className="text-sm text-purple-700">Ready for Export</span>
          </div>
        </div>
      </div>

      {/* Results */}
      {scanResults.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Extracted Data</h3>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleDownload('excel')}
                  disabled={loading}
                  className="px-4 py-2 success-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Download All (Excel)
                </button>
                <button
                  onClick={() => handleDownload('pdf')}
                  disabled={loading}
                  className="px-4 py-2 error-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Download All (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b">
            <nav className="flex space-x-8 px-6">
              {scanResults.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => setActiveTab(index)}
                  className={`py-4 text-sm font-medium border-b-2 ${
                    activeTab === index
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {result.original_filename}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {scanResults[activeTab] && (
              <div className="space-y-6">
                {/* File Info */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-6 h-6 text-blue-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">{scanResults[activeTab].original_filename}</h4>
                      <p className="text-sm text-gray-600">Confidence: {(scanResults[activeTab].confidence * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleDownload('excel', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                    >
                      <Download className="w-4 h-4 inline mr-1" />
                      Excel
                    </button>
                    <button
                      onClick={() => handleDownload('pdf', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                    >
                      <Download className="w-4 h-4 inline mr-1" />
                      PDF
                    </button>
                    <button
                      onClick={() => handleGoogleDriveShare('excel', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                    >
                      <Share2 className="w-4 h-4 inline mr-1" />
                      Save to Drive
                    </button>
                  </div>
                </div>

                {/* Extracted Data */}
                {renderExtractedData(scanResults[activeTab])}
              </div>
            )}
          </div>
        </div>
      )}

      {/* No Results */}
      {batch.status === 'completed' && scanResults.length === 0 && (
        <div className="bg-white rounded-lg p-12 shadow-sm border text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No scan results available</h3>
          <p className="text-gray-600">The processing completed but no results were generated.</p>
        </div>
      )}
    </div>
  );
};

export default ScanResults;