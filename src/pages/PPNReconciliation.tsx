import { useState, useEffect } from 'react';
import { FileSpreadsheet, Plus, FolderOpen, CheckCircle, AlertCircle, Edit2, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import Swal from 'sweetalert2';
import CreateProjectModal, { ProjectFormData } from '../components/ppn/CreateProjectModal';

interface Project {
  id: string;
  name: string;
  periode_start: string;
  periode_end: string;
  company_npwp: string;
  status: 'draft' | 'in_progress' | 'completed';
  created_at: string;
  point_a_count?: number;
  point_b_count?: number;
  point_c_count?: number;
  point_e_count?: number;
}

const PPNReconciliation = () => {
  const navigate = useNavigate();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/reconciliation-ppn/projects', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch projects');
      }

      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      toast.error('Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProject = async (projectData: ProjectFormData) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/reconciliation-ppn/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(projectData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create project');
      }

      const newProject = await response.json();
      setProjects([newProject, ...projects]);
      setIsCreateModalOpen(false);
      toast.success('Project created successfully!');
    } catch (error: any) {
      console.error('Failed to create project:', error);
      toast.error(error.message || 'Failed to create project');
      throw error; // Re-throw to let modal handle it
    }
  };

  const handleEditProject = async (projectData: ProjectFormData) => {
    if (!editingProject) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/reconciliation-ppn/projects/${editingProject.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(projectData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update project');
      }

      const updatedProject = await response.json();
      setProjects(projects.map(p => p.id === updatedProject.id ? updatedProject : p));
      setIsEditModalOpen(false);
      setEditingProject(null);
      toast.success('Project updated successfully!');
    } catch (error: any) {
      console.error('Failed to update project:', error);
      toast.error(error.message || 'Failed to update project');
      throw error;
    }
  };

  const handleDeleteProject = async (projectId: string, projectName: string) => {
    const result = await Swal.fire({
      title: 'Delete Project?',
      html: `Are you sure you want to delete project <strong>"${projectName}"</strong>?<br><br>This action cannot be undone.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#dc2626',
      cancelButtonColor: '#6b7280',
      confirmButtonText: 'Yes, delete it!',
      cancelButtonText: 'Cancel',
      reverseButtons: true,
      focusCancel: true
    });

    if (!result.isConfirmed) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/reconciliation-ppn/projects/${projectId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete project');
      }

      setProjects(projects.filter(p => p.id !== projectId));

      Swal.fire({
        title: 'Deleted!',
        text: 'Project has been deleted successfully.',
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
      });
    } catch (error: any) {
      console.error('Failed to delete project:', error);
      Swal.fire({
        title: 'Error!',
        text: error.message || 'Failed to delete project',
        icon: 'error',
        confirmButtonColor: '#dc2626'
      });
    }
  };

  const handleProjectClick = (projectId: string) => {
    navigate(`/ppn-reconciliation/${projectId}`);
  };

  const handleEditClick = (e: React.MouseEvent, project: Project) => {
    e.stopPropagation(); // Prevent navigation
    setEditingProject(project);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (e: React.MouseEvent, project: Project) => {
    e.stopPropagation(); // Prevent navigation
    handleDeleteProject(project.id, project.name);
  };

  const getStatusColor = (status: Project['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: Project['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4" />;
      case 'in_progress':
        return <AlertCircle className="w-4 h-4" />;
      case 'draft':
        return <FolderOpen className="w-4 h-4" />;
      default:
        return <FolderOpen className="w-4 h-4" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 flex items-center gap-2 md:gap-3">
              <FileSpreadsheet className="w-6 h-6 md:w-8 md:h-8 text-blue-600" />
              Reconciliation
            </h1>
            <p className="text-sm md:text-base text-gray-600 mt-1 md:mt-2">
              Rekonsiliasi komprehensif untuk Faktur Pajak Keluaran, Masukan, dan Bukti Potong
            </p>
          </div>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center justify-center gap-2 px-4 py-2.5 md:px-6 md:py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md whitespace-nowrap"
          >
            <Plus className="w-4 h-4 md:w-5 md:h-5" />
            <span className="text-sm md:text-base">New Project</span>
          </button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-xl border border-blue-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <h3 className="font-semibold text-blue-900">Point A vs C</h3>
          </div>
          <p className="text-sm text-blue-700">
            Faktur Keluaran vs Bukti Potong Lawan Transaksi
          </p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-xl border border-green-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <h3 className="font-semibold text-green-900">Invoice vs Payment</h3>
          </div>
          <p className="text-sm text-green-700">
            Rekonsiliasi Invoice dengan Rekening Koran
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-xl border border-purple-200">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <h3 className="font-semibold text-purple-900">Summary Report</h3>
          </div>
          <p className="text-sm text-purple-700">
            Laporan lengkap rekonsiliasi pajak
          </p>
        </div>
      </div>

      {/* Projects List */}
      <div className="bg-white rounded-xl shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Reconciliation Projects</h2>
          <p className="text-sm text-gray-600 mt-1">Manage your reconciliation projects</p>
        </div>

        <div className="p-6">
          {isLoading ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-12">
              <FolderOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Projects Yet</h3>
              <p className="text-gray-600 mb-6">
                Create your first reconciliation project to get started
              </p>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-5 h-5" />
                Create New Project
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {projects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => handleProjectClick(project.id)}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                >
                  {/* Mobile & Tablet Layout */}
                  <div className="flex flex-col gap-3">
                    {/* Header Row */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base md:text-lg font-semibold text-gray-900 truncate">{project.name}</h3>
                        <span className={`inline-flex items-center gap-1 px-2 md:px-3 py-1 rounded-full text-xs font-medium mt-1 ${getStatusColor(project.status)}`}>
                          {getStatusIcon(project.status)}
                          <span className="hidden sm:inline">{project.status.charAt(0).toUpperCase() + project.status.slice(1)}</span>
                        </span>
                      </div>
                      <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
                        <button
                          onClick={(e) => handleEditClick(e, project)}
                          className="p-1.5 md:p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit project"
                        >
                          <Edit2 className="w-4 h-4 md:w-5 md:h-5" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteClick(e, project)}
                          className="p-1.5 md:p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete project"
                        >
                          <Trash2 className="w-4 h-4 md:w-5 md:h-5" />
                        </button>
                      </div>
                    </div>

                    {/* Period & Date */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs md:text-sm text-gray-600">
                      <p className="truncate">
                        Periode: {project.periode_start} to {project.periode_end}
                      </p>
                      <p className="text-gray-500 flex-shrink-0">
                        Created: {new Date(project.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    {/* Data Counts */}
                    {(project.point_a_count || project.point_b_count || project.point_c_count || project.point_e_count) && (
                      <div className="flex flex-wrap items-center gap-2 md:gap-4 text-xs md:text-sm text-gray-600">
                        {project.point_a_count ? (
                          <span className="bg-gray-50 px-2 py-1 rounded">Point A: {project.point_a_count}</span>
                        ) : null}
                        {project.point_b_count ? (
                          <span className="bg-gray-50 px-2 py-1 rounded">Point B: {project.point_b_count}</span>
                        ) : null}
                        {project.point_c_count ? (
                          <span className="bg-gray-50 px-2 py-1 rounded">Point C: {project.point_c_count}</span>
                        ) : null}
                        {project.point_e_count ? (
                          <span className="bg-gray-50 px-2 py-1 rounded">Point E: {project.point_e_count}</span>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateProject}
      />

      {/* Edit Project Modal */}
      <CreateProjectModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingProject(null);
        }}
        onSubmit={handleEditProject}
        initialData={editingProject ? {
          name: editingProject.name,
          company_npwp: editingProject.company_npwp,
          periode_start: editingProject.periode_start,
          periode_end: editingProject.periode_end
        } : undefined}
        isEditMode={true}
      />
    </div>
  );
};

export default PPNReconciliation;
