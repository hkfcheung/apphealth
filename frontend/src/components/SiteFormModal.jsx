import React, { useState, useEffect } from 'react';

export default function SiteFormModal({ isOpen, onClose, onSubmit, site = null }) {
  const [formData, setFormData] = useState({
    id: '',
    display_name: '',
    status_page: '',
    feed_url: '',
    poll_frequency_seconds: 300,
    parser: 'auto',
    is_active: true,
    console_only: false,
    use_playwright: false,
  });

  useEffect(() => {
    if (site) {
      setFormData(site);
    } else {
      setFormData({
        id: '',
        display_name: '',
        status_page: '',
        feed_url: '',
        poll_frequency_seconds: 300,
        parser: 'auto',
        is_active: true,
        console_only: false,
        use_playwright: false,
      });
    }
  }, [site, isOpen]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">
            {site ? 'Edit Site' : 'Add New Site'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Site ID *
              </label>
              <input
                type="text"
                name="id"
                value={formData.id}
                onChange={handleChange}
                disabled={!!site}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                placeholder="e.g., aws-status"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Display Name *
              </label>
              <input
                type="text"
                name="display_name"
                value={formData.display_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., AWS Service Health"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status Page URL *
              </label>
              <input
                type="url"
                name="status_page"
                value={formData.status_page}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://status.example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Feed URL (optional)
              </label>
              <input
                type="url"
                name="feed_url"
                value={formData.feed_url}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://status.example.com/feed.rss or .../summary.json"
              />
              <p className="text-xs text-gray-500 mt-1">
                RSS/Atom feed or JSON API endpoint. Leave empty for HTML scraping.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Poll Frequency (seconds)
                </label>
                <input
                  type="number"
                  name="poll_frequency_seconds"
                  value={formData.poll_frequency_seconds}
                  onChange={handleChange}
                  min="60"
                  max="3600"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Parser Type
                </label>
                <select
                  name="parser"
                  value={formData.parser}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="auto">Auto</option>
                  <option value="json">JSON</option>
                  <option value="rss">RSS/Atom</option>
                  <option value="html">HTML</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Active</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="console_only"
                  checked={formData.console_only}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Console Only</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="use_playwright"
                  checked={formData.use_playwright}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Use Browser (Playwright)</span>
              </label>
            </div>

            <div className="flex gap-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
              >
                {site ? 'Update Site' : 'Add Site'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
