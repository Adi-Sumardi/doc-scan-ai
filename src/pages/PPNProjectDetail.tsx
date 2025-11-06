import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, PlayCircle, FileSpreadsheet, CheckCircle, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import DataSourceSelector, { SelectedDataSources } from '../components/ppn/DataSourceSelector';
import ReconciliationResults from '../components/ppn/ReconciliationResults';

interface Project {
  id: string;
  name: string;
  periode_start: string;
  periode_end: string;
  company_npwp: string;
  status: 'draft' | 'in_progress' | 'completed';
  created_at: string;
  point_a_count?: number;
  point_b_count?: number;
  point_c_count?: number;
  point_e_count?: number;
}

const PPNProjectDetail = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSources, setSelectedSources] = useState<SelectedDataSources>({
    point_a_b_source: null,
    point_c_source: null,
    point_e_source: null,
  });
  const [isReconciling, setIsReconciling] = useState(false);
  const [reconciliationResults, setReconciliationResults] = useState<any>(null);
  const [useAI, setUseAI] = useState(true); // Enable AI by default

  useEffect(() => {
    if (projectId) {
      fetchProject();
    }
  }, [projectId]);

  const fetchProject = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/reconciliation-ppn/projects/${projectId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch project');
      }

      const data = await response.json();
      setProject(data);
    } catch (error) {
      console.error('Failed to fetch project:', error);
      toast.error('Failed to load project details');
      navigate('/ppn-reconciliation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDataSelected = (sources: SelectedDataSources) => {
    setSelectedSources(sources);
  };

  const canRunReconciliation = () => {
    // At minimum, need Point A/B source (Faktur Pajak)
    return selectedSources.point_a_b_source !== null;
  };

  const handleRunReconciliation = async () => {
    if (!canRunReconciliation()) {
      toast.error('Please select at least Faktur Pajak data source');
      return;
    }

    setIsReconciling(true);
    try {
      const token = localStorage.getItem('token');

      // Build FormData for file uploads
      const formData = new FormData();
      formData.append('project_id', projectId!);

      // Handle Point A & B (Faktur Pajak)
      if (selectedSources.point_a_b_source) {
        if (selectedSources.point_a_b_source.type === 'upload' && selectedSources.point_a_b_source.uploaded_file) {
          formData.append('faktur_pajak_file', selectedSources.point_a_b_source.uploaded_file);
        } else if (selectedSources.point_a_b_source.type === 'scanned' && selectedSources.point_a_b_source.file_id) {
          formData.append('faktur_pajak_file_id', selectedSources.point_a_b_source.file_id);
        }
      }

      // Handle Point C (Bukti Potong)
      if (selectedSources.point_c_source) {
        if (selectedSources.point_c_source.type === 'upload' && selectedSources.point_c_source.uploaded_file) {
          formData.append('bukti_potong_file', selectedSources.point_c_source.uploaded_file);
        } else if (selectedSources.point_c_source.type === 'scanned' && selectedSources.point_c_source.file_id) {
          formData.append('bukti_potong_file_id', selectedSources.point_c_source.file_id);
        }
      }

      // Handle Point E (Rekening Koran)
      if (selectedSources.point_e_source) {
        if (selectedSources.point_e_source.type === 'upload' && selectedSources.point_e_source.uploaded_file) {
          formData.append('rekening_koran_file', selectedSources.point_e_source.uploaded_file);
        } else if (selectedSources.point_e_source.type === 'scanned' && selectedSources.point_e_source.file_id) {
          formData.append('rekening_koran_file_id', selectedSources.point_e_source.file_id);
        }
      }

      // Add AI toggle
      formData.append('use_ai', String(useAI));

      const response = await fetch('/api/reconciliation-ppn/reconcile-with-files', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
          // Note: Don't set Content-Type - browser will set it with boundary for multipart/form-data
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to run reconciliation');
      }

      const result = await response.json();

      // Refresh project to get updated counts
      await fetchProject();

      // Store results to display
      setReconciliationResults(result);

      toast.success('Reconciliation completed successfully!');

    } catch (error: any) {
      console.error('Failed to run reconciliation:', error);
      toast.error(error.message || 'Failed to run reconciliation');
    } finally {
      setIsReconciling(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="text-center py-20">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Project Not Found</h2>
          <p className="text-gray-600 mb-6">The project you're looking for doesn't exist or you don't have access to it.</p>
          <button
            onClick={() => navigate('/ppn-reconciliation')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const getStatusBadge = () => {
    const statusColors = {
      draft: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800'
    };

    const statusIcons = {
      draft: null,
      in_progress: <PlayCircle className="w-4 h-4" />,
      completed: <CheckCircle className="w-4 h-4" />
    };

    return (
      <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${statusColors[project.status]}`}>
        {statusIcons[project.status]}
        {project.status.charAt(0).toUpperCase() + project.status.slice(1).replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <button
          onClick={() => navigate('/ppn-reconciliation')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Projects
        </button>

        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
                  <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 break-words">{project.name}</h1>
                </div>
                {getStatusBadge()}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mt-4">
                <div>
                  <p className="text-xs sm:text-sm text-gray-500">Period</p>
                  <p className="text-sm sm:text-base font-medium text-gray-900 break-words">
                    {new Date(project.periode_start).toLocaleDateString()} - {new Date(project.periode_end).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs sm:text-sm text-gray-500">Company NPWP</p>
                  <p className="text-sm sm:text-base font-medium text-gray-900 break-words">{project.company_npwp}</p>
                </div>
                <div className="sm:col-span-2 lg:col-span-1">
                  <p className="text-xs sm:text-sm text-gray-500">Created</p>
                  <p className="text-sm sm:text-base font-medium text-gray-900">
                    {new Date(project.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Data Counts */}
              {(project.point_a_count || project.point_b_count || project.point_c_count || project.point_e_count) ? (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-500 mb-2">Data Summary</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {project.point_a_count ? (
                      <div className="bg-blue-50 rounded-lg p-3">
                        <p className="text-xs text-blue-600 font-medium">Point A (Keluaran)</p>
                        <p className="text-2xl font-bold text-blue-900">{project.point_a_count}</p>
                      </div>
                    ) : null}
                    {project.point_b_count ? (
                      <div className="bg-green-50 rounded-lg p-3">
                        <p className="text-xs text-green-600 font-medium">Point B (Masukan)</p>
                        <p className="text-2xl font-bold text-green-900">{project.point_b_count}</p>
                      </div>
                    ) : null}
                    {project.point_c_count ? (
                      <div className="bg-purple-50 rounded-lg p-3">
                        <p className="text-xs text-purple-600 font-medium">Point C (Bukti Potong)</p>
                        <p className="text-2xl font-bold text-purple-900">{project.point_c_count}</p>
                      </div>
                    ) : null}
                    {project.point_e_count ? (
                      <div className="bg-orange-50 rounded-lg p-3">
                        <p className="text-xs text-orange-600 font-medium">Point E (Rekening Koran)</p>
                        <p className="text-2xl font-bold text-orange-900">{project.point_e_count}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {/* Data Source Selection */}
      <div className="bg-white rounded-xl shadow-md border border-gray-200 p-4 sm:p-6 mb-6">
        <div className="mb-6">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Select Data Sources</h2>
          <p className="text-gray-600">
            Choose data sources for reconciliation. You can select from previously scanned files or upload new Excel files.
          </p>
        </div>

        <DataSourceSelector
          companyNpwp={project.company_npwp}
          onDataSelected={handleDataSelected}
        />
      </div>

      {/* Action Buttons */}
      {!reconciliationResults && (
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1">Ready to Reconcile?</h3>
              <p className="text-xs sm:text-sm text-gray-600">
                {canRunReconciliation()
                  ? 'Click the button to start PPN reconciliation process'
                  : 'Please select at least Faktur Pajak data source to continue'}
              </p>
            </div>

            {/* AI Toggle Switch */}
            <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="ai-toggle"
                  checked={useAI}
                  onChange={(e) => setUseAI(e.target.checked)}
                  className="w-5 h-5 text-purple-600 bg-gray-100 border-gray-300 rounded focus:ring-purple-500 focus:ring-2 cursor-pointer"
                />
                <label htmlFor="ai-toggle" className="text-sm font-medium text-gray-900 cursor-pointer select-none">
                  🤖 Use AI-Enhanced Matching (GPT-4o)
                </label>
              </div>
              {useAI && (
                <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded-full">
                  With Auto Fallback
                </span>
              )}
            </div>

            <button
              onClick={handleRunReconciliation}
              disabled={!canRunReconciliation() || isReconciling}
              className="flex items-center justify-center gap-2 px-6 sm:px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600 shadow-md w-full sm:w-auto whitespace-nowrap"
            >
              {isReconciling ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm sm:text-base">Processing...</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-5 h-5" />
                  <span className="text-sm sm:text-base">Run Reconciliation</span>
                </>
              )}
            </button>
          </div>

          {/* Info Box */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4">
            <h4 className="text-xs sm:text-sm font-semibold text-blue-900 mb-2">What happens next?</h4>
            <ul className="text-xs sm:text-sm text-blue-800 space-y-1">
              <li>• Faktur Pajak will be automatically split into Point A (Keluaran) and Point B (Masukan)</li>
              <li>• Point A will be matched with Point C (Bukti Potong) based on buyer NPWP</li>
              <li>• Point B will be matched with Point E (Rekening Koran) based on date and amount</li>
              <li>• You'll receive a detailed report with matched and unmatched items</li>
            </ul>
          </div>
        </div>
      )}

      {/* Reconciliation Results */}
      {reconciliationResults && (
        <div>
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Reconciliation Results</h2>
            <button
              onClick={() => setReconciliationResults(null)}
              className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors w-full sm:w-auto whitespace-nowrap"
            >
              Run New Reconciliation
            </button>
          </div>
          <ReconciliationResults results={reconciliationResults} />
        </div>
      )}
    </div>
  );
};

export default PPNProjectDetail;
