import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Suggested modules based on service type
const SUGGESTED_MODULES = {
  'microsoft-365': [
    'Exchange Online',
    'Teams',
    'SharePoint Online',
    'OneDrive for Business',
    'Outlook',
    'Azure Active Directory',
  ],
  'aws': [
    'EC2',
    'S3',
    'Lambda',
    'CloudFront',
    'RDS',
    'ECS',
    'DynamoDB',
  ],
  'slack': [
    'Messaging',
    'Calls',
    'Huddles',
    'Notifications',
    'Search',
  ],
  'google-workspace': [
    'Gmail',
    'Google Drive',
    'Google Calendar',
    'Google Meet',
    'Google Docs',
  ],
};

export default function ModuleConfigModal({ isOpen, onClose, site }) {
  const [modules, setModules] = useState([]);
  const [newModuleName, setNewModuleName] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (isOpen && site) {
      loadModules();
    }
  }, [isOpen, site]);

  const loadModules = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/intelligence/sites/${site.site_id}/modules`);
      setModules(response.data);
    } catch (error) {
      console.error('Failed to load modules:', error);
      setMessage({ type: 'error', text: 'Failed to load modules' });
    } finally {
      setLoading(false);
    }
  };

  const handleAddModule = async (moduleName) => {
    if (!moduleName.trim()) return;

    // Check if module already exists
    if (modules.some(m => m.module_name.toLowerCase() === moduleName.toLowerCase())) {
      setMessage({ type: 'error', text: 'Module already exists' });
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/intelligence/sites/${site.site_id}/modules`,
        {
          site_id: site.site_id,
          module_name: moduleName,
          enabled: true,
        }
      );
      setModules([...modules, response.data]);
      setNewModuleName('');
      setMessage({ type: 'success', text: `Added "${moduleName}"` });
    } catch (error) {
      console.error('Failed to add module:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to add module',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleModule = async (module) => {
    try {
      const response = await axios.patch(
        `${API_BASE_URL}/intelligence/modules/${module.id}`,
        { enabled: !module.enabled }
      );
      setModules(modules.map(m => m.id === module.id ? response.data : m));
    } catch (error) {
      console.error('Failed to toggle module:', error);
      setMessage({ type: 'error', text: 'Failed to update module' });
    }
  };

  const handleDeleteModule = async (moduleId) => {
    if (!confirm('Are you sure you want to remove this module?')) return;

    try {
      await axios.delete(`${API_BASE_URL}/intelligence/modules/${moduleId}`);
      setModules(modules.filter(m => m.id !== moduleId));
      setMessage({ type: 'success', text: 'Module removed' });
    } catch (error) {
      console.error('Failed to delete module:', error);
      setMessage({ type: 'error', text: 'Failed to remove module' });
    }
  };

  const getSuggestedModules = () => {
    if (!site) return [];

    // Try to match site ID to suggested modules
    for (const [key, suggestions] of Object.entries(SUGGESTED_MODULES)) {
      if (site.site_id.toLowerCase().includes(key)) {
        // Filter out already added modules
        return suggestions.filter(
          suggested => !modules.some(m => m.module_name.toLowerCase() === suggested.toLowerCase())
        );
      }
    }

    return [];
  };

  if (!isOpen || !site) return null;

  const suggestedModules = getSuggestedModules();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Configure Modules</h2>
            <p className="text-sm text-gray-600 mt-1">{site.display_name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Info Box */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <h3 className="text-sm font-medium text-blue-900 mb-2">
              Why configure modules?
            </h3>
            <p className="text-xs text-blue-700">
              AI Intelligence uses your configured modules to determine which service advisories
              are relevant to your organization. For example, if you only use Exchange Online,
              advisories about Teams won't be marked as affecting you.
            </p>
          </div>

          {/* Message */}
          {message && (
            <div
              className={`mb-4 p-3 rounded-md ${
                message.type === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Add New Module */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Add Module/Package
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newModuleName}
                onChange={(e) => setNewModuleName(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddModule(newModuleName);
                  }
                }}
                placeholder="e.g., Exchange Online, Teams, EC2"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={saving}
              />
              <button
                onClick={() => handleAddModule(newModuleName)}
                disabled={saving || !newModuleName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Add
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Use vendor terminology when possible (e.g., "Exchange Online" not "Exchange")
            </p>
          </div>

          {/* Suggested Modules */}
          {suggestedModules.length > 0 && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Suggested Modules
              </label>
              <div className="flex flex-wrap gap-2">
                {suggestedModules.map((suggested) => (
                  <button
                    key={suggested}
                    onClick={() => handleAddModule(suggested)}
                    className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    + {suggested}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Configured Modules List */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Configured Modules ({modules.length})
            </label>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-600 mx-auto"></div>
                <p className="text-gray-600 mt-2 text-sm">Loading modules...</p>
              </div>
            ) : modules.length === 0 ? (
              <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-md">
                <p className="text-gray-500 text-sm">No modules configured yet</p>
                <p className="text-gray-400 text-xs mt-1">
                  Add modules above to enable intelligent advisory filtering
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {modules.map((module) => (
                  <div
                    key={module.id}
                    className={`flex items-center justify-between p-3 border rounded-md transition-colors ${
                      module.enabled
                        ? 'border-gray-300 bg-white'
                        : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 flex-1">
                      {/* Enable/Disable Toggle */}
                      <button
                        onClick={() => handleToggleModule(module)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          module.enabled ? 'bg-blue-600' : 'bg-gray-300'
                        }`}
                        aria-label={`${module.enabled ? 'Disable' : 'Enable'} ${module.module_name}`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            module.enabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>

                      {/* Module Name */}
                      <span
                        className={`text-sm font-medium ${
                          module.enabled ? 'text-gray-900' : 'text-gray-500'
                        }`}
                      >
                        {module.module_name}
                      </span>
                    </div>

                    {/* Delete Button */}
                    <button
                      onClick={() => handleDeleteModule(module.id)}
                      className="text-red-600 hover:text-red-800 text-sm transition-colors"
                      aria-label={`Delete ${module.module_name}`}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
