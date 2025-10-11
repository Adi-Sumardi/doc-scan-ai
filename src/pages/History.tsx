import { useState } from 'react';
import { useDocument } from '../context/DocumentContext';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  Calendar,
  Eye,
  ArrowRight,
  Search,
  Filter,
  Trash2
} from 'lucide-react';

const History = () => {
  const navigate = useNavigate();
  const { batches, deleteBatch, loading } = useDocument();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deletingBatchId, setDeletingBatchId] = useState<string | null>(null);

  const safeBatches = Array.isArray(batches) ? batches : [];

  const filteredBatches = safeBatches.filter(batch => {
    const matchesSearch = batch.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || batch.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const calculateProcessingTime = (batch: any) => {
    if (!batch.completed_at) return 'In progress...';

    const startTime = new Date(batch.created_at);
    const endTime = new Date(batch.completed_at);
    const diffMs = endTime.getTime() - startTime.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);

    if (diffSeconds < 60) return `${diffSeconds}s`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    return `${diffMinutes}m ${diffSeconds % 60}s`;
  };

  const handleDelete = async (batch: any) => {
    const result = await Swal.fire({
      title: 'Delete Batch?',
      html: `
        <div class="text-left">
          <p class="mb-2">Anda yakin ingin menghapus batch ini?</p>
          <div class="bg-gray-100 p-3 rounded-lg mb-3">
            <p class="font-semibold text-gray-900">Batch #${batch.id.slice(-8)}</p>
            <p class="text-sm text-gray-600">${batch.total_files} files</p>
            <p class="text-sm text-red-600">Status: ${batch.status}</p>
          </div>
          <p class="text-red-600 font-semibold">⚠️ Tindakan ini tidak dapat dibatalkan!</p>
        </div>
      `,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#dc2626',
      cancelButtonColor: '#6b7280',
      confirmButtonText: 'Ya, Hapus!',
      cancelButtonText: 'Batal',
      reverseButtons: true
    });

    if (!result.isConfirmed) return;

    try {
      setDeletingBatchId(batch.id);

      // Show loading
      Swal.fire({
        title: 'Menghapus...',
        html: 'Mohon tunggu, batch sedang dihapus...',
        allowOutsideClick: false,
        allowEscapeKey: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });

      await deleteBatch(batch.id);

      // Show success
      Swal.fire({
        title: 'Berhasil!',
        html: `Batch #${batch.id.slice(-8)} telah dihapus.`,
        icon: 'success',
        confirmButtonColor: '#059669',
        timer: 2000,
        timerProgressBar: true
      });
    } catch (error: any) {
      // Show error
      Swal.fire({
        title: 'Gagal!',
        html: `Gagal menghapus batch.<br><small class="text-gray-600">${error.message || 'Terjadi kesalahan'}</small>`,
        icon: 'error',
        confirmButtonColor: '#dc2626'
      });
      console.error('Failed to delete batch:', error);
    } finally {
      setDeletingBatchId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-4 md:p-6 shadow-sm border">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-gray-900">Processing History</h1>
            <p className="text-sm md:text-base text-gray-600 mt-1">Track all your document processing batches</p>
          </div>
          <div className="flex items-center justify-end sm:justify-start">
            <span className="text-xs md:text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">{filteredBatches.length} batches</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-4 md:p-6 shadow-sm border">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 flex-1">
            <div className="relative flex-1 sm:flex-initial sm:min-w-0 sm:w-64">
              <Search className="w-4 h-4 md:w-5 md:h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search batch ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 md:pl-10 pr-4 py-2 text-sm md:text-base border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="relative flex-1 sm:flex-initial sm:min-w-0 sm:w-48">
              <Filter className="w-4 h-4 md:w-5 md:h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full pl-9 md:pl-10 pr-8 py-2 text-sm md:text-base border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* History List */}
      {filteredBatches.length === 0 ? (
        <div className="bg-white rounded-lg p-12 shadow-sm border text-center">
          <Clock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No processing history</h3>
          <p className="text-gray-600">Your processing history will appear here after uploading documents.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Batch
                  </th>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                    Files
                  </th>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">
                    Created
                  </th>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden xl:table-cell">
                    Processing Time
                  </th>
                  <th className="px-3 md:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredBatches.map((batch) => (
                  <tr key={batch.id} className="hover:bg-gray-50">
                    <td className="px-3 md:px-6 py-4">
                      <div className="flex items-center">
                        <FileText className="w-4 h-4 md:w-5 md:h-5 text-gray-400 mr-2 md:mr-3 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            #{batch.id.slice(-8)}
                          </div>
                          <div className="text-xs md:text-sm text-gray-500">
                            <span className="sm:hidden">{batch.processed_files}/{batch.total_files} files</span>
                            <span className="hidden sm:inline">Batch ID</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 md:px-6 py-4 hidden sm:table-cell">
                      <div className="text-sm text-gray-900">
                        {batch.processed_files}/{batch.total_files} files
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${(batch.processed_files / batch.total_files) * 100}%` }}
                        ></div>
                      </div>
                    </td>
                    <td className="px-3 md:px-6 py-4">
                      <div className="flex items-center">
                        {getStatusIcon(batch.status)}
                        <span className={`ml-1 md:ml-2 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(batch.status)}`}>
                          <span className="sm:hidden">{batch.status.charAt(0).toUpperCase()}</span>
                          <span className="hidden sm:inline">{batch.status}</span>
                        </span>
                      </div>
                    </td>
                    <td className="px-3 md:px-6 py-4 hidden lg:table-cell">
                      <div className="flex items-center text-sm text-gray-600">
                        <Calendar className="w-4 h-4 mr-2" />
                        {new Date(batch.created_at).toLocaleDateString()}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(batch.created_at).toLocaleTimeString()}
                      </div>
                    </td>
                    <td className="px-3 md:px-6 py-4 text-sm text-gray-600 hidden xl:table-cell">
                      {calculateProcessingTime(batch)}
                    </td>
                    <td className="px-3 md:px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {(batch.status === 'error' || batch.status === 'failed') && (
                          <button
                            onClick={() => handleDelete(batch)}
                            disabled={deletingBatchId === batch.id || loading}
                            className="inline-flex items-center px-2 md:px-3 py-2 border border-transparent text-xs md:text-sm leading-4 font-medium rounded-md text-red-600 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Delete batch"
                          >
                            <Trash2 className="w-3 h-3 md:w-4 md:h-4" />
                            <span className="hidden sm:inline ml-1">
                              {deletingBatchId === batch.id ? 'Deleting...' : 'Delete'}
                            </span>
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/scan-results/${batch.id}`)}
                          className="inline-flex items-center px-2 md:px-3 py-2 border border-transparent text-xs md:text-sm leading-4 font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                        >
                          <Eye className="w-3 h-3 md:w-4 md:h-4 mr-1" />
                          <span className="hidden sm:inline">View Results</span>
                          <span className="sm:hidden">View</span>
                          <ArrowRight className="w-3 h-3 md:w-4 md:h-4 ml-1" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default History;