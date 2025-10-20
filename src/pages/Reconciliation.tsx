import { Scale, CheckCircle, Database, Brain, FileSpreadsheet, ArrowRight } from 'lucide-react';

const Reconciliation = () => {
  return (
    <div className="max-w-7xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Header */}
        <div className="flex items-center space-x-4 mb-8">
          <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
            <Scale className="w-10 h-10 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Tax Reconciliation</h1>
            <p className="text-gray-600 mt-1">Automated matching of Tax Invoices & Bank Statements</p>
          </div>
        </div>

        {/* Module Status */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-500 p-6 rounded-r-lg mb-8">
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-6 h-6 text-blue-600 mt-1 flex-shrink-0" />
            <div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">Backend API Ready - 100% Complete</h2>
              <p className="text-gray-700 mb-4">
                Full backend implementation with AI-powered features is complete and ready to use.
                Frontend interface is under development.
              </p>
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Feature 1 */}
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3 mb-3">
              <Database className="w-8 h-8 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-800">70% Code Reuse</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Leverages existing OCR pipeline. No need to re-scan documents - import directly from Faktur Pajak & Rekening Koran results.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3 mb-3">
              <Brain className="w-8 h-8 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-800">Dual AI Power</h3>
            </div>
            <p className="text-gray-600 text-sm">
              GPT-4o extracts vendor names from transactions. Claude extracts invoice numbers. Intelligent auto-matching with confidence scores.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3 mb-3">
              <Scale className="w-8 h-8 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-800">Smart Matching</h3>
            </div>
            <p className="text-gray-600 text-sm">
              4-factor matching algorithm: Amount (50%), Date (25%), Vendor (15%), Reference (10%). High/Medium/Low confidence levels.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3 mb-3">
              <FileSpreadsheet className="w-8 h-8 text-orange-600" />
              <h3 className="text-lg font-semibold text-gray-800">Excel Export</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Comprehensive reports with 4 sheets: Summary, Invoices, Transactions, and Matches. Includes AI metadata and color-coded status.
            </p>
          </div>
        </div>

        {/* API Endpoints */}
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Available API Endpoints</h3>
          <div className="space-y-2 text-sm font-mono">
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/projects</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">GET</span>
              <code className="text-gray-700">/api/reconciliation/projects</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/projects/{'{id}'}/import/batch/invoices</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/projects/{'{id}'}/import/batch/transactions</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/projects/{'{id}'}/ai/extract-vendors</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/projects/{'{id}'}/ai/extract-invoices</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">POST</span>
              <code className="text-gray-700">/api/reconciliation/auto-match</code>
            </div>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">GET</span>
              <code className="text-gray-700">/api/reconciliation/projects/{'{id}'}/export</code>
            </div>
          </div>
        </div>

        {/* Workflow */}
        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Typical Workflow</h3>
          <div className="flex flex-col md:flex-row items-start md:items-center space-y-4 md:space-y-0 md:space-x-4">
            <div className="flex-1">
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <p className="font-semibold text-blue-900 text-sm">1. Create Project</p>
                <p className="text-blue-700 text-xs mt-1">Define period & name</p>
              </div>
            </div>
            <ArrowRight className="hidden md:block w-5 h-5 text-gray-400" />
            <div className="flex-1">
              <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                <p className="font-semibold text-green-900 text-sm">2. Import Data</p>
                <p className="text-green-700 text-xs mt-1">From existing scans</p>
              </div>
            </div>
            <ArrowRight className="hidden md:block w-5 h-5 text-gray-400" />
            <div className="flex-1">
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <p className="font-semibold text-purple-900 text-sm">3. AI Extract</p>
                <p className="text-purple-700 text-xs mt-1">Vendors & invoices</p>
              </div>
            </div>
            <ArrowRight className="hidden md:block w-5 h-5 text-gray-400" />
            <div className="flex-1">
              <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                <p className="font-semibold text-orange-900 text-sm">4. Auto Match</p>
                <p className="text-orange-700 text-xs mt-1">Intelligent matching</p>
              </div>
            </div>
            <ArrowRight className="hidden md:block w-5 h-5 text-gray-400" />
            <div className="flex-1">
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-300">
                <p className="font-semibold text-gray-900 text-sm">5. Export</p>
                <p className="text-gray-700 text-xs mt-1">Download Excel</p>
              </div>
            </div>
          </div>
        </div>

        {/* Development Status */}
        <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            <strong>Development Status:</strong> Frontend UI is being developed. You can use the API endpoints directly
            or wait for the complete UI interface to be released.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Reconciliation;
