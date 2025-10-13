import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import { Upload as UploadIcon, FileText, X, Brain, Zap, CheckCircle, FolderArchive, Files } from 'lucide-react';
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

// Separate component for Submit Button to avoid React warnings
const SubmitButton: React.FC<{
  loading: boolean;
  totalFiles: number;
  onSubmit: () => void;
}> = ({ loading, totalFiles, onSubmit }) => {
  return (
    <div className="flex justify-center animate-fade-in-up">
      <button
        onClick={onSubmit}
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
                Start AI Processing ({totalFiles} {totalFiles === 1 ? 'file' : 'files'})
              </span>
              <Zap className="w-5 h-5 animate-pulse-slow" />
            </>
          )}
        </div>
      </button>
    </div>
  );
};

const Upload = () => {
  const navigate = useNavigate();
  const { uploadDocuments, loading } = useDocument();
  const [selectedFiles, setSelectedFiles] = useState<{ [key: string]: File[] }>({});
  const [dragOver, setDragOver] = useState<string | null>(null);

  // ZIP upload mode state
  const [uploadMode, setUploadMode] = useState<'files' | 'zip'>('files');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [zipDocType, setZipDocType] = useState<string>('faktur_pajak');

  const handleFileSelect = (documentType: string, newFiles: File[]) => {
    // File validation constants
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB - Support untuk rekening koran bank dengan banyak halaman
    const MAX_FILES = 10;
    const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'application/pdf'];
    const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];

    // Validate each file
    const validFiles: File[] = [];
    const rejectedFiles: string[] = [];

    newFiles.forEach(file => {
      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        rejectedFiles.push(`${file.name} (exceeds 50MB limit)`);
        return;
      }

      // Enhanced file type validation - check MIME type first
      const isValidMimeType = ALLOWED_TYPES.includes(file.type);

      // Check extension - only get the last extension to prevent bypass
      const nameParts = file.name.split('.');
      const fileExtension = nameParts.length > 1 ? '.' + nameParts[nameParts.length - 1].toLowerCase() : '';
      const isValidExtension = ALLOWED_EXTENSIONS.includes(fileExtension);

      // Reject if filename has multiple extensions (e.g., file.pdf.exe)
      const hasMultipleExtensions = nameParts.length > 2 &&
        nameParts.slice(1, -1).some(part => ALLOWED_EXTENSIONS.includes('.' + part.toLowerCase()));

      if (hasMultipleExtensions) {
        rejectedFiles.push(`${file.name} (suspicious file name)`);
        return;
      }

      // Both MIME type and extension must be valid
      if (!isValidMimeType || !isValidExtension) {
        rejectedFiles.push(`${file.name} (invalid file type)`);
        return;
      }

      // Additional check: file size must be > 0
      if (file.size === 0) {
        rejectedFiles.push(`${file.name} (empty file)`);
        return;
      }

      validFiles.push(file);
    });

    // Show errors for rejected files
    if (rejectedFiles.length > 0) {
      toast.error(`Rejected files:\n${rejectedFiles.join('\n')}`, {
        duration: 5000
      });
    }

    // Add valid files
    if (validFiles.length > 0) {
      setSelectedFiles(prev => {
        const existingFiles = prev[documentType] || [];
        const combined = [...existingFiles, ...validFiles];

        // Limit to MAX_FILES maximum
        if (combined.length > MAX_FILES) {
          toast.error(`Maximum ${MAX_FILES} files per document type. Only first ${MAX_FILES} files will be added.`);
          return {
            ...prev,
            [documentType]: combined.slice(0, MAX_FILES)
          };
        }

        toast.success(`${validFiles.length} file(s) added successfully`);
        return {
          ...prev,
          [documentType]: combined
        };
      });
    }
  };

  const handleFileDrop = (e: React.DragEvent, documentType: string) => {
    e.preventDefault();
    setDragOver(null);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(documentType, files);
    }
  };

  const removeFile = (documentType: string, fileIndex?: number) => {
    setSelectedFiles(prev => {
      if (fileIndex !== undefined) {
        // Remove specific file
        const files = prev[documentType] || [];
        const newFiles = files.filter((_, index) => index !== fileIndex);
        if (newFiles.length === 0) {
          const { [documentType]: _, ...rest } = prev;
          return rest;
        }
        return {
          ...prev,
          [documentType]: newFiles
        };
      } else {
        // Remove all files for this document type
        const { [documentType]: _, ...rest } = prev;
        return rest;
      }
    });
  };


  const handleSubmit = async () => {
    const fileEntries = Object.entries(selectedFiles).filter(([_, files]) => files && files.length > 0);

    if (fileEntries.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    try {
      // Flatten all files with their document types
      const fileList: File[] = [];
      const documentTypesList: string[] = [];

      fileEntries.forEach(([docType, files]) => {
        files.forEach(file => {
          fileList.push(file);
          documentTypesList.push(docType);
        });
      });

      const batch = await uploadDocuments(fileList, documentTypesList);

      // Navigate to results immediately
      navigate(`/scan-results/${batch.id}`);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const handleZipFileSelect = (file: File) => {
    // Validate ZIP file
    const MAX_ZIP_SIZE = 100 * 1024 * 1024; // 100MB

    if (!file.name.toLowerCase().endsWith('.zip')) {
      toast.error('Please select a ZIP file');
      return;
    }

    if (file.size > MAX_ZIP_SIZE) {
      toast.error('ZIP file exceeds 100MB limit');
      return;
    }

    if (file.size === 0) {
      toast.error('ZIP file is empty');
      return;
    }

    setZipFile(file);
    toast.success(`ZIP file selected: ${file.name}`);
  };

  const handleZipSubmit = async () => {
    if (!zipFile) {
      toast.error('Please select a ZIP file');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', zipFile);
      formData.append('document_type', zipDocType);

      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/upload-zip', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = typeof error.detail === 'object'
          ? error.detail.message || JSON.stringify(error.detail)
          : error.detail || 'ZIP upload failed';
        throw new Error(errorMessage);
      }

      const batch = await response.json();
      toast.success(`ZIP uploaded! Processing ${batch.total_files} files...`);

      // Navigate to results
      navigate(`/scan-results/${batch.id}`);
    } catch (error) {
      console.error('ZIP upload failed:', error);
      toast.error(error instanceof Error ? error.message : 'ZIP upload failed');
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
            <p className="text-gray-600 mt-1">
              {uploadMode === 'files'
                ? 'Upload 1-10 files per document type for AI-powered scanning'
                : 'Upload a ZIP file containing multiple documents for batch processing'
              }
            </p>
          </div>
        </div>
      </div>

      {/* Upload Mode Toggle */}
      <div className="bg-white rounded-lg p-4 shadow-sm border">
        <div className="flex items-center justify-center space-x-4">
          <button
            onClick={() => {
              setUploadMode('files');
              setZipFile(null);
            }}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg transition-all transform hover:scale-105 ${
              uploadMode === 'files'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Files className="w-5 h-5" />
            <span className="font-medium">Upload Files</span>
          </button>
          <button
            onClick={() => {
              setUploadMode('zip');
              setSelectedFiles({});
            }}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg transition-all transform hover:scale-105 ${
              uploadMode === 'zip'
                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <FolderArchive className="w-5 h-5" />
            <span className="font-medium">Upload ZIP</span>
          </button>
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

      {/* Upload Areas - Files Mode */}
      {uploadMode === 'files' && (
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
              {selectedFiles[docType.id] && selectedFiles[docType.id].length > 0 ? (
                <div className="space-y-2">
                  {/* Files List */}
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {selectedFiles[docType.id].map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border-2 border-green-300 shadow-sm animate-scale-in hover:shadow-md transition-all duration-300">
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <div className="relative flex-shrink-0">
                            <FileText className="w-5 h-5 text-green-600" />
                            <CheckCircle className="w-3 h-3 text-green-600 absolute -top-1 -right-1" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <span className="text-xs font-semibold text-green-900 block truncate">
                              {file.name}
                            </span>
                            <span className="text-xs text-green-700">
                              {(file.size / 1024).toFixed(1)} KB
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(docType.id, index)}
                          className="text-red-500 hover:text-red-700 hover:bg-red-100 p-1.5 rounded-full transition-all duration-200 hover:scale-110 flex-shrink-0 ml-2"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                  
                  {/* Add More Button */}
                  {selectedFiles[docType.id].length < 10 && (
                    <button
                      onClick={() => {
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.accept = '.pdf,.jpg,.jpeg,.png';
                        input.multiple = true;
                        input.onchange = (e) => {
                          const files = Array.from((e.target as HTMLInputElement).files || []);
                          if (files.length > 0) {
                            handleFileSelect(docType.id, files);
                          }
                        };
                        input.click();
                      }}
                      className="w-full py-2 px-3 text-sm border-2 border-dashed border-green-300 rounded-lg text-green-700 hover:bg-green-50 hover:border-green-400 transition-all duration-200 font-medium"
                    >
                      + Add More Files ({selectedFiles[docType.id].length}/10)
                    </button>
                  )}
                  
                  {/* Remove All Button */}
                  <button
                    onClick={() => removeFile(docType.id)}
                    className="w-full py-2 px-3 text-sm bg-red-50 border border-red-200 rounded-lg text-red-700 hover:bg-red-100 transition-all duration-200 font-medium"
                  >
                    Remove All
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
                    input.multiple = true;
                    input.onchange = (e) => {
                      const files = Array.from((e.target as HTMLInputElement).files || []);
                      if (files.length > 0) {
                        handleFileSelect(docType.id, files);
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
                    {dragOver === docType.id ? '🎯 Drop files here!' : 'Drop files here or click to browse'}
                  </p>
                  <p className="text-xs text-gray-500">PDF, JPG, PNG • Max 10 files • Up to 50MB each</p>
                  
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
      )}

      {/* Upload Area - ZIP Mode */}
      {uploadMode === 'zip' && (
        <div className="space-y-6">
          {/* Document Type Selector for ZIP */}
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Document Type</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {documentTypes.map((docType) => (
                <button
                  key={docType.id}
                  onClick={() => setZipDocType(docType.id)}
                  className={`p-4 rounded-lg border-2 transition-all transform hover:scale-105 ${
                    zipDocType === docType.id
                      ? 'border-purple-500 bg-purple-50 shadow-lg'
                      : 'border-gray-200 bg-white hover:border-purple-300'
                  }`}
                >
                  <div className="text-3xl mb-2">{docType.icon}</div>
                  <div className="text-sm font-medium text-gray-900">{docType.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{docType.accuracy}</div>
                </button>
              ))}
            </div>
          </div>

          {/* ZIP File Upload Area */}
          <div className="bg-white rounded-lg p-8 shadow-sm border">
            {zipFile ? (
              <div className="space-y-4">
                {/* Selected ZIP File Display */}
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-6 border-2 border-green-300 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="relative">
                        <FolderArchive className="w-12 h-12 text-green-600" />
                        <CheckCircle className="w-5 h-5 text-green-600 absolute -top-1 -right-1" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-green-900 text-lg">{zipFile.name}</h4>
                        <p className="text-sm text-green-700">
                          {(zipFile.size / (1024 * 1024)).toFixed(2)} MB • Document Type: {documentTypes.find(dt => dt.id === zipDocType)?.label}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setZipFile(null)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-100 p-2 rounded-full transition-all hover:scale-110"
                    >
                      <X className="w-6 h-6" />
                    </button>
                  </div>
                </div>

                {/* ZIP Info */}
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                  <div className="flex items-start space-x-3">
                    <Brain className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div className="text-sm text-blue-800">
                      <p className="font-medium mb-1">Ready to process!</p>
                      <p>The ZIP file will be extracted and all valid documents (PDF, PNG, JPG, JPEG, TIFF) will be processed as <strong>{documentTypes.find(dt => dt.id === zipDocType)?.label}</strong>.</p>
                    </div>
                  </div>
                </div>

                {/* Submit Button for ZIP */}
                <div className="flex justify-center pt-4">
                  <button
                    onClick={handleZipSubmit}
                    disabled={loading}
                    className={`relative px-8 py-4 rounded-xl font-medium text-white overflow-hidden ${
                      loading
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'gradient-bg hover:shadow-2xl transform hover:scale-105 animate-glow'
                    } transition-all duration-300`}
                  >
                    {!loading && (
                      <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-blue-600 to-purple-600 animate-gradient opacity-0 hover:opacity-100 transition-opacity duration-300" />
                    )}
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
                          <span className="animate-pulse">Processing ZIP...</span>
                          <Zap className="w-5 h-5 animate-pulse" />
                        </>
                      ) : (
                        <>
                          <Brain className="w-5 h-5 animate-pulse-slow" />
                          <span className="font-bold">Start AI Processing (ZIP)</span>
                          <Zap className="w-5 h-5 animate-pulse-slow" />
                        </>
                      )}
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              <div
                className="upload-dropzone p-12 rounded-lg text-center cursor-pointer transition-all duration-300 hover:border-purple-300 hover:bg-purple-50 hover:scale-102"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver('zip');
                }}
                onDragLeave={() => setDragOver(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(null);
                  const files = Array.from(e.dataTransfer.files);
                  if (files.length > 0 && files[0].name.toLowerCase().endsWith('.zip')) {
                    handleZipFileSelect(files[0]);
                  } else {
                    toast.error('Please drop a ZIP file');
                  }
                }}
                onClick={() => {
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.accept = '.zip';
                  input.onchange = (e) => {
                    const file = (e.target as HTMLInputElement).files?.[0];
                    if (file) {
                      handleZipFileSelect(file);
                    }
                  };
                  input.click();
                }}
              >
                <FolderArchive className={`w-16 h-16 mx-auto mb-4 transition-all duration-300 ${
                  dragOver === 'zip' ? 'text-blue-500 animate-bounce scale-110' : 'text-gray-400'
                }`} />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {dragOver === 'zip' ? 'Drop your ZIP file here!' : 'Upload ZIP File'}
                </h3>
                <p className="text-sm text-gray-600 mb-1">
                  Drop a ZIP file here or click to browse
                </p>
                <p className="text-xs text-gray-500">
                  Max 100MB • Contains PDF, JPG, PNG, TIFF files • Max 50 files in ZIP
                </p>
                <div className="mt-6 flex items-center justify-center space-x-6 text-xs text-gray-500">
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span>PDF</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span>PNG</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span>JPG</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span>TIFF</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Submit Button with Enhanced Animation - Files Mode */}
      {uploadMode === 'files' && Object.keys(selectedFiles).length > 0 && (
        <SubmitButton
          loading={loading}
          totalFiles={Object.values(selectedFiles).reduce((sum, files) => sum + files.length, 0)}
          onSubmit={handleSubmit}
        />
      )}
    </div>
  );
};

export default Upload;