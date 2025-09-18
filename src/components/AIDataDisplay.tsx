import React from 'react';

interface AIFormattedData {
  documentType: string;
  confidence: number;
  originalData: any;
  title: string;
  sections: any[];
  summary: {
    totalAmount?: number;
    keyInsights: string[];
  };
}

interface AIDataDisplayProps {
  data: AIFormattedData;
  className?: string;
}

const AIDataDisplay: React.FC<AIDataDisplayProps> = ({ data, className = '' }) => {
  
  // Recreate the exact same layout pattern as the original renderExtractedData
  const renderByDocumentType = () => {
    const extractedData = data.originalData || {};
    
    if (data.documentType === 'faktur_pajak') {
      return (
        <div className="space-y-6">
          {/* A. Faktur Pajak Keluaran */}
          <div className="bg-green-50 p-6 rounded-lg border border-green-200">
            <h4 className="text-lg font-semibold text-green-900 mb-4">A. Faktur Pajak Keluaran</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-green-700">Nama Lawan Transaksi</label>
                <p className="text-green-900">{extractedData.keluaran?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">No Seri FP</label>
                <p className="text-green-900">{extractedData.keluaran?.no_seri_fp || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-green-700">Alamat</label>
                <p className="text-green-900">{extractedData.keluaran?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">NPWP</label>
                <p className="text-green-900">{extractedData.keluaran?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Quantity</label>
                <p className="text-green-900">{extractedData.keluaran?.quantity || 0}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Diskon</label>
                <p className="text-green-900">Rp {extractedData.keluaran?.diskon?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Harga</label>
                <p className="text-green-900">Rp {extractedData.keluaran?.harga?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">DPP</label>
                <p className="text-green-900">Rp {extractedData.keluaran?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">PPN</label>
                <p className="text-green-900">Rp {extractedData.keluaran?.ppn?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Tgl Faktur</label>
                <p className="text-green-900">{extractedData.keluaran?.tgl_faktur || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-green-700">Keterangan Lain</label>
                <p className="text-green-900">{extractedData.keluaran?.keterangan_lain || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700">Tgl Rekam</label>
                <p className="text-green-900">{extractedData.keluaran?.tgl_rekam || 'N/A'}</p>
              </div>
            </div>
            
            {/* Keterangan Barang Table */}
            {extractedData.keluaran?.keterangan_barang && extractedData.keluaran.keterangan_barang.length > 0 && (
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
                      {extractedData.keluaran.keterangan_barang.map((item: any, index: number) => (
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
            <h4 className="text-lg font-semibold text-blue-900 mb-4">B. Faktur Pajak Masukan</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-blue-700">Nama Lawan Transaksi</label>
                <p className="text-blue-900">{extractedData.masukan?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">No Seri FP</label>
                <p className="text-blue-900">{extractedData.masukan?.no_seri_fp || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Alamat</label>
                <p className="text-blue-900">{extractedData.masukan?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">NPWP</label>
                <p className="text-blue-900">{extractedData.masukan?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Email</label>
                <p className="text-blue-900">{extractedData.masukan?.email || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Quantity</label>
                <p className="text-blue-900">{extractedData.masukan?.quantity || 0}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Diskon</label>
                <p className="text-blue-900">Rp {extractedData.masukan?.diskon?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Harga</label>
                <p className="text-blue-900">Rp {extractedData.masukan?.harga?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">DPP</label>
                <p className="text-blue-900">Rp {extractedData.masukan?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">PPN</label>
                <p className="text-blue-900">Rp {extractedData.masukan?.ppn?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tgl Faktur</label>
                <p className="text-blue-900">{extractedData.masukan?.tgl_faktur || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Keterangan Lain</label>
                <p className="text-blue-900">{extractedData.masukan?.keterangan_lain || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tgl Rekam</label>
                <p className="text-blue-900">{extractedData.masukan?.tgl_rekam || 'N/A'}</p>
              </div>
            </div>
            
            {/* Keterangan Barang Table */}
            {extractedData.masukan?.keterangan_barang && extractedData.masukan.keterangan_barang.length > 0 && (
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
                      {extractedData.masukan.keterangan_barang.map((item: any, index: number) => (
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

    if (data.documentType === 'pph21') {
      return (
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <h4 className="text-lg font-semibold text-yellow-900 mb-4">PPh 21 Data</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-yellow-700">Nomor</label>
              <p className="text-yellow-900">{extractedData.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Masa Pajak</label>
              <p className="text-yellow-900">{extractedData.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Sifat Pemotongan</label>
              <p className="text-yellow-900">{extractedData.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-yellow-700">Status Bukti Pemotongan</label>
              <p className="text-yellow-900">{extractedData.status_bukti_pemotongan || 'N/A'}</p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{extractedData.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nama</label>
                <p className="text-yellow-900">{extractedData.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">NITKU</label>
                <p className="text-yellow-900">{extractedData.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* PPh Information */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Informasi PPh</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">Jenis PPh</label>
                <p className="text-yellow-900">{extractedData.jenis_pph || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Kode Objek Pajak</label>
                <p className="text-yellow-900">{extractedData.kode_objek_pajak || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-yellow-700">Objek Pajak</label>
                <p className="text-yellow-900">{extractedData.objek_pajak || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Penghasilan Bruto</label>
                <p className="text-lg font-semibold text-yellow-900">
                  Rp {typeof extractedData.penghasilan_bruto === 'number' && extractedData.penghasilan_bruto > 0 
                    ? extractedData.penghasilan_bruto.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">DPP</label>
                <p className="text-yellow-900">
                  Rp {typeof extractedData.dpp === 'number' && extractedData.dpp > 0 
                    ? extractedData.dpp.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tarif</label>
                <p className="text-yellow-900">{extractedData.tarif || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">PPh</label>
                <p className="text-lg font-bold text-yellow-900">
                  Rp {typeof extractedData.pph === 'number' && extractedData.pph > 0 
                    ? extractedData.pph.toLocaleString() 
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
                <p className="text-yellow-900">{extractedData.dasar_dokumen?.jenis_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nomor Dokumen</label>
                <p className="text-yellow-900">{extractedData.dasar_dokumen?.nomor_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tanggal Dokumen</label>
                <p className="text-yellow-900">{extractedData.dasar_dokumen?.tanggal_dokumen || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-yellow-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{extractedData.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">NITKU</label>
                <p className="text-yellow-900">{extractedData.identitas_pemotong?.nitku || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Nama Pemotong</label>
                <p className="text-yellow-900">{extractedData.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-yellow-700">Tanggal Pemotongan</label>
                <p className="text-yellow-900">{extractedData.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-yellow-700">Nama Penandatanganan</label>
                <p className="text-yellow-900">{extractedData.identitas_pemotong?.nama_penandatanganan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (data.documentType === 'pph23') {
      return (
        <div className="bg-orange-50 p-6 rounded-lg border border-orange-200">
          <h4 className="text-lg font-semibold text-orange-900 mb-4">PPh 23 Data</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-orange-700">Nomor</label>
              <p className="text-orange-900">{extractedData.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Masa Pajak</label>
              <p className="text-orange-900">{extractedData.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Sifat Pemotongan</label>
              <p className="text-orange-900">{extractedData.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-orange-700">Status Bukti Pemotongan</label>
              <p className="text-orange-900">{extractedData.status_bukti_pemotongan || 'N/A'}</p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{extractedData.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nama</label>
                <p className="text-orange-900">{extractedData.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">NITKU</label>
                <p className="text-orange-900">{extractedData.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* PPh Information */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Informasi PPh</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">Jenis PPh</label>
                <p className="text-orange-900">{extractedData.jenis_pph || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Kode Objek Pajak</label>
                <p className="text-orange-900">{extractedData.kode_objek_pajak || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-orange-700">Objek Pajak</label>
                <p className="text-orange-900">{extractedData.objek_pajak || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">DPP</label>
                <p className="text-orange-900">
                  Rp {typeof extractedData.dpp === 'number' && extractedData.dpp > 0 
                    ? extractedData.dpp.toLocaleString() 
                    : '0'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tarif</label>
                <p className="text-orange-900">{extractedData.tarif || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">PPh</label>
                <p className="text-lg font-bold text-orange-900">
                  Rp {typeof extractedData.pph === 'number' && extractedData.pph > 0 
                    ? extractedData.pph.toLocaleString() 
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
                <p className="text-orange-900">{extractedData.dasar_dokumen?.jenis_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nomor Dokumen</label>
                <p className="text-orange-900">{extractedData.dasar_dokumen?.nomor_dokumen || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tanggal Dokumen</label>
                <p className="text-orange-900">{extractedData.dasar_dokumen?.tanggal_dokumen || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-4">
            <h5 className="text-md font-semibold text-orange-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{extractedData.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">NITKU</label>
                <p className="text-orange-900">{extractedData.identitas_pemotong?.nitku || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Nama Pemotong</label>
                <p className="text-orange-900">{extractedData.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-orange-700">Tanggal Pemotongan</label>
                <p className="text-orange-900">{extractedData.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-orange-700">Nama Penandatanganan</label>
                <p className="text-orange-900">{extractedData.identitas_pemotong?.nama_penandatanganan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (data.documentType === 'rekening_koran') {
      return (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <h4 className="text-lg font-semibold text-blue-900 mb-4">Rekening Koran</h4>
          <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-blue-700">Tanggal</label>
                <p className="text-blue-900">{extractedData.tanggal || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Nilai Uang Masuk</label>
                <p className="text-blue-900">Rp {extractedData.nilai_uang_masuk?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Nilai Uang Keluar</label>
                <p className="text-blue-900">Rp {extractedData.nilai_uang_keluar?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Saldo</label>
                <p className="text-blue-900">Rp {extractedData.saldo?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Sumber Uang Masuk</label>
                <p className="text-blue-900">{extractedData.sumber_uang_masuk || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-blue-700">Tujuan Uang Keluar</label>
                <p className="text-blue-900">{extractedData.tujuan_uang_keluar || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-blue-700">Keterangan</label>
                <p className="text-blue-900">{extractedData.keterangan || 'N/A'}</p>
              </div>
          </div>
        </div>
      );
    }

    if (data.documentType === 'invoice') {
      return (
        <div className="bg-purple-50 p-6 rounded-lg border border-purple-200">
          <h4 className="text-lg font-semibold text-purple-900 mb-4">Invoice</h4>
          <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-purple-700">PO</label>
                <p className="text-purple-900">{extractedData.po || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal PO</label>
                <p className="text-purple-900">{extractedData.tanggal_po || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal Invoice</label>
                <p className="text-purple-900">{extractedData.tanggal_invoice || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Tanggal</label>
                <p className="text-purple-900">{extractedData.tanggal || 'N/A'}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-purple-700">Keterangan</label>
                <p className="text-purple-900">{extractedData.keterangan || 'N/A'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-purple-700">Nilai</label>
                <p className="text-lg font-bold text-purple-900">Rp {extractedData.nilai?.toLocaleString() || '0'}</p>
              </div>
          </div>
        </div>
      );
    }

    // Default rendering for other document types
    return (
      <div className="bg-gray-50 p-6 rounded-lg">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap">
          {JSON.stringify(extractedData, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <div className={className}>
      {renderByDocumentType()}
    </div>
  );
};

export default AIDataDisplay;