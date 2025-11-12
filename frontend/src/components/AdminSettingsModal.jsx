import { useState, useEffect } from 'react';
import axios from 'axios';

const sliderPurpleStyle = `
  .slider-purple::-webkit-slider-thumb {
    appearance: none;
    height: 20px;
    width: 20px;
    border-radius: 50%;
    background: #8b5cf6;
    cursor: pointer;
    border: 2px solid #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  .slider-purple::-moz-range-thumb {
    height: 20px;
    width: 20px;
    border-radius: 50%;
    background: #8b5cf6;
    cursor: pointer;
    border: 2px solid #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
`;

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function AdminSettingsModal({ isOpen, onClose }) {
  const [settings, setSettings] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    smtp_from_email: '',
    notification_email: '',
    notification_cooldown_minutes: 60,
    llm_provider: '',
    llm_api_key: '',
    llm_model: '',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/admin/settings`);
      setSettings(response.data);
      setMessage(null);
    } catch (error) {
      console.error('Failed to load settings:', error);
      setMessage({ type: 'error', text: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      await axios.put(`${API_BASE_URL}/admin/settings`, settings);
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
    } catch (error) {
      console.error('Failed to save settings:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to save settings',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTestEmail = async () => {
    setTestingEmail(true);
    setMessage(null);

    try {
      await axios.post(`${API_BASE_URL}/admin/settings/test-email`);
      setMessage({ type: 'success', text: 'Test email sent! Check your inbox.' });
    } catch (error) {
      console.error('Failed to send test email:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to send test email',
      });
    } finally {
      setTestingEmail(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
    setMessage(null);
  };

  if (!isOpen) return null;

  return (
    <>
      <style>{sliderPurpleStyle}</style>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Admin Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSave} className="p-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-blue-600 mx-auto"></div>
              <p className="text-gray-600 mt-2">Loading settings...</p>
            </div>
          ) : (
            <>
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

              {/* Email Notifications Section */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Email Notifications
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure SMTP settings to receive email alerts when services change status.
                  Leave blank to disable notifications.
                </p>

                <div className="space-y-4">
                  {/* SMTP Host */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Host
                    </label>
                    <input
                      type="text"
                      value={settings.smtp_host || ''}
                      onChange={(e) => handleChange('smtp_host', e.target.value)}
                      placeholder="smtp.gmail.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Example: smtp.gmail.com, smtp.sendgrid.net
                    </p>
                  </div>

                  {/* SMTP Port */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Port
                    </label>
                    <input
                      type="number"
                      value={settings.smtp_port}
                      onChange={(e) => handleChange('smtp_port', parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Usually 587 for TLS or 465 for SSL
                    </p>
                  </div>

                  {/* SMTP Username */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Username
                    </label>
                    <input
                      type="text"
                      value={settings.smtp_username || ''}
                      onChange={(e) => handleChange('smtp_username', e.target.value)}
                      placeholder="your-email@gmail.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {/* SMTP Password */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Password
                    </label>
                    <input
                      type="password"
                      value={settings.smtp_password || ''}
                      onChange={(e) => handleChange('smtp_password', e.target.value)}
                      placeholder="••••••••••••••••"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      For Gmail: Use an App Password (not your account password)
                    </p>
                  </div>

                  {/* From Email */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      From Email
                    </label>
                    <input
                      type="email"
                      value={settings.smtp_from_email || ''}
                      onChange={(e) => handleChange('smtp_from_email', e.target.value)}
                      placeholder="status-dashboard@your-domain.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {/* Notification Email */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Notification Email
                    </label>
                    <input
                      type="email"
                      value={settings.notification_email || ''}
                      onChange={(e) => handleChange('notification_email', e.target.value)}
                      placeholder="you@your-domain.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Where to send status change alerts
                    </p>
                  </div>

                  {/* Cooldown Period */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Notification Cooldown (minutes)
                    </label>
                    <input
                      type="number"
                      value={settings.notification_cooldown_minutes}
                      onChange={(e) =>
                        handleChange('notification_cooldown_minutes', parseInt(e.target.value))
                      }
                      min="1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Minimum time between notifications for the same service (prevents spam)
                    </p>
                  </div>
                </div>
              </div>

              {/* AI Intelligence Section */}
              <div className="mb-6 border-t border-gray-200 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  🤖 AI Intelligence
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure AI provider for analyzing service advisories and intelligent chat. OpenAI offers economical models with excellent accuracy.
                </p>

                <div className="space-y-4">
                  {/* Provider Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      AI Provider
                    </label>
                    <select
                      value={settings.llm_provider || ''}
                      onChange={(e) => handleChange('llm_provider', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Select a provider</option>
                      <option value="openai">OpenAI (Recommended)</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="ollama">Ollama (Local)</option>
                      <option value="huggingface">Hugging Face</option>
                    </select>
                  </div>

                  {/* API Key / Endpoint */}
                  {settings.llm_provider && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {settings.llm_provider === 'ollama' ? 'Ollama Endpoint (optional)' : 'API Key'}
                      </label>
                      <input
                        type={settings.llm_provider === 'ollama' ? 'text' : 'password'}
                        value={settings.llm_api_key || ''}
                        onChange={(e) => handleChange('llm_api_key', e.target.value)}
                        placeholder={
                          settings.llm_provider === 'ollama'
                            ? 'http://host.docker.internal:11434/v1'
                            : settings.llm_provider === 'huggingface'
                            ? 'hf_... (optional for public models)'
                            : 'sk-... or your API key'
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {settings.llm_provider === 'openai' &&
                          'Get your API key from platform.openai.com'}
                        {settings.llm_provider === 'anthropic' &&
                          'Get your API key from console.anthropic.com'}
                        {settings.llm_provider === 'ollama' &&
                          'Default: http://host.docker.internal:11434/v1 (leave blank for default)'}
                        {settings.llm_provider === 'huggingface' &&
                          'Get your API token from huggingface.co/settings/tokens (optional for public models)'}
                      </p>
                    </div>
                  )}

                  {/* Model Selection */}
                  {settings.llm_provider && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Model
                      </label>
                      {settings.llm_provider === 'openai' ? (
                        <select
                          value={settings.llm_model || ''}
                          onChange={(e) => handleChange('llm_model', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Select a model</option>
                          <option value="gpt-4o-mini">GPT-4o Mini (Recommended - Best value)</option>
                          <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget friendly)</option>
                          <option value="gpt-4o">GPT-4o (Latest full model)</option>
                          <option value="gpt-4-turbo">GPT-4 Turbo (Previous generation)</option>
                          <option value="gpt-4">GPT-4 (Most capable, expensive)</option>
                        </select>
                      ) : settings.llm_provider === 'anthropic' ? (
                        <select
                          value={settings.llm_model || ''}
                          onChange={(e) => handleChange('llm_model', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Select a model</option>
                          <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Recommended)</option>
                          <option value="claude-3-opus-20240229">Claude 3 Opus (Most capable)</option>
                          <option value="claude-3-sonnet-20240229">Claude 3 Sonnet (Balanced)</option>
                          <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast & economical)</option>
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={settings.llm_model || ''}
                          onChange={(e) => handleChange('llm_model', e.target.value)}
                          placeholder={
                            settings.llm_provider === 'ollama'
                              ? 'e.g., llama3.2, mistral'
                              : 'e.g., model-name'
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {settings.llm_provider === 'openai' &&
                          '💡 gpt-4o-mini is ~60x cheaper than GPT-4 with excellent quality'}
                        {settings.llm_provider === 'anthropic' &&
                          'Choose based on your accuracy and speed requirements'}
                        {settings.llm_provider === 'ollama' &&
                          'Enter model name from `ollama list` (install models with `ollama pull <model>`)'}
                        {settings.llm_provider === 'huggingface' &&
                          'Enter Hugging Face model identifier (e.g., username/model-name)'}
                      </p>
                    </div>
                  )}

                  {/* Info Box */}
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <h4 className="text-sm font-medium text-blue-900 mb-2">
                      What does AI Intelligence enable?
                    </h4>
                    <ul className="text-xs text-blue-700 space-y-1">
                      <li>• Automatic criticality classification (high/medium/low)</li>
                      <li>• Detection of advisories affecting your configured modules</li>
                      <li>• Intelligent chat interface to query status data</li>
                      <li>• Summarization of outages and impact assessment</li>
                    </ul>
                    {settings.llm_provider === 'openai' && (
                      <div className="mt-3 pt-3 border-t border-blue-300">
                        <p className="text-xs text-blue-800 font-medium">
                          💰 Economical OpenAI Models:
                        </p>
                        <ul className="text-xs text-blue-700 space-y-1 mt-1">
                          <li>• <strong>gpt-4o-mini</strong>: Best value - excellent quality at ~$0.15/1M input tokens</li>
                          <li>• <strong>gpt-3.5-turbo</strong>: Ultra-cheap - good for simple tasks at ~$0.50/1M tokens</li>
                          <li>• <strong>gpt-4o</strong>: Latest full model - great balance of cost and capability</li>
                        </ul>
                      </div>
                    )}
                    {settings.llm_provider === 'ollama' && (
                      <div className="mt-3 pt-3 border-t border-blue-300">
                        <p className="text-xs text-blue-800 font-medium">
                          🏠 Local Ollama Setup:
                        </p>
                        <ul className="text-xs text-blue-700 space-y-1 mt-1">
                          <li>1. Install from <a href="https://ollama.com" target="_blank" rel="noopener noreferrer" className="underline">ollama.com</a></li>
                          <li>2. Run: <code className="bg-blue-100 px-1 rounded">ollama pull llama3.2</code></li>
                          <li>3. Ollama runs automatically on localhost:11434</li>
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </form>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-between">
          <button
            type="button"
            onClick={handleTestEmail}
            disabled={testingEmail || loading}
            className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {testingEmail ? 'Sending...' : 'Send Test Email'}
          </button>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              onClick={handleSave}
              disabled={saving || loading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
        </div>
      </div>
    </>
  );
}
