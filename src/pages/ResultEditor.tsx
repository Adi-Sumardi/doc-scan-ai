import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader, AlertCircle } from 'lucide-react';
import DocumentPreview from '../components/DocumentPreview';
import EditableOCRResult from '../components/EditableOCRResult.tsx';
import { apiService, ScanResult } from '../services/api';
import toast from 'react-hot-toast';

const ResultEditor = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);

  const toggleEditMode = () => {
    setIsEditMode(prev => !prev);
  };

  useEffect(() => {
    if (id) {
      fetchResult(id);
    }
  }, [id]);

  const fetchResult = async (resultId: string) => {
    try {
      setLoading(true);
      setError(null);
      // Fetch a single result by its ID for efficiency
      const response = await apiService.getResultById(resultId);
      if (response) {
        setResult(response);
      } else {
        setError('Result not found');
      }
    } catch (err) {
      console.error('Error fetching result:', err);
      setError('Failed to load result');
      toast.error('Failed to load result');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (editedData: any) => {
    if (!id) return;
    
    try {
      // TODO: Implement API endpoint to update result
      // await apiService.updateResult(id, editedData);
      
      // For now, just update local state
      setResult(prev => prev ? { ...prev, extracted_data: editedData } : null);
      
      console.log('Saving edited data:', editedData);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.error('Error saving result:', error);
      throw error;
    }
  };

  const handleBack = () => {
    navigate(-1);
  };

  // Get file URL - construct from backend
  const getFileUrl = () => {
    if (!result) return '';
    
    // Pass the API endpoint to fetch the file blob
    return `/api/results/${result.id}/file`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading result...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Result</h2>
          <p className="text-gray-600 mb-6">{error || 'Result not found'}</p>
          <button
            onClick={handleBack}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6 text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Result Editor</h1>
              <p className="text-sm text-gray-600">View and edit OCR extraction results</p>
            </div>
          </div>
        </div>
      </div>

      {/* Split View */}
      <div className="h-[calc(100vh-80px)] flex">
        {/* Left Panel - Document Preview */}
        <div className="w-1/2 p-4">
          <DocumentPreview
            fileUrl={getFileUrl()}
            fileName={result.filename || result.original_filename || 'document'}
            fileType={result.file_type || 'application/pdf'}
          />
        </div>

        {/* Right Panel - Editable Result */}
        <div className="w-1/2 p-4">
          <div className="h-full rounded-lg shadow-lg overflow-hidden">
            <EditableOCRResult
              result={result}
              isEditing={isEditMode}
              onToggleEdit={toggleEditMode}
              onSave={handleSave}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultEditor;
