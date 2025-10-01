import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { 
  Users, 
  Activity, 
  Shield, 
  FileText, 
  Clock, 
  CheckCircle, 
  XCircle,
  Key,
  RefreshCw,
  Eye,
  Ban,
  CheckSquare
} from 'lucide-react';
import toast from 'react-hot-toast';

interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login: string | null;
  total_batches: number;
  last_activity: string | null;
}

interface DashboardStats {
  users: {
    total: number;
    active: number;
    inactive: number;
    admins: number;
    new_this_week: number;
  };
  batches: {
    total: number;
    completed: number;
    processing: number;
    failed: number;
    this_week: number;
  };
  files: {
    total: number;
  };
}

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showResetModal, setShowResetModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    // Check if user is admin
    if (!user?.is_admin) {
      toast.error('Access denied. Admin only.');
      navigate('/dashboard');
      return;
    }

    fetchDashboardData();
  }, [user, navigate]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [usersRes, statsRes] = await Promise.all([
        api.get('/api/admin/users'),
        api.get('/api/admin/dashboard/stats')
      ]);
      
      setUsers(usersRes.data);
      setStats(statsRes.data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUserStatus = async (userId: string, currentStatus: boolean) => {
    try {
      await api.patch(`/api/admin/users/${userId}/status`, null, {
        params: { is_active: !currentStatus }
      });
      
      toast.success(`User ${!currentStatus ? 'activated' : 'deactivated'} successfully`);
      fetchDashboardData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update user status');
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser) return;
    
    if (!newPassword || newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    try {
      await api.post(`/api/admin/users/${selectedUser.id}/reset-password`, null, {
        params: { new_password: newPassword }
      });
      
      toast.success(`Password reset for ${selectedUser.username}`);
      setShowResetModal(false);
      setNewPassword('');
      setSelectedUser(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleGenerateTempPassword = async (userId: string, username: string) => {
    try {
      const response = await api.post(`/api/admin/users/${userId}/generate-temp-password`);
      const tempPassword = response.data.temp_password;
      
      // Copy to clipboard
      navigator.clipboard.writeText(tempPassword);
      
      toast.success(
        <div>
          <div className="font-bold">Temp password generated for {username}!</div>
          <div className="text-sm mt-1">Password: <span className="font-mono font-bold">{tempPassword}</span></div>
          <div className="text-xs text-gray-500 mt-1">Copied to clipboard!</div>
        </div>,
        { duration: 8000 }
      );
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to generate temp password');
    }
  };

  const handleViewActivities = (userId: string) => {
    navigate(`/admin/user-activities/${userId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          <span className="text-gray-600">Loading admin dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg p-6 shadow-lg text-white">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
            <Shield className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
            <p className="text-blue-100 mt-1">System Overview & User Management</p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total Users */}
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <span className="text-xs text-gray-500">Total</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{stats.users.total}</div>
            <div className="text-sm text-gray-600 mt-1">Users</div>
            <div className="mt-2 flex items-center text-xs text-green-600">
              <CheckCircle className="w-3 h-3 mr-1" />
              {stats.users.active} active
            </div>
          </div>

          {/* Total Batches */}
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <span className="text-xs text-gray-500">Total</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{stats.batches.total}</div>
            <div className="text-sm text-gray-600 mt-1">Batches</div>
            <div className="mt-2 flex items-center text-xs text-blue-600">
              <Activity className="w-3 h-3 mr-1" />
              {stats.batches.this_week} this week
            </div>
          </div>

          {/* Total Files */}
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-purple-600" />
              </div>
              <span className="text-xs text-gray-500">Total</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{stats.files.total}</div>
            <div className="text-sm text-gray-600 mt-1">Files Scanned</div>
            <div className="mt-2 flex items-center text-xs text-purple-600">
              <CheckCircle className="w-3 h-3 mr-1" />
              {stats.batches.completed} completed
            </div>
          </div>

          {/* Admin Users */}
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-xs text-gray-500">Admin</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{stats.users.admins}</div>
            <div className="text-sm text-gray-600 mt-1">Administrators</div>
            <div className="mt-2 flex items-center text-xs text-orange-600">
              <Users className="w-3 h-3 mr-1" />
              {stats.users.new_this_week} new users
            </div>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <Users className="w-6 h-6 mr-2 text-blue-600" />
            User Management
          </h2>
          <p className="text-sm text-gray-600 mt-1">Manage all registered users</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Activity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <div className="ml-3">
                        <div className="text-sm font-medium text-gray-900">{u.username}</div>
                        <div className="text-xs text-gray-500">{u.full_name || 'No name'}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{u.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      u.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {u.is_active ? (
                        <>
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Active
                        </>
                      ) : (
                        <>
                          <XCircle className="w-3 h-3 mr-1" />
                          Inactive
                        </>
                      )}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      u.is_admin 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {u.is_admin ? (
                        <>
                          <Shield className="w-3 h-3 mr-1" />
                          Admin
                        </>
                      ) : (
                        'User'
                      )}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{u.total_batches} batches</div>
                    {u.last_activity && (
                      <div className="text-xs text-gray-500">{new Date(u.last_activity).toLocaleDateString()}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-900">
                      <Clock className="w-4 h-4 mr-1 text-gray-400" />
                      {u.last_login 
                        ? new Date(u.last_login).toLocaleString() 
                        : 'Never'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center space-x-2">
                      <div className="relative group">
                        <button
                          onClick={() => handleViewActivities(u.id)}
                          className="text-blue-600 hover:text-blue-800 p-2 rounded hover:bg-blue-50 transition-all"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                          View Activities
                        </div>
                      </div>
                      
                      {user?.id !== u.id && (
                        <div className="relative group">
                          <button
                            onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                            className={`p-2 rounded transition-all ${
                              u.is_active 
                                ? 'text-red-600 hover:text-red-800 hover:bg-red-50' 
                                : 'text-green-600 hover:text-green-800 hover:bg-green-50'
                            }`}
                          >
                            {u.is_active ? <Ban className="w-4 h-4" /> : <CheckSquare className="w-4 h-4" />}
                          </button>
                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                            {u.is_active ? 'Deactivate User' : 'Activate User'}
                          </div>
                        </div>
                      )}
                      
                      <div className="relative group">
                        <button
                          onClick={() => {
                            setSelectedUser(u);
                            setShowResetModal(true);
                          }}
                          className="text-orange-600 hover:text-orange-800 p-2 rounded hover:bg-orange-50 transition-all"
                        >
                          <Key className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                          Reset Password
                        </div>
                      </div>
                      
                      <div className="relative group">
                        <button
                          onClick={() => handleGenerateTempPassword(u.id, u.username)}
                          className="text-purple-600 hover:text-purple-800 p-2 rounded hover:bg-purple-50 transition-all"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                          Generate Temp Password
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reset Password Modal */}
      {showResetModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900 flex items-center">
                <Key className="w-6 h-6 mr-2 text-orange-600" />
                Reset Password
              </h3>
              <button
                onClick={() => {
                  setShowResetModal(false);
                  setNewPassword('');
                  setSelectedUser(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                Reset password for user: <span className="font-bold text-gray-900">{selectedUser.username}</span>
              </p>
              <input
                type="text"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password (min 6 chars)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={handleResetPassword}
                className="flex-1 bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 transition-colors font-medium"
              >
                Reset Password
              </button>
              <button
                onClick={() => {
                  setShowResetModal(false);
                  setNewPassword('');
                  setSelectedUser(null);
                }}
                className="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
