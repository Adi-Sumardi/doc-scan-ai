import { useDocument } from '../context/DocumentContext';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  Upload as UploadIcon,
  Brain,
  Zap,
  FileCheck,
  TrendingUp,
  FileText,
  Activity,
  Calendar,
  BarChart3,
  Eye
} from 'lucide-react';
import { useState, useEffect } from 'react';

const Dashboard = () => {
  const { batches, scanResults } = useDocument();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [greeting, setGreeting] = useState('');

  // Set greeting based on time
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Selamat Pagi');
    else if (hour < 15) setGreeting('Selamat Siang');
    else if (hour < 18) setGreeting('Selamat Sore');
    else setGreeting('Selamat Malam');
  }, []);

  // Ensure data is always array
  const safeResults = Array.isArray(scanResults) ? scanResults : [];
  const safeBatches = Array.isArray(batches) ? batches : [];

  // Calculate comprehensive metrics
  const totalDocuments = safeResults.length;
  const totalBatches = safeBatches.length;
  const completedBatches = safeBatches.filter(b => b.status === 'completed').length;
  const processingBatches = safeBatches.filter(b => b.status === 'processing').length;
  const failedBatches = safeBatches.filter(b => b.status === 'error').length;

  // Calculate success rate
  const successRate = totalBatches > 0
    ? ((completedBatches / totalBatches) * 100).toFixed(1)
    : 0;

  // Calculate average processing time
  const averageProcessingTime = safeResults.length > 0
    ? safeResults.reduce((sum, r) => sum + (r.processing_time || r.ocr_processing_time || 0), 0) / safeResults.length
    : 0;

  // Get recent batches
  const recentBatches = safeBatches
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  // Get today's documents
  const today = new Date().toDateString();
  const todayDocuments = safeResults.filter(r => {
    const date = r.created_at;
    return date ? new Date(date).toDateString() === today : false;
  }).length;

  // Calculate document type distribution
  const documentTypes = safeResults.reduce((acc, result) => {
    const type = result.document_type || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const topDocumentType = Object.entries(documentTypes)
    .sort(([, a], [, b]) => b - a)[0]?.[0] || 'N/A';

  // Stats cards with enhanced data
  const statsCards = [
    {
      label: 'Total Documents',
      value: totalDocuments,
      subtitle: `${todayDocuments} processed today`,
      icon: FileCheck,
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-50',
      iconColor: 'text-blue-600',
      change: `+${todayDocuments}`,
      changeLabel: 'today',
      trend: 'up'
    },
    {
      label: 'Success Rate',
      value: `${successRate}%`,
      subtitle: `${completedBatches}/${totalBatches} batches completed`,
      icon: TrendingUp,
      color: 'from-green-500 to-green-600',
      bgColor: 'bg-green-50',
      iconColor: 'text-green-600',
      change: Number(successRate) > 95 ? 'Excellent' : 'Good',
      changeLabel: 'performance',
      trend: 'up'
    },
    {
      label: 'Avg Processing',
      value: `${averageProcessingTime.toFixed(1)}s`,
      subtitle: 'Per document speed',
      icon: Zap,
      color: 'from-orange-500 to-orange-600',
      bgColor: 'bg-orange-50',
      iconColor: 'text-orange-600',
      change: averageProcessingTime < 5 ? 'Fast' : 'Normal',
      changeLabel: 'speed',
      trend: 'up'
    },
    {
      label: 'Active Batches',
      value: processingBatches,
      subtitle: `${failedBatches} failed batches`,
      icon: Activity,
      color: 'from-purple-500 to-purple-600',
      bgColor: 'bg-purple-50',
      iconColor: 'text-purple-600',
      change: `${processingBatches}`,
      changeLabel: 'in queue',
      trend: processingBatches > 0 ? 'up' : 'neutral'
    },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Enhanced Header with Welcome - RESPONSIVE */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg md:rounded-xl p-4 md:p-6 lg:p-8 shadow-lg text-white">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-6">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold mb-2">
              {greeting}, {user?.full_name || user?.username || 'User'}! 👋
            </h1>
            <p className="text-blue-100 text-sm md:text-base lg:text-lg">
              Selamat datang di AI Document Scanner Dashboard
            </p>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mt-3 md:mt-4 text-xs md:text-sm">
              <div className="flex items-center gap-2 bg-white/20 px-3 py-1.5 rounded-full w-fit">
                <Calendar className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span className="truncate">{new Date().toLocaleDateString('id-ID', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}</span>
              </div>
              <div className="flex items-center gap-2 bg-green-500/30 px-3 py-1.5 rounded-full w-fit">
                <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse flex-shrink-0"></div>
                <span>System Online</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full sm:w-auto lg:w-auto">
            <button
              onClick={() => navigate('/upload')}
              className="bg-white text-blue-600 px-4 md:px-6 py-2.5 md:py-3 rounded-lg font-semibold hover:bg-blue-50 transition-all transform hover:scale-105 shadow-lg flex items-center justify-center gap-2 text-sm md:text-base"
            >
              <UploadIcon className="w-4 h-4 md:w-5 md:h-5" />
              <span className="hidden sm:inline">Upload Dokumen</span>
              <span className="sm:hidden">Upload</span>
            </button>
            <button
              onClick={() => navigate('/documents')}
              className="bg-blue-500/30 backdrop-blur-sm text-white px-4 md:px-6 py-2.5 md:py-3 rounded-lg font-semibold hover:bg-blue-500/50 transition-all flex items-center justify-center gap-2 text-sm md:text-base"
            >
              <Eye className="w-4 h-4 md:w-5 md:h-5" />
              <span className="hidden sm:inline">Lihat Semua</span>
              <span className="sm:hidden">Semua</span>
            </button>
          </div>
        </div>
      </div>

      {/* Enhanced Stats Grid with Animations - RESPONSIVE */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6">
        {statsCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              className="group bg-white rounded-lg md:rounded-xl p-4 md:p-6 shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100 hover:border-blue-200 transform hover:-translate-y-1 cursor-pointer"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <div className="flex items-start justify-between mb-3 md:mb-4">
                <div className={`${stat.bgColor} p-2 md:p-3 rounded-lg md:rounded-xl group-hover:scale-110 transition-transform duration-300`}>
                  <Icon className={`w-5 h-5 md:w-6 md:h-6 ${stat.iconColor}`} />
                </div>
                <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                  stat.trend === 'up' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  <TrendingUp className="w-3 h-3" />
                  <span className="hidden sm:inline">{stat.change}</span>
                </div>
              </div>
              <div>
                <p className="text-xs md:text-sm font-medium text-gray-600 mb-1">{stat.label}</p>
                <p className="text-2xl md:text-3xl font-bold text-gray-900 mb-1">{stat.value}</p>
                <p className="text-xs text-gray-500 line-clamp-1">{stat.subtitle}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Content Grid - RESPONSIVE */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Recent Activity - Takes 2 columns */}
        <div className="lg:col-span-2 bg-white rounded-lg md:rounded-xl shadow-md border border-gray-100">
          <div className="p-4 md:p-6 border-b border-gray-100">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 p-2 rounded-lg flex-shrink-0">
                  <Activity className="w-4 h-4 md:w-5 md:h-5 text-blue-600" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-base md:text-lg font-semibold text-gray-900">Recent Batches</h3>
                  <p className="text-xs md:text-sm text-gray-500 hidden sm:block">Latest document processing activities</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/history')}
                className="text-xs md:text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 w-fit"
              >
                <span className="hidden sm:inline">View All</span>
                <span className="sm:hidden">All</span>
                <Eye className="w-3 h-3 md:w-4 md:h-4" />
              </button>
            </div>
          </div>
          <div className="p-4 md:p-6">
            {recentBatches.length === 0 ? (
              <div className="text-center py-8 md:py-12">
                <div className="bg-gray-100 w-12 h-12 md:w-16 md:h-16 rounded-full flex items-center justify-center mx-auto mb-3 md:mb-4">
                  <UploadIcon className="w-6 h-6 md:w-8 md:h-8 text-gray-400" />
                </div>
                <p className="text-sm md:text-base text-gray-500 mb-3 md:mb-4">No batches uploaded yet</p>
                <button
                  onClick={() => navigate('/upload')}
                  className="bg-blue-600 text-white px-4 md:px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2 text-sm md:text-base"
                >
                  <UploadIcon className="w-4 h-4" />
                  <span className="hidden sm:inline">Upload Your First Batch</span>
                  <span className="sm:hidden">Upload</span>
                </button>
              </div>
            ) : (
              <div className="space-y-2 md:space-y-3">
                {recentBatches.map((batch, idx) => (
                  <div
                    key={batch.id}
                    className="flex items-center justify-between p-3 md:p-4 rounded-lg md:rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50/50 transition-all cursor-pointer group"
                    onClick={() => navigate(`/scan-results/${batch.id}`)}
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    <div className="flex items-center gap-2 md:gap-4 flex-1 min-w-0">
                      <div className={`p-2 md:p-3 rounded-lg flex-shrink-0 ${
                        batch.status === 'completed' ? 'bg-green-100' :
                        batch.status === 'processing' ? 'bg-yellow-100' :
                        'bg-red-100'
                      }`}>
                        {batch.status === 'completed' && <CheckCircle className="w-4 h-4 md:w-5 md:h-5 text-green-600" />}
                        {batch.status === 'processing' && <Clock className="w-4 h-4 md:w-5 md:h-5 text-yellow-600 animate-spin" />}
                        {batch.status === 'error' && <AlertCircle className="w-4 h-4 md:w-5 md:h-5 text-red-600" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm md:text-base font-semibold text-gray-900 truncate">Batch #{batch.id.slice(-8)}</p>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                            batch.status === 'completed' ? 'bg-green-100 text-green-700' :
                            batch.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {batch.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 md:gap-4 mt-1 text-xs md:text-sm text-gray-500 flex-wrap">
                          <span className="flex items-center gap-1 flex-shrink-0">
                            <FileText className="w-3 h-3" />
                            {batch.total_files} files
                          </span>
                          <span className="hidden sm:flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(batch.created_at).toLocaleDateString('id-ID')}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
                      <div className="text-right hidden sm:block mr-2">
                        <p className="text-xs md:text-sm font-medium text-gray-900">
                          {batch.processed_files}/{batch.total_files}
                        </p>
                        <p className="text-xs text-gray-500">processed</p>
                      </div>
                      <Eye className="w-4 h-4 md:w-5 md:h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Document Statistics - RESPONSIVE */}
        <div className="bg-white rounded-lg md:rounded-xl shadow-md border border-gray-100">
          <div className="p-4 md:p-6 border-b border-gray-100">
            <div className="flex items-center gap-2 md:gap-3">
              <div className="bg-purple-100 p-2 rounded-lg flex-shrink-0">
                <BarChart3 className="w-4 h-4 md:w-5 md:h-5 text-purple-600" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base md:text-lg font-semibold text-gray-900">Statistics</h3>
                <p className="text-xs md:text-sm text-gray-500 hidden sm:block">Document overview</p>
              </div>
            </div>
          </div>
          <div className="p-4 md:p-6 space-y-3 md:space-y-4">
            {/* Document Type Distribution */}
            <div className="space-y-3">
              <p className="text-sm font-medium text-gray-700">Document Types</p>
              {Object.entries(documentTypes).length > 0 ? (
                Object.entries(documentTypes)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([type, count]) => {
                    const percentage = ((count / totalDocuments) * 100).toFixed(0);
                    return (
                      <div key={type} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600 capitalize">{type.replace(/_/g, ' ')}</span>
                          <span className="font-medium text-gray-900">{count}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No data available</p>
              )}
            </div>

            {/* Quick Stats */}
            <div className="pt-4 border-t border-gray-100 space-y-3">
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-gray-700">Most Common</span>
                </div>
                <span className="text-sm font-bold text-blue-600 capitalize">
                  {topDocumentType.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium text-gray-700">Completed</span>
                </div>
                <span className="text-sm font-bold text-green-600">
                  {completedBatches} batches
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-orange-600" />
                  <span className="text-sm font-medium text-gray-700">Avg Speed</span>
                </div>
                <span className="text-sm font-bold text-orange-600">
                  {averageProcessingTime.toFixed(1)}s
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Engine Status - Enhanced & RESPONSIVE */}
      <div className="bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 rounded-lg md:rounded-xl shadow-md border border-purple-100 p-4 md:p-6">
        <div className="flex items-center gap-2 md:gap-3 mb-4 md:mb-6">
          <div className="bg-gradient-to-r from-purple-500 to-blue-500 p-2 md:p-3 rounded-lg md:rounded-xl shadow-lg flex-shrink-0">
            <Brain className="w-5 h-5 md:w-6 md:h-6 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg md:text-xl font-bold text-gray-900">AI Engine Status</h3>
            <p className="text-xs md:text-sm text-gray-600 hidden sm:block">Real-time processing capabilities</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4">
          {/* Google Document AI */}
          <div className="bg-white/80 backdrop-blur-sm rounded-lg md:rounded-xl p-3 md:p-4 border border-orange-200 hover:shadow-lg transition-all">
            <div className="flex items-center justify-between mb-2 md:mb-3">
              <div className="flex items-center gap-2 min-w-0">
                <Zap className="w-4 h-4 md:w-5 md:h-5 text-orange-600 flex-shrink-0" />
                <span className="text-sm md:text-base font-semibold text-gray-900 truncate">Google Doc AI</span>
              </div>
              <span className="px-2 py-0.5 md:py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex-shrink-0">
                Active
              </span>
            </div>
            <p className="text-xs md:text-sm text-gray-600 mb-1 md:mb-2">Primary OCR Engine</p>
            <div className="flex items-center gap-1 text-xs text-orange-600">
              <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse flex-shrink-0"></div>
              <span>Ultra-fast processing</span>
            </div>
          </div>

          {/* Smart Mapper */}
          <div className="bg-white/80 backdrop-blur-sm rounded-lg md:rounded-xl p-3 md:p-4 border border-blue-200 hover:shadow-lg transition-all">
            <div className="flex items-center justify-between mb-2 md:mb-3">
              <div className="flex items-center gap-2 min-w-0">
                <Brain className="w-4 h-4 md:w-5 md:h-5 text-blue-600 flex-shrink-0" />
                <span className="text-sm md:text-base font-semibold text-gray-900 truncate">Smart Mapper</span>
              </div>
              <span className="px-2 py-0.5 md:py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex-shrink-0">
                Active
              </span>
            </div>
            <p className="text-xs md:text-sm text-gray-600 mb-1 md:mb-2">AI Field Extraction</p>
            <div className="flex items-center gap-1 text-xs text-blue-600">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse flex-shrink-0"></div>
              <span>GPT-4 powered</span>
            </div>
          </div>

          {/* Image Enhancement */}
          <div className="bg-white/80 backdrop-blur-sm rounded-lg md:rounded-xl p-3 md:p-4 border border-purple-200 hover:shadow-lg transition-all">
            <div className="flex items-center justify-between mb-2 md:mb-3">
              <div className="flex items-center gap-2 min-w-0">
                <Activity className="w-4 h-4 md:w-5 md:h-5 text-purple-600 flex-shrink-0" />
                <span className="text-sm md:text-base font-semibold text-gray-900 truncate">Preprocessing</span>
              </div>
              <span className="px-2 py-0.5 md:py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex-shrink-0">
                Active
              </span>
            </div>
            <p className="text-xs md:text-sm text-gray-600 mb-1 md:mb-2">Quality Optimization</p>
            <div className="flex items-center gap-1 text-xs text-purple-600">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse flex-shrink-0"></div>
              <span>Auto enhancement</span>
            </div>
          </div>
        </div>

        {/* System Performance Bar - RESPONSIVE */}
        <div className="mt-4 md:mt-6 p-3 md:p-4 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg md:rounded-xl text-white">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm md:text-base font-semibold">System Performance</span>
            <span className="text-xs md:text-sm">Optimal</span>
          </div>
          <div className="w-full bg-white/30 rounded-full h-2 mb-2 md:mb-3">
            <div className="bg-white h-2 rounded-full animate-pulse" style={{ width: '98%' }}></div>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs md:text-sm">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span>All engines ready</span>
              </span>
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                <span>High accuracy mode</span>
              </span>
            </div>
            <span className="font-medium">98% Uptime</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
