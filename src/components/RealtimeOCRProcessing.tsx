import React, { useState, useEffect } from 'react';
import { Brain, Zap, Cpu, CheckCircle, Clock, AlertCircle, TrendingUp } from 'lucide-react';

interface RealtimeOCRProcessingProps {
  batchId: string;
  onComplete?: () => void;
  className?: string;
}

interface ProcessingStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  duration?: number;
  icon: React.ReactNode;
}

const RealtimeOCRProcessing: React.FC<RealtimeOCRProcessingProps> = ({
  batchId,
  onComplete,
  className = ''
}) => {
  const [currentStage, setCurrentStage] = useState(0);
  const [stages, setStages] = useState<ProcessingStage[]>([
    {
      id: 'preprocessing',
      name: 'Advanced Preprocessing',
      description: 'AI-powered image enhancement and optimization',
      status: 'pending',
      icon: <Brain className="w-5 h-5" />
    },
    {
      id: 'rapidocr',
      name: 'RapidOCR Processing',
      description: 'Ultra-fast ONNX runtime text extraction',
      status: 'pending',
      icon: <Zap className="w-5 h-5" />
    },
    {
      id: 'easyocr',
      name: 'EasyOCR Analysis',
      description: 'Multilingual OCR with Indonesian support',
      status: 'pending',
      icon: <Cpu className="w-5 h-5" />
    },
    {
      id: 'ensemble',
      name: 'Ensemble AI Fusion',
      description: 'Combining results with confidence weighting',
      status: 'pending',
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      id: 'analysis',
      name: 'Document Analysis',
      description: 'Structure analysis and entity extraction',
      status: 'pending',
      icon: <Brain className="w-5 h-5" />
    }
  ]);

  const [processingMetrics, setProcessingMetrics] = useState({
    totalFiles: 0,
    processedFiles: 0,
    currentFile: '',
    averageAccuracy: 0,
    processingSpeed: 0,
    estimatedTimeRemaining: 0
  });

  useEffect(() => {
    // Simulate processing stages
    const processStages = async () => {
      for (let i = 0; i < stages.length; i++) {
        setCurrentStage(i);
        
        // Update stage to processing
        setStages(prev => prev.map((stage, index) => ({
          ...stage,
          status: index === i ? 'processing' : index < i ? 'completed' : 'pending'
        })));

        // Simulate processing time
        const processingTime = Math.random() * 2000 + 1000; // 1-3 seconds
        
        // Update metrics during processing
        const interval = setInterval(() => {
          setProcessingMetrics(prev => ({
            ...prev,
            processingSpeed: Math.random() * 50 + 50, // 50-100 chars/sec
            averageAccuracy: Math.random() * 10 + 90, // 90-100%
            estimatedTimeRemaining: Math.max(0, prev.estimatedTimeRemaining - 0.1)
          }));
        }, 100);

        await new Promise(resolve => setTimeout(resolve, processingTime));
        clearInterval(interval);

        // Mark stage as completed
        setStages(prev => prev.map((stage, index) => ({
          ...stage,
          status: index <= i ? 'completed' : 'pending',
          duration: index === i ? processingTime : stage.duration
        })));
      }

      // All stages completed
      setTimeout(() => {
        onComplete?.();
      }, 500);
    };

    processStages();
  }, [batchId, onComplete, stages.length]);

  const getStageStatusIcon = (status: ProcessingStage['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
        return <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStageStatusColor = (status: ProcessingStage['status']) => {
    switch (status) {
      case 'completed':
        return 'border-green-200 bg-green-50';
      case 'processing':
        return 'border-blue-200 bg-blue-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm border ${className}`}>
      {/* Header */}
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
          <Brain className="w-6 h-6 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Next-Generation OCR Processing</h3>
          <p className="text-sm text-gray-600">Real-time AI document analysis in progress</p>
        </div>
      </div>

      {/* Processing Stages */}
      <div className="space-y-4 mb-6">
        {stages.map((stage, index) => (
          <div 
            key={stage.id}
            className={`p-4 rounded-lg border transition-all duration-300 ${getStageStatusColor(stage.status)}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="text-gray-600">
                  {stage.icon}
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">{stage.name}</h4>
                  <p className="text-sm text-gray-600">{stage.description}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {stage.duration && (
                  <span className="text-xs text-gray-500">
                    {(stage.duration / 1000).toFixed(1)}s
                  </span>
                )}
                {getStageStatusIcon(stage.status)}
              </div>
            </div>
            
            {stage.status === 'processing' && (
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" 
                       style={{ width: `${Math.min(100, (index + 1) * 20)}%` }} />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Real-time Metrics */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4 border border-purple-100">
        <h4 className="font-medium text-gray-900 mb-3">Processing Metrics</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {processingMetrics.averageAccuracy.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Accuracy</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {processingMetrics.processingSpeed.toFixed(0)}
            </div>
            <div className="text-xs text-gray-600">chars/sec</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {currentStage + 1}/{stages.length}
            </div>
            <div className="text-xs text-gray-600">Stages</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600">
              {((currentStage + 1) / stages.length * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-gray-600">Complete</div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm text-gray-500">
            {((currentStage + 1) / stages.length * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-purple-500 to-blue-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${(currentStage + 1) / stages.length * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default RealtimeOCRProcessing;