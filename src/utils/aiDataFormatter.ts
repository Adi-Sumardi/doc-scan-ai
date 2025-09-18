export interface FormattedField {
  label: string;
  value: string;
  type: 'currency' | 'date' | 'email' | 'id' | 'text' | 'number';
  importance: 'high' | 'medium' | 'low';
  confidence?: number;
}

export interface AIFormattedSection {
  name: string;
  icon: string;
  color: string;
  fields: FormattedField[];
}

export interface AIFormattedData {
  documentType: string;
  confidence: number;
  originalData: any; // Store the original extracted_data
  title: string;
  sections: AIFormattedSection[];
  summary: {
    totalAmount?: number;
    keyInsights: string[];
  };
}

export class AIDataFormatter {
  /**
   * Format document data dengan AI analysis
   */
  static formatDocumentData(result: any): AIFormattedData {
    return {
      documentType: result.document_type,
      confidence: result.confidence,
      originalData: result.extracted_data, // Store original data for pattern matching
      title: result.original_filename || 'Document',
      sections: [], // Not used in simple pattern
      summary: {
        totalAmount: 0,
        keyInsights: []
      }
    };
  }
}