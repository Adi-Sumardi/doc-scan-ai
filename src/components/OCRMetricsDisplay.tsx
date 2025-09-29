import React from 'react';
import { Brain, Zap, Target, Cpu, TrendingUp } from 'lucide-react';
import { NextGenOCRMetrics, ProcessingQuality } from '../services/api';

interface OCRMetricsDisplayProps {
  metrics?: NextGenOCRMetrics;
  quality?: ProcessingQuality;
  className?: string;
}

const OCRMetricsDisplay: React.FC<OCRMetricsDisplayProps> = ({ 
  metrics, 
  quality, 
  className = '' 
}) => {
  if (!metrics && !quality) {
    return null;
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 95) return 'text-green-600 bg-green-50';
    if (confidence >= 85) return 'text-blue-600 bg-blue-50';
    if (confidence >= 70) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getEngineIcon = (engine: string) => {
    switch (engine.toLowerCase()) {
      case 'rapid':
        return <Zap className="w-4 h-4" />;
      case 'easy':
        return <Brain className="w-4 h-4" />;
      default:
        return <Cpu className="w-4 h-4" />;
    }
  };

  const getQualityBadge = (rating: string) => {
    const badges = {
      excellent: 'bg-green-100 text-green-800',
      good: 'bg-blue-100 text-blue-800',
      fair: 'bg-yellow-100 text-yellow-800',
      poor: 'bg-red-100 text-red-800'
    };
    return badges[rating as keyof typeof badges] || badges.fair;
  };

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm border ${className}`}>
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Next-Gen OCR Metrics</h3>
      </div>

      {metrics && (
        <div className="space-y-4">
          {/* Primary Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`text-2xl font-bold ${getConfidenceColor(metrics.confidence)}`}>
                {metrics.confidence.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 mt-1">OCR Confidence</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getConfidenceColor(metrics.quality_score)}`}>
                {metrics.quality_score.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 mt-1">Quality Score</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {metrics.processing_time.toFixed(2)}s
              </div>
              <div className="text-sm text-gray-600 mt-1">Processing Time</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-indigo-600 flex items-center justify-center space-x-2">
                {getEngineIcon(metrics.engine_used)}
                <span className="text-sm">{metrics.engine_used.toUpperCase()}</span>
              </div>
              <div className="text-sm text-gray-600 mt-1">OCR Engine</div>
            </div>
          </div>

          {/* Advanced Metrics */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Advanced Analysis</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Layout Recognition</span>
                  <span className={`text-sm font-medium ${getConfidenceColor(metrics.layout_confidence)}`}>
                    {metrics.layout_confidence.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full"
                    style={{ width: `${metrics.layout_confidence}%` }}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Semantic Understanding</span>
                  <span className={`text-sm font-medium ${getConfidenceColor(metrics.semantic_confidence)}`}>
                    {metrics.semantic_confidence.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-green-500 to-blue-500 h-2 rounded-full"
                    style={{ width: `${metrics.semantic_confidence}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {quality && (
        <div className="border-t pt-4 mt-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-700">Processing Quality</h4>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getQualityBadge(quality.accuracy_rating)}`}>
              {quality.accuracy_rating.toUpperCase()}
            </span>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Overall Score</span>
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <span className="text-sm font-semibold text-green-600">
                  {quality.overall_score.toFixed(1)}/100
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Text Clarity</span>
              <span className="text-sm font-medium text-blue-600">
                {quality.text_clarity.toFixed(1)}/100
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Structure Preservation</span>
              <span className="text-sm font-medium text-purple-600">
                {quality.structure_preservation.toFixed(1)}/100
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Performance Badge */}
      <div className="mt-4 pt-4 border-t">
        <div className="flex items-center justify-center space-x-2 text-sm">
          <Target className="w-4 h-4 text-purple-500" />
          <span className="text-gray-600">Powered by</span>
          <span className="font-semibold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Next-Generation OCR
          </span>
        </div>
      </div>
    </div>
  );
};

export default OCRMetricsDisplay;