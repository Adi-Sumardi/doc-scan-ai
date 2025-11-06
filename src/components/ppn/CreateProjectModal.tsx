import { useState, FormEvent, useEffect } from 'react';
import { X, Calendar, Building2, FileText } from 'lucide-react';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectData: ProjectFormData) => Promise<void>;
  initialData?: Partial<ProjectFormData>;
  isEditMode?: boolean;
}

export interface ProjectFormData {
  name: string;
  periode_start: string;
  periode_end: string;
  company_npwp: string;
}

const CreateProjectModal = ({ isOpen, onClose, onSubmit, initialData, isEditMode = false }: CreateProjectModalProps) => {
  const [formData, setFormData] = useState<ProjectFormData>({
    name: '',
    periode_start: '',
    periode_end: '',
    company_npwp: '',
  });

  // Update form data when initialData changes (for edit mode)
  useEffect(() => {
    if (isEditMode && initialData) {
      setFormData({
        name: initialData.name || '',
        periode_start: initialData.periode_start || '',
        periode_end: initialData.periode_end || '',
        company_npwp: initialData.company_npwp || '',
      });
    }
  }, [isEditMode, initialData]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof ProjectFormData, string>>>({});
  const [submitError, setSubmitError] = useState<string>('');

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof ProjectFormData, string>> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    }

    if (!formData.periode_start) {
      newErrors.periode_start = 'Start date is required';
    }

    if (!formData.periode_end) {
      newErrors.periode_end = 'End date is required';
    }

    if (formData.periode_start && formData.periode_end) {
      if (new Date(formData.periode_start) > new Date(formData.periode_end)) {
        newErrors.periode_end = 'End date must be after start date';
      }
    }

    if (!formData.company_npwp.trim()) {
      newErrors.company_npwp = 'Company NPWP is required';
    } else {
      // Basic NPWP validation (15 digits with optional dots/dashes)
      const npwpClean = formData.company_npwp.replace(/[.-]/g, '');
      if (!/^\d{15}$/.test(npwpClean)) {
        newErrors.company_npwp = 'NPWP must be 15 digits';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');
    try {
      await onSubmit(formData);
      // Reset form on success
      setFormData({
        name: '',
        periode_start: '',
        periode_end: '',
        company_npwp: '',
      });
      setErrors({});
      setSubmitError('');
      onClose();
    } catch (error: any) {
      console.error(`Failed to ${isEditMode ? 'update' : 'create'} project:`, error);
      setSubmitError(error.message || `Failed to ${isEditMode ? 'update' : 'create'} project. Please try again.`);
      // Don't close modal - let user retry
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setFormData({
        name: '',
        periode_start: '',
        periode_end: '',
        company_npwp: '',
      });
      setErrors({});
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <FileText className="w-6 h-6 text-blue-600" />
              {isEditMode ? 'Edit Reconciliation Project' : 'Create New Reconciliation Project'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {isEditMode ? 'Update your project details' : 'Set up a new reconciliation project for your tax documents'}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Error Alert */}
          {submitError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-800">{submitError}</p>
            </div>
          )}

          {/* Project Name */}
          <div>
            <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 mb-2">
              Project Name <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="project-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., PPN Reconciliation Q4 2024"
                className={`w-full pl-11 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                  errors.name ? 'border-red-500' : 'border-gray-300'
                }`}
                disabled={isSubmitting}
              />
            </div>
            {errors.name && (
              <p className="text-sm text-red-500 mt-1">{errors.name}</p>
            )}
          </div>

          {/* Period Dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Start Date */}
            <div>
              <label htmlFor="periode-start" className="block text-sm font-medium text-gray-700 mb-2">
                Period Start Date <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  id="periode-start"
                  type="date"
                  value={formData.periode_start}
                  onChange={(e) => setFormData({ ...formData, periode_start: e.target.value })}
                  className={`w-full pl-11 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                    errors.periode_start ? 'border-red-500' : 'border-gray-300'
                  }`}
                  disabled={isSubmitting}
                />
              </div>
              {errors.periode_start && (
                <p className="text-sm text-red-500 mt-1">{errors.periode_start}</p>
              )}
            </div>

            {/* End Date */}
            <div>
              <label htmlFor="periode-end" className="block text-sm font-medium text-gray-700 mb-2">
                Period End Date <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  id="periode-end"
                  type="date"
                  value={formData.periode_end}
                  onChange={(e) => setFormData({ ...formData, periode_end: e.target.value })}
                  className={`w-full pl-11 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                    errors.periode_end ? 'border-red-500' : 'border-gray-300'
                  }`}
                  disabled={isSubmitting}
                />
              </div>
              {errors.periode_end && (
                <p className="text-sm text-red-500 mt-1">{errors.periode_end}</p>
              )}
            </div>
          </div>

          {/* Company NPWP */}
          <div>
            <label htmlFor="company-npwp" className="block text-sm font-medium text-gray-700 mb-2">
              Company NPWP <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="company-npwp"
                type="text"
                value={formData.company_npwp}
                onChange={(e) => setFormData({ ...formData, company_npwp: e.target.value })}
                placeholder="e.g., 01.234.567.8-901.000"
                className={`w-full pl-11 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
                  errors.company_npwp ? 'border-red-500' : 'border-gray-300'
                }`}
                disabled={isSubmitting}
                maxLength={20}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Used to automatically split Faktur Pajak into Point A and Point B
            </p>
            {errors.company_npwp && (
              <p className="text-sm text-red-500 mt-1">{errors.company_npwp}</p>
            )}
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">How it works:</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Your Company NPWP is used to automatically identify transactions</li>
              <li>• When NPWP Seller matches your company → Point A (Faktur Keluaran)</li>
              <li>• When NPWP Buyer matches your company → Point B (Faktur Masukan)</li>
              <li>• This reduces manual work and ensures accuracy</li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProjectModal;
