import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import { Upload as UploadIcon, FileText, X, Brain, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const documentTypes = [
  { id: 'faktur_pajak', label: 'Faktur Pajak', icon: '📋' },
  { id: 'pph21', label: 'Bukti Potong PPh 21', icon: '📄' },
  { id: 'pph23', label: 'Bukti Potong PPh 23', icon: '📄' },
  { id: 'rekening_koran', label: 'Rekening Koran', icon: '🏦' },
  { id: 'invoice', label: 'Invoice', icon: '🧾' }
];

const Upload = () => {
  const navigate = useNavigate();
  const { uploadDocuments, loading } = useDocument();
  const [selectedFiles, setSelectedFiles] = useState<{ [key: string]: File | null }>({});
  const [dragOver, setDragOver] = useState<string | null>(null);

  const handleFileSelect = (documentType: string, file: File) => {
    setSelectedFiles(prev => ({
      ...prev,
      [documentType]: file
    }));
  };

  const handleFileDrop = (e: React.DragEvent, documentType: string) => {
    e.preventDefault();
    setDragOver(null);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(documentType, files[0]);
    }
  };

  const removeFile = (documentType: string) => {
    setSelectedFiles(prev => {
      const newFiles = { ...prev };
      delete newFiles[documentType];
      return newFiles;
    });
  };


  const handleSubmit = async () => {
    const files = Object.entries(selectedFiles).filter(([_, file]) => file !== null);
    
    if (files.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    try {
      const fileList = files.map(([_, file]) => file!);
      const documentTypes = files.map(([type, _]) => type);
      
      const batch = await uploadDocuments(fileList, documentTypes);
      
      // Navigate to results immediately
      navigate(`/scan-results/${batch.id}`);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 gradient-bg rounded-lg flex items-center justify-center">
            <UploadIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Upload Documents</h1>
            <p className="text-gray-600 mt-1">Upload up to 5 documents for AI-powered scanning</p>
          </div>
        </div>
      </div>

      {/* AI Processing Info */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
        <div className="flex items-center space-x-3 mb-4">
          <Brain className="w-6 h-6 text-blue-600" />
          <h3 className="text-lg font-semibold text-blue-900">AI Processing Pipeline</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-purple-600" />
            <span className="text-sm text-purple-800">LayoutLMv3 + EasyOCR</span>
          </div>
          <div className="flex items-center space-x-2">
            <Brain className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-800">Transformers + LangChain</span>
          </div>
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-green-600" />
            <span className="text-sm text-green-800">spaCy NER Extraction</span>
          </div>
        </div>
      </div>

      {/* Upload Areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {documentTypes.map((docType) => (
          <div key={docType.id} className="bg-white rounded-lg shadow-sm border">
            <div className="p-4 border-b">
              <div className="flex items-center space-x-2">
                <span className="text-lg">{docType.icon}</span>
                <h3 className="font-medium text-gray-900">{docType.label}</h3>
              </div>
            </div>
            
            <div className="p-4">
              {selectedFiles[docType.id] ? (
                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-green-600" />
                    <span className="text-sm font-medium text-green-800">
                      {selectedFiles[docType.id]!.name}
                    </span>
                  </div>
                  <button
                    onClick={() => removeFile(docType.id)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  className={`upload-dropzone p-6 rounded-lg text-center cursor-pointer ${
                    dragOver === docType.id ? 'drag-over' : ''
                  }`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(docType.id);
                  }}
                  onDragLeave={() => setDragOver(null)}
                  onDrop={(e) => handleFileDrop(e, docType.id)}
                  onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.pdf,.jpg,.jpeg,.png';
                    input.onchange = (e) => {
                      const file = (e.target as HTMLInputElement).files?.[0];
                      if (file) {
                        handleFileSelect(docType.id, file);
                      }
                    };
                    input.click();
                  }}
                >
                  <UploadIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 mb-1">Drop file here or click to browse</p>
                  <p className="text-xs text-gray-500">PDF, JPG, PNG up to 10MB</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Submit Button */}
      {Object.keys(selectedFiles).length > 0 && (
        <div className="flex justify-center">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className={`px-8 py-3 rounded-lg font-medium text-white ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'gradient-bg hover:shadow-lg transform hover:scale-105'
            } transition-all duration-200`}
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Processing...</span>
              </div>
            ) : (
              `Start AI Processing (${Object.keys(selectedFiles).length} files)`
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default Upload;