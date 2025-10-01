import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import { Upload as UploadIcon, FileText, X, Brain, Zap, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const documentTypes = [
  { 
    id: 'faktur_pajak', 
    label: 'Faktur Pajak', 
    icon: '📋',
    accuracy: '99.6%',
    description: 'Optimized for Indonesian tax invoices'
  },
  { 
    id: 'pph21', 
    label: 'Bukti Potong PPh 21', 
    icon: '📄',
    accuracy: '95%+',
    description: 'Income tax withholding certificates'
  },
  { 
    id: 'pph23', 
    label: 'Bukti Potong PPh 23', 
    icon: '📄',
    accuracy: '95%+',
    description: 'Service tax withholding certificates'
  },
  { 
    id: 'rekening_koran', 
    label: 'Rekening Koran', 
    icon: '🏦',
    accuracy: '90%+',
    description: 'Bank account statements'
  },
  { 
    id: 'invoice', 
    label: 'Invoice', 
    icon: '🧾',
    accuracy: '85%+',
    description: 'General business invoices'
  }
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

      {/* AI DocScan Info */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6 border border-purple-200">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-purple-900">AI DocScan System</h3>
            <p className="text-sm text-purple-700">High accuracy for Indonesian tax documents</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="bg-white/50 rounded-lg p-3 border border-purple-100">
            <div className="flex items-center space-x-2 mb-2">
              <Zap className="w-4 h-4 text-orange-500" />
              <span className="text-sm font-medium text-purple-800">Lightning Speed</span>
            </div>
            <p className="text-xs text-purple-600">Ultra-fast document processing</p>
          </div>
          
          <div className="bg-white/50 rounded-lg p-3 border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <Brain className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium text-blue-800">Smart Recognition</span>
            </div>
            <p className="text-xs text-blue-600">Multilingual Indonesian + English</p>
          </div>
          
          <div className="bg-white/50 rounded-lg p-3 border border-green-100">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-800">Advanced AI</span>
            </div>
            <p className="text-xs text-green-600">Document structure analysis</p>
          </div>
          
          <div className="bg-white/50 rounded-lg p-3 border border-indigo-100">
            <div className="flex items-center space-x-2 mb-2">
              <Zap className="w-4 h-4 text-indigo-500" />
              <span className="text-sm font-medium text-indigo-800">Ensemble AI</span>
            </div>
            <p className="text-xs text-indigo-600">Multiple engine fusion</p>
          </div>
        </div>
        
        <div className="bg-white/30 rounded-lg p-3 border border-purple-100">
          <div className="flex items-center justify-center space-x-4 text-sm">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-purple-700">Faktur Pajak: 99.6%</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-purple-700">PPh 21/23: 90%+</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="text-purple-700">Processing: 3-5s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Areas with Enhanced Animation */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {documentTypes.map((docType, index) => (
          <div 
            key={docType.id} 
            className="bg-white rounded-lg shadow-sm border hover:shadow-xl transition-all duration-300 transform hover:scale-105 animate-scale-in"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className="p-4 border-b bg-gradient-to-r from-gray-50 to-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-2xl animate-bounce-once">{docType.icon}</span>
                  <div>
                    <h3 className="font-medium text-gray-900">{docType.label}</h3>
                    <p className="text-xs text-gray-500">{docType.description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-green-600 flex items-center gap-1">
                    {docType.accuracy}
                    <CheckCircle className="w-3 h-3" />
                  </div>
                  <div className="text-xs text-gray-500">accuracy</div>
                </div>
              </div>
            </div>
            
            <div className="p-4">
              {selectedFiles[docType.id] ? (
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border-2 border-green-300 shadow-md animate-scale-in hover:shadow-lg transition-all duration-300">
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <FileText className="w-6 h-6 text-green-600 animate-bounce-once" />
                      <CheckCircle className="w-3 h-3 text-green-600 absolute -top-1 -right-1 animate-pulse" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-green-900 block">
                        {selectedFiles[docType.id]!.name}
                      </span>
                      <span className="text-xs text-green-700">
                        {(selectedFiles[docType.id]!.size / 1024).toFixed(1)} KB • Ready to scan
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(docType.id)}
                    className="text-red-500 hover:text-red-700 hover:bg-red-100 p-2 rounded-full transition-all duration-200 hover:scale-110"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  className={`upload-dropzone p-6 rounded-lg text-center cursor-pointer transition-all duration-300 relative ${
                    dragOver === docType.id 
                      ? 'drag-over scale-105 border-4 border-blue-400 bg-blue-50 shadow-lg' 
                      : 'hover:border-purple-300 hover:bg-purple-50 hover:scale-102'
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
                  <UploadIcon className={`w-8 h-8 mx-auto mb-2 transition-all duration-300 ${
                    dragOver === docType.id 
                      ? 'text-blue-500 animate-bounce scale-110' 
                      : 'text-gray-400 group-hover:text-purple-500'
                  }`} />
                  <p className="text-sm text-gray-600 mb-1 font-medium">
                    {dragOver === docType.id ? '🎯 Drop it here!' : 'Drop file here or click to browse'}
                  </p>
                  <p className="text-xs text-gray-500">PDF, JPG, PNG up to 10MB</p>
                  
                  {/* Animated corners */}
                  {dragOver === docType.id && (
                    <>
                      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-blue-500 animate-pulse" />
                      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-blue-500 animate-pulse" />
                      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-blue-500 animate-pulse" />
                      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-blue-500 animate-pulse" />
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Submit Button with Enhanced Animation */}
      {Object.keys(selectedFiles).length > 0 && (
        <div className="flex justify-center animate-fade-in-up">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className={`relative px-8 py-4 rounded-xl font-medium text-white overflow-hidden ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'gradient-bg hover:shadow-2xl transform hover:scale-105 animate-glow'
            } transition-all duration-300`}
          >
            {/* Animated background effect */}
            {!loading && (
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-blue-600 to-purple-600 animate-gradient opacity-0 hover:opacity-100 transition-opacity duration-300" />
            )}
            
            {/* Button content */}
            <div className="relative z-10 flex items-center space-x-3">
              {loading ? (
                <>
                  <div className="flex space-x-1">
                    {[...Array(3)].map((_, i) => (
                      <div 
                        key={i}
                        className="w-2 h-2 bg-white rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                  <span className="animate-pulse">Processing...</span>
                  <Zap className="w-5 h-5 animate-pulse" />
                </>
              ) : (
                <>
                  <Brain className="w-5 h-5 animate-pulse-slow" />
                  <span className="font-bold">
                    Start AI Processing ({Object.keys(selectedFiles).length} {Object.keys(selectedFiles).length === 1 ? 'file' : 'files'})
                  </span>
                  <Zap className="w-5 h-5 animate-pulse-slow" />
                </>
              )}
            </div>
          </button>
        </div>
      )}
    </div>
  );
};

export default Upload;