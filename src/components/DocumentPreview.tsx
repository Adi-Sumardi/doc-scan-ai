import { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCw, Download, Maximize2, ChevronLeft, ChevronRight } from 'lucide-react';
import { apiService } from '../services/api';

interface DocumentPreviewProps {
  fileUrl: string;
  fileName: string;
  fileType: string;
  boundingBoxes?: Array<{
    text: string;
    coordinates: number[];
    confidence?: number;
  }>;
}

const DocumentPreview = ({ fileUrl, fileName, fileType, boundingBoxes }: DocumentPreviewProps) => {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const isPDF = fileType.toLowerCase().includes('pdf');
  const isImage = fileType.toLowerCase().match(/image|png|jpg|jpeg|tiff|bmp/);

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 300));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 50));
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);
  const handleNextPage = () => setCurrentPage(prev => Math.min(prev + 1, totalPages));
  const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  useEffect(() => {
    let isMounted = true;
    const fetchFile = async () => {
      setIsLoading(true);
      try {
        const response = await apiService.exportResultPdf(fileUrl.split('/')[3]); // Extract ID from URL
        const blob = new Blob([response], { type: fileType });
        const url = URL.createObjectURL(blob);
        if (isMounted) {
          setObjectUrl(url);
        }
      } catch (error) {
        console.error("Failed to load document preview:", error);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    fetchFile();
    return () => { isMounted = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [fileUrl, fileType]);

  return (
    <div 
      ref={containerRef}
      className={`h-full flex flex-col bg-gray-900 rounded-lg overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}
    >
      {/* Toolbar */}
      <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomOut}
            disabled={zoom <= 50}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Zoom Out"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          <span className="text-white font-medium min-w-[60px] text-center">{zoom}%</span>
          <button
            onClick={handleZoomIn}
            disabled={zoom >= 300}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Zoom In"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
          
          <div className="w-px h-6 bg-gray-600 mx-2" />
          
          <button
            onClick={handleRotate}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title="Rotate"
          >
            <RotateCw className="w-5 h-5" />
          </button>
          
          <button
            onClick={handleFullscreen}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title="Fullscreen"
          >
            <Maximize2 className="w-5 h-5" />
          </button>
          
          <button
            onClick={handleDownload}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title="Download"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>

        {/* Page Navigation for PDF */}
        {isPDF && totalPages > 1 && (
          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-white font-medium">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}

        <div className="text-gray-400 text-sm truncate max-w-xs" title={fileName}>
          {fileName}
        </div>
      </div>

      {/* Document Viewer */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4">
        <div 
          className="transition-all duration-300"
          style={{
            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
            transformOrigin: 'center center',
          }}
        >
          {isLoading && <div className="text-white">Loading preview...</div>}
          
          {!isLoading && !objectUrl && <div className="text-red-400">Failed to load preview.</div>}

          {!isLoading && objectUrl && isImage && (
            <img
              src={objectUrl}
              alt={fileName}
              className="max-w-full h-auto shadow-2xl"
              style={{ maxHeight: 'calc(100vh - 200px)' }}
            />
          )}
          
          {!isLoading && objectUrl && isPDF && (
            <div className="bg-white shadow-2xl">
              <iframe
                src={`${objectUrl}#page=${currentPage}`}
                className="w-full border-0"
                style={{ 
                  width: '800px',
                  height: '1000px',
                }}
                title={fileName}
                onLoad={() => {
                  // PDF loaded
                }}
              />
            </div>
          )}

          {!isImage && !isPDF && (
            <div className="bg-gray-800 text-white p-8 rounded-lg text-center">
              <p className="text-lg mb-2">Preview not available</p>
              <p className="text-gray-400">File type: {fileType}</p>
              <button
                onClick={handleDownload}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors inline-flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Download File
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bounding Boxes Info */}
      {boundingBoxes && boundingBoxes.length > 0 && (
        <div className="bg-gray-800 px-4 py-2 border-t border-gray-700">
          <p className="text-gray-400 text-sm">
            Detected {boundingBoxes.length} text regions
          </p>
        </div>
      )}
    </div>
  );
};

export default DocumentPreview;
