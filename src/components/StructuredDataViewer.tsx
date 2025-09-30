import React from 'react';
import { ChevronRight } from 'lucide-react';

interface StructuredDataViewerProps {
  data: any;
  className?: string;
}

const DataRow: React.FC<{ label: string; value: any; level?: number }> = ({ label, value, level = 0 }) => {
  const isObject = typeof value === 'object' && value !== null && !Array.isArray(value);
  const isArray = Array.isArray(value);

  const renderValue = (val: any) => {
    if (val === null || val === undefined) {
      return <span className="text-sm text-gray-400 italic">N/A</span>;
    }
    if (typeof val === 'boolean') {
      return <span className={`text-sm font-medium ${val ? 'text-green-600' : 'text-red-600'}`}>{val ? 'Yes' : 'No'}</span>;
    }
    return <span className="text-sm text-gray-800 text-right break-all">{String(val)}</span>;
  };

  return (
    <div style={{ marginLeft: `${level * 1.5}rem` }}>
      <div className="flex justify-between items-start py-2 border-b border-gray-100">
        <span className="font-medium text-sm text-gray-600 capitalize">{label.replace(/_/g, ' ')}:</span>
        {!isObject && !isArray && (
          renderValue(value)
        )}
      </div>
      {isObject && (
        <div className="pb-2">
          {Object.entries(value).map(([key, val]) => (
            <DataRow key={key} label={key} value={val} level={level + 1} />
          ))}
        </div>
      )}
      {isArray && (
        <div className="pb-2">
          {value.map((item, index) => (
            <div key={index} className="pl-4 mt-2 border-l-2 border-blue-200">
               <div className="flex items-center text-xs text-blue-600 font-semibold mb-1">
                 <ChevronRight className="w-3 h-3 mr-1" /> Item {index + 1}
               </div>
              {typeof item === 'object' ? (
                Object.entries(item).map(([key, val]) => (
                  <DataRow key={key} label={key} value={val} level={level + 1} />
                ))
              ) : (
                renderValue(item)
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const StructuredDataViewer: React.FC<StructuredDataViewerProps> = ({ data, className = '' }) => {
  return (
    <div className={`bg-white rounded-lg p-4 border ${className}`}>
      {Object.entries(data).map(([key, value]) => (
        <DataRow key={key} label={key} value={value} />
      ))}
    </div>
  );
};

export default StructuredDataViewer;