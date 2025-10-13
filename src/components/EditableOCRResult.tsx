import { useState, useEffect, useMemo, memo } from 'react';
import { Edit3, Save, X, Check, AlertCircle, Copy, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { ScanResult } from '../services/api';

interface OCRField {
  key: string;
  label: string;
  value: any;
  type: 'text' | 'number' | 'date' | 'textarea' | 'json';
  editable: boolean;
  confidence?: number;
}

interface EditableOCRResultProps {
  result: ScanResult;
  isEditing: boolean;
  onToggleEdit: () => void;
  onSave: (editedData: any) => void;
}

const EditableOCRResult = ({
  result,
  isEditing,
  onToggleEdit,
  onSave
}: EditableOCRResultProps) => {
  const [editedData, setEditedData] = useState<any>(result.extracted_data || {});
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setEditedData(result.extracted_data || {});
  }, [result]);

  const parseDataToFields = (data: ScanResult): OCRField[] => {
    const fields: OCRField[] = [];

    // Only show Smart Mapped data - skip raw_text, text_lines, and other legacy fields
    if (data.extracted_data) {
      // Only include smart_mapped field
      if (data.extracted_data.smart_mapped) {
        fields.push({
          key: 'smart_mapped',
          label: 'Smart Mapped Data',
          value: JSON.stringify(data.extracted_data.smart_mapped, null, 2),
          type: 'json',
          editable: true,
        });
      }
    }

    return fields;
  };

  const fields = useMemo(() => parseDataToFields({ ...result, extracted_data: editedData }), [editedData, result]);

  const handleFieldChange = (key: string, newValue: any) => {
    setHasChanges(true);
    setEditedData((prev: any) => ({
      ...prev,
      [key]: newValue,
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(editedData);
      setHasChanges(false);
      toast.success('Changes saved successfully!');
    } catch (error) {
      toast.error('Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original data
    setEditedData(result.extracted_data || {});
    setHasChanges(false);
    onToggleEdit();
  };

  const handleCopyField = (value: string) => {
    navigator.clipboard.writeText(value);
    toast.success('Copied to clipboard!');
  };

  const handleCopyAll = () => {
    const allText = fields.map(f => `${f.label}: ${f.value}`).join('\n');
    navigator.clipboard.writeText(allText);
    toast.success('All data copied to clipboard!');
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-lg overflow-hidden shadow-lg">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center">
              <FileText className="w-6 h-6 mr-2" />
              Extracted Data
            </h2>
            <p className="text-blue-100 text-sm mt-1">{result.filename}</p>
          </div>
          
          <div className="flex items-center space-x-2">
            {hasChanges && (
              <span className="bg-yellow-400 text-yellow-900 px-3 py-1 rounded-full text-sm font-medium flex items-center">
                <AlertCircle className="w-4 h-4 mr-1" />
                Unsaved Changes
              </span>
            )}
            
            {isEditing ? (
              <>
                <button
                  onClick={handleSave}
                  disabled={!hasChanges || isSaving}
                  className="bg-white text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors font-medium flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancel}
                  className="bg-white/20 text-white px-4 py-2 rounded-lg hover:bg-white/30 transition-colors font-medium flex items-center"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={onToggleEdit}
                className="bg-white text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors font-medium flex items-center"
              >
                <Edit3 className="w-4 h-4 mr-2" />
                Edit
              </button>
            )}
            
            <button
              onClick={handleCopyAll}
              className="bg-white/20 text-white px-4 py-2 rounded-lg hover:bg-white/30 transition-colors font-medium flex items-center"
              title="Copy all data"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Metadata - Smart Mapper and Document Type Only */}
      <div className="bg-gray-50 px-6 py-3 border-b border-gray-200 text-sm">
        <div className="flex items-center space-x-6">
          <span className="flex items-center text-gray-600">
            <span className="font-semibold text-blue-600 mr-2">Smart Mapped</span>
            <span className="text-green-600 font-medium">✓ AI Processed</span>
          </span>
          <span className="text-gray-400">|</span>
          <span className="text-gray-600">
            Document Type: <span className="font-medium text-gray-900">{result.document_type}</span>
          </span>
        </div>
      </div>

      {/* Fields */}
      <div className="flex-1 overflow-auto p-6">
        <div className="space-y-4 max-w-4xl mx-auto">
          {fields.map((field) => (
            <div key={field.key} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-gray-700 flex items-center">
                  {field.label}
                  {field.confidence !== undefined && (
                    <span className="ml-2 text-xs text-gray-500">
                      ({(field.confidence * 100).toFixed(0)}% confidence)
                    </span>
                  )}
                </label>
                <button
                  onClick={() => handleCopyField(String(field.value))}
                  className="text-gray-400 hover:text-blue-600 transition-colors"
                  title="Copy field"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              
              {isEditing && field.editable ? (
                field.type === 'textarea' || field.type === 'json' ? (
                  <textarea
                    value={field.value}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    rows={field.type === 'json' ? 10 : 5}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y font-mono text-sm"
                  />
                ) : (
                  <input
                    type={field.type}
                    value={field.value}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                )
              ) : (
                <div className="bg-gray-50 px-3 py-2 rounded-lg">
                  {field.type === 'json' ? (
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono overflow-x-auto max-h-96 overflow-y-auto">
                      {field.value}
                    </pre>
                  ) : (
                    <p className="text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {field.value || <span className="text-gray-400 italic">No data</span>}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium">No extracted data available</p>
              <p className="text-sm mt-2">The OCR process did not extract any structured data from this document.</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      {isEditing && (
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-600 flex items-center">
            <Check className="w-4 h-4 mr-1 text-green-600" />
            Edit mode enabled - Make your changes and click Save
          </div>
          <div className="flex space-x-3">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              Discard Changes
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save All Changes'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// Wrap with React.memo to prevent unnecessary re-renders when parent re-renders
export default memo(EditableOCRResult);
