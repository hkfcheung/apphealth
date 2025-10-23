import React, { useState, useEffect } from 'react';
import axios from 'axios';

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
                  AI Intelligence (Optional)
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure AI to analyze service advisories and enable intelligent chat.
                  If no provider is selected, basic keyword matching will be used.
                </p>

                <div className="space-y-4">
                  {/* LLM Provider */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      LLM Provider
                    </label>
                    <select
                      value={settings.llm_provider || ''}
                      onChange={(e) => handleChange('llm_provider', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">None (Basic Keywords Only)</option>
                      <option value="openai">OpenAI (GPT-4, GPT-3.5)</option>
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="ollama">Ollama (Local LLM)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      {settings.llm_provider === 'ollama'
                        ? 'Run LLMs locally with Ollama - no API key needed!'
                        : 'Select an AI provider for advanced advisory analysis'}
                    </p>
                  </div>

                  {/* Show API Key and Model fields only if provider is selected */}
                  {settings.llm_provider && (
                    <>
                      {/* API Key / Endpoint URL */}
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
                        </p>
                      </div>

                      {/* Model Selection */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Model
                        </label>
                        {settings.llm_provider === 'ollama' ? (
                          // For Ollama: Use text input with datalist for suggestions
                          <>
                            <input
                              type="text"
                              list="ollama-models"
                              value={settings.llm_model || ''}
                              onChange={(e) => handleChange('llm_model', e.target.value)}
                              placeholder="e.g., deepseek-r1:1.5b"
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            <datalist id="ollama-models">
                              <option value="llava">llava (Vision - can analyze images)</option>
                              <option value="llava:13b">llava 13B (Vision - higher quality)</option>
                              <option value="llama3.2">Llama 3.2</option>
                              <option value="llama3.1">Llama 3.1</option>
                              <option value="llama3.1:70b">Llama 3.1 70B</option>
                              <option value="mistral">Mistral</option>
                              <option value="mixtral">Mixtral</option>
                              <option value="qwen2.5">Qwen 2.5</option>
                              <option value="phi3">Phi 3</option>
                              <option value="gemma2">Gemma 2</option>
                              <option value="deepseek-r1:1.5b">DeepSeek R1 1.5B</option>
                              <option value="deepseek-r1:7b">DeepSeek R1 7B</option>
                              <option value="deepseek-r1:14b">DeepSeek R1 14B</option>
                            </datalist>
                          </>
                        ) : (
                          // For OpenAI/Anthropic: Use dropdown
                          <select
                            value={settings.llm_model || ''}
                            onChange={(e) => handleChange('llm_model', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          >
                            {settings.llm_provider === 'openai' && (
                              <>
                                <option value="">Select a model</option>
                                <option value="gpt-4">GPT-4 (Most capable)</option>
                                <option value="gpt-4-turbo">GPT-4 Turbo (Faster)</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Budget)</option>
                              </>
                            )}
                            {settings.llm_provider === 'anthropic' && (
                              <>
                                <option value="">Select a model</option>
                                <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Recommended)</option>
                                <option value="claude-3-opus-20240229">Claude 3 Opus (Most capable)</option>
                                <option value="claude-3-sonnet-20240229">Claude 3 Sonnet (Balanced)</option>
                                <option value="claude-3-haiku-20240307">Claude 3 Haiku (Fast)</option>
                              </>
                            )}
                          </select>
                        )}
                        <p className="text-xs text-gray-500 mt-1">
                          {settings.llm_provider === 'ollama'
                            ? 'Type any model name from `ollama list` (suggestions provided)'
                            : 'Choose the AI model for analysis and chat'}
                        </p>
                      </div>
                    </>
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
                        {settings.llm_model && settings.llm_model.toLowerCase().includes('llava') && (
                          <div className="mt-2 pt-2 border-t border-blue-300">
                            <p className="text-xs text-blue-800 font-medium">
                              👁️ Vision Enabled:
                            </p>
                            <p className="text-xs text-blue-700 mt-1">
                              llava can analyze DownDetector chart images in chat! Ask about trends, patterns, or specific service outages shown in the charts.
                            </p>
                          </div>
                        )}
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
  );
}
