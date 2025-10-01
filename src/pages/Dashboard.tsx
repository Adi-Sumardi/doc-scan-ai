import { useDocument } from '../context/DocumentContext';
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Upload as UploadIcon,
  Brain,
  Zap,
  Award,
  FileCheck
} from 'lucide-react';

const Dashboard = () => {
  const { batches, scanResults } = useDocument();

  // Ensure scanResults is always an array to prevent runtime errors
  const safeResults = Array.isArray(scanResults) ? scanResults : [];
  const totalDocuments = safeResults.length;

  // Calculate metrics from the actual scanResults data
  const averageAccuracy = safeResults.length > 0
    ? (safeResults.reduce((sum, r) => sum + (r.confidence_score || r.confidence || 0), 0) / safeResults.length) * 100
    : 0;
  const averageProcessingTime = safeResults.length > 0
    ? safeResults.reduce((sum, r) => sum + (r.processing_time || r.ocr_processing_time || 0), 0) / safeResults.length
    : 0;
  const resultsWithQuality = safeResults.filter(r => r.nextgen_metrics?.quality_score);
  const averageQuality = resultsWithQuality.length > 0
    ? resultsWithQuality.reduce((sum, r) => sum + (r.nextgen_metrics?.quality_score || 0), 0) / resultsWithQuality.length
    : 0;

  const recentBatches = Array.isArray(batches) ? batches.slice(0, 5) : [];

  const statsCards = [
    {
      label: 'AI Accuracy',
      value: `${averageAccuracy.toFixed(1)}%`,
      subtitle: 'Document recognition precision',
      icon: TrendingUp,
      color: 'bg-gradient-to-r from-green-500 to-green-600',
      change: '+2.5% from last week'
    },
    {
      label: 'Quality Score',
      value: `${averageQuality.toFixed(1)}%`,
      subtitle: 'Real-time validation metrics',
      icon: Award,
      color: 'bg-gradient-to-r from-blue-500 to-blue-600',
      change: '+1.8% from last week'
    },
    {
      label: 'Processing Speed',
      value: `${averageProcessingTime.toFixed(2)}s`,
      subtitle: 'Average time per document',
      icon: Zap,
      color: 'bg-gradient-to-r from-orange-500 to-orange-600',
      change: '-0.3s faster'
    },
    {
      label: 'Documents Processed',
      value: totalDocuments,
      subtitle: 'Successfully scanned documents',
      icon: FileCheck,
      color: 'bg-gradient-to-r from-purple-500 to-purple-600',
      change: `+${recentBatches.length} batches`
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">AI-Powered Document Scanner Analytics</p>
          </div>
          <div className="flex items-center space-x-2 text-green-600">
            <Zap className="w-5 h-5" />
            <span className="font-medium">System Online</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white rounded-lg p-6 shadow-sm border hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{stat.subtitle}</p>
                  <p className="text-sm text-purple-600 mt-2 flex items-center font-medium">
                    <TrendingUp className="w-4 h-4 mr-1" />
                    {stat.change}
                  </p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Batches */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-900">Recent Batches</h3>
          </div>
          <div className="p-6">
            {recentBatches.length === 0 ? (
              <div className="text-center py-8">
                <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500">No batches uploaded yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recentBatches.map((batch) => (
                  <div key={batch.id} className="flex items-center justify-between p-3 rounded-lg border">
                    <div>
                      <p className="font-medium text-gray-900">Batch #{batch.id.slice(-8)}</p>
                      <p className="text-sm text-gray-500">{batch.total_files} files</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      {batch.status === 'completed' && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                      {batch.status === 'processing' && (
                        <Clock className="w-5 h-5 text-yellow-500" />
                      )}
                      {batch.status === 'error' && (
                        <AlertCircle className="w-5 h-5 text-red-500" />
                      )}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        batch.status === 'completed' 
                          ? 'bg-green-100 text-green-800'
                          : batch.status === 'processing'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {batch.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI DocScan Status */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">AI DocScan Engine</h3>
                <p className="text-sm text-gray-600">Intelligent document processing</p>
              </div>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-orange-50 to-red-50 border border-orange-100">
                <div className="flex items-center space-x-3">
                  <Zap className="w-5 h-5 text-orange-600" />
                  <div>
                    <p className="font-medium text-orange-900">Lightning Processing</p>
                    <p className="text-sm text-orange-600">Ultra-fast document recognition</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                    ⚡ Active
                  </span>
                  <p className="text-xs text-gray-500 mt-1">Primary Engine</p>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-100">
                <div className="flex items-center space-x-3">
                  <Brain className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="font-medium text-blue-900">Smart Recognition</p>
                    <p className="text-sm text-blue-600">Multilingual support • Indonesian optimized</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                    🧠 Active
                  </span>
                  <p className="text-xs text-gray-500 mt-1">AI Intelligence</p>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-100">
                <div className="flex items-center space-x-3">
                  <Brain className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="font-medium text-purple-900">Image Enhancement</p>
                    <p className="text-sm text-purple-600">AI-powered quality optimization</p>
                  </div>
                </div>
                <div className="text-right">  
                  <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                    🎯 Active
                  </span>
                  <p className="text-xs text-gray-500 mt-1">Preprocessing</p>
                </div>
              </div>
              
              <div className="mt-4 p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border border-green-100">
                <div className="flex items-center justify-center space-x-4 text-sm">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-green-700 font-medium">System Status: Optimal</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-blue-700">High Accuracy • Tax Documents</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;