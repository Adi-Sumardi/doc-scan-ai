import { useDocument } from '../context/DocumentContext';
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Upload as UploadIcon,
  Brain,
  Zap
} from 'lucide-react';

const Dashboard = () => {
  const { batches, scanResults } = useDocument();

  const totalBatches = batches.length;
  const completedBatches = batches.filter(b => b.status === 'completed').length;
  const processingBatches = batches.filter(b => b.status === 'processing').length;
  const totalDocuments = scanResults.length;

  const stats = [
    {
      label: 'Total Batches',
      value: totalBatches,
      icon: FileText,
      color: 'bg-blue-500',
      change: '+12%'
    },
    {
      label: 'Completed',
      value: completedBatches,
      icon: CheckCircle,
      color: 'bg-green-500',
      change: '+8%'
    },
    {
      label: 'Processing',
      value: processingBatches,
      icon: Clock,
      color: 'bg-yellow-500',
      change: '0%'
    },
    {
      label: 'Documents Scanned',
      value: totalDocuments,
      icon: Brain,
      color: 'bg-purple-500',
      change: '+15%'
    }
  ];

  const recentBatches = batches.slice(0, 5);

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
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white rounded-lg p-6 shadow-sm border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                  <p className="text-sm text-green-600 mt-1 flex items-center">
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

        {/* AI Processing Info */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-900">AI Processing Status</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-blue-50">
                <div className="flex items-center space-x-3">
                  <Brain className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="font-medium text-blue-900">LayoutLMv3</p>
                    <p className="text-sm text-blue-600">Document Layout Analysis</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                  Active
                </span>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-green-50">
                <div className="flex items-center space-x-3">
                  <Zap className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="font-medium text-green-900">EasyOCR</p>
                    <p className="text-sm text-green-600">Optical Character Recognition</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                  Active
                </span>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-purple-50">
                <div className="flex items-center space-x-3">
                  <Brain className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="font-medium text-purple-900">Transformers + spaCy</p>
                    <p className="text-sm text-purple-600">NER & Data Extraction</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                  Active
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;