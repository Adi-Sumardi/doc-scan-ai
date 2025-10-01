import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { 
  ArrowLeft,
  FileText,
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  Activity,
  Download
} from 'lucide-react';
import toast from 'react-hot-toast';

interface UserActivity {
  user: {
    id: string;
    username: string;
    email: string;
    full_name: string;
    is_active: boolean;
    created_at: string;
    last_login: string | null;
  };
  batches: Array<{
    id: string;
    created_at: string;
    status: string;
    file_count: number;
    processing_time: number | null;
    file_names: string[];
  }>;
}

const UserActivities = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [activities, setActivities] = useState<UserActivity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.is_admin) {
      toast.error('Access denied. Admin only.');
      navigate('/dashboard');
      return;
    }

    fetchUserActivities();
  }, [userId, user, navigate]);

  const fetchUserActivities = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/admin/users/${userId}/activities`);
      setActivities(response.data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load user activities');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <Activity className="w-6 h-6 animate-spin text-blue-500" />
          <span className="text-gray-600">Loading user activities...</span>
        </div>
      </div>
    );
  }

  if (!activities) {
    return (
      <div className="text-center py-12">
        <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">User not found</h3>
      </div>
    );
  }

  const { user: userData, batches } = activities;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/admin')}
        className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
      >
        <ArrowLeft className="w-5 h-5 mr-2" />
        Back to Admin Dashboard
      </button>

      {/* User Info Card */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-4 md:p-6 shadow-lg text-white">
        <div className="flex flex-col sm:flex-row items-center sm:space-x-4 space-y-3 sm:space-y-0">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center text-2xl font-bold">
            {userData.username.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 text-center sm:text-left">
            <h1 className="text-xl md:text-2xl font-bold">{userData.username}</h1>
            <p className="text-blue-100 text-sm md:text-base">{userData.email}</p>
            {userData.full_name && (
              <p className="text-xs md:text-sm text-blue-200 mt-1">{userData.full_name}</p>
            )}
          </div>
          <div>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              userData.is_active 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {userData.is_active ? (
                <>
                  <CheckCircle className="w-4 h-4 mr-1" />
                  Active
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 mr-1" />
                  Inactive
                </>
              )}
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
          <div className="bg-white/10 rounded-lg p-3">
            <div className="flex items-center text-sm text-blue-100 mb-1">
              <Calendar className="w-4 h-4 mr-1" />
              Joined
            </div>
            <div className="text-white font-medium">
              {new Date(userData.created_at).toLocaleDateString()}
            </div>
          </div>
          
          <div className="bg-white/10 rounded-lg p-3">
            <div className="flex items-center text-sm text-blue-100 mb-1">
              <Clock className="w-4 h-4 mr-1" />
              Last Login
            </div>
            <div className="text-white font-medium">
              {userData.last_login 
                ? new Date(userData.last_login).toLocaleDateString()
                : 'Never'}
            </div>
          </div>
          
          <div className="bg-white/10 rounded-lg p-3">
            <div className="flex items-center text-sm text-blue-100 mb-1">
              <FileText className="w-4 h-4 mr-1" />
              Total Batches
            </div>
            <div className="text-white font-medium text-2xl">
              {batches.length}
            </div>
          </div>
        </div>
      </div>

      {/* Activities List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <Activity className="w-6 h-6 mr-2 text-blue-600" />
            Upload History ({batches.length} batches)
          </h2>
        </div>

        {batches.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Activities Yet</h3>
            <p className="text-gray-600">This user hasn't uploaded any documents.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {batches.map((batch) => (
              <div key={batch.id} className="p-4 md:p-6 hover:bg-gray-50 transition-colors">
                <div className="flex flex-col sm:flex-row items-start sm:justify-between mb-3 space-y-2 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      batch.status === 'completed' 
                        ? 'bg-green-100' 
                        : batch.status === 'failed'
                        ? 'bg-red-100'
                        : 'bg-blue-100'
                    }`}>
                      <FileText className={`w-6 h-6 ${
                        batch.status === 'completed' 
                          ? 'text-green-600' 
                          : batch.status === 'failed'
                          ? 'text-red-600'
                          : 'text-blue-600'
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        Batch {batch.id.substring(0, 8)}
                      </h3>
                      <div className="flex items-center text-sm text-gray-500 mt-1">
                        <Clock className="w-4 h-4 mr-1" />
                        {new Date(batch.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                    batch.status === 'completed' 
                      ? 'bg-green-100 text-green-800' 
                      : batch.status === 'failed'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {batch.status === 'completed' && <CheckCircle className="w-3 h-3 mr-1" />}
                    {batch.status === 'failed' && <XCircle className="w-3 h-3 mr-1" />}
                    {batch.status}
                  </span>
                </div>

                <div className="sm:ml-13 space-y-2">
                  <div className="flex flex-wrap items-center text-sm text-gray-600 gap-2">
                    <div className="flex items-center">
                      <Download className="w-4 h-4 mr-2 text-gray-400" />
                      <span className="font-medium">{batch.file_count} files</span>
                    </div>
                    {batch.processing_time && (
                      <span className="text-gray-500">
                        • Processing time: {batch.processing_time.toFixed(2)}s
                      </span>
                    )}
                  </div>

                  {batch.file_names.length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-3 mt-2">
                      <div className="text-xs font-medium text-gray-700 mb-2">Files:</div>
                      <div className="space-y-1">
                        {batch.file_names.map((fileName, idx) => (
                          <div key={idx} className="text-xs text-gray-600 flex items-center">
                            <FileText className="w-3 h-3 mr-1 text-gray-400" />
                            {fileName}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserActivities;
