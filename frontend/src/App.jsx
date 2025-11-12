import React, { useState, useEffect } from 'react';
import SiteCard from './components/SiteCard';
import SiteFormModal from './components/SiteFormModal';
import HistoryModal from './components/HistoryModal';
import StatusBanner from './components/StatusBanner';
import GlobalPasteArea from './components/GlobalPasteArea';
import AdminSettingsModal from './components/AdminSettingsModal';
import ModuleConfigModal from './components/ModuleConfigModal';
import AdminChatPanel from './components/AdminChatPanel';
import { stateAPI, sitesAPI } from './services/api';

export default function App() {
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [isPaused, setIsPaused] = useState(false);

  // Status banner state - load from localStorage
  const [showBanner, setShowBanner] = useState(() => {
    const saved = localStorage.getItem('showStatusBanner');
    return saved !== null ? JSON.parse(saved) : true; // Default to true
  });

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [historyModalSite, setHistoryModalSite] = useState(null);
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [moduleConfigSite, setModuleConfigSite] = useState(null);
  const [showChatPanel, setShowChatPanel] = useState(false);

  // Global paste area state
  const [activePasteService, setActivePasteService] = useState(null);

  useEffect(() => {
    loadSites();
    const interval = setInterval(loadSites, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const loadSites = async () => {
    try {
      const response = await stateAPI.getAll();
      setSites(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load sites:', err);
      setError('Failed to load sites. Please check if the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSite = async (siteData) => {
    try {
      await sitesAPI.create(siteData);
      setShowAddModal(false);
      loadSites();
    } catch (err) {
      console.error('Failed to add site:', err);
      alert('Failed to add site: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleEditSite = (site) => {
    // Transform state object to site object (site_id -> id)
    const siteForEdit = {
      ...site,
      id: site.site_id || site.id,
      // Only include fields that can be edited
      feed_url: site.feed_url || '',
    };
    setEditingSite(siteForEdit);
  };

  const handleUpdateSite = async (siteData) => {
    try {
      await sitesAPI.update(siteData.id, siteData);
      setEditingSite(null);
      loadSites();
    } catch (err) {
      console.error('Failed to update site:', err);
      alert('Failed to update site: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteSite = async (siteId) => {
    if (!confirm('Are you sure you want to delete this site?')) {
      return;
    }

    try {
      await sitesAPI.delete(siteId);
      loadSites();
    } catch (err) {
      console.error('Failed to delete site:', err);
      alert('Failed to delete site: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handlePollNow = async (siteId) => {
    try {
      await sitesAPI.poll(siteId);
      // Refresh after a short delay to allow poll to complete
      setTimeout(loadSites, 2000);
    } catch (err) {
      console.error('Failed to poll site:', err);
      alert('Failed to poll site: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleTogglePause = async () => {
    try {
      if (isPaused) {
        await stateAPI.resume();
      } else {
        await stateAPI.pause();
      }
      setIsPaused(!isPaused);
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    }
  };

  const handleReload = async () => {
    try {
      await stateAPI.reload();
      loadSites();
    } catch (err) {
      console.error('Failed to reload:', err);
    }
  };

  const handleToggleBanner = () => {
    const newValue = !showBanner;
    setShowBanner(newValue);
    localStorage.setItem('showStatusBanner', JSON.stringify(newValue));
  };

  const filteredSites = sites.filter((site) => {
    if (filterStatus === 'all') return true;
    return site.status === filterStatus;
  });

  const statusCounts = {
    all: sites.length,
    operational: sites.filter((s) => s.status === 'operational').length,
    recently_resolved: sites.filter((s) => s.status === 'recently_resolved').length,
    degraded: sites.filter((s) => s.status === 'degraded').length,
    incident: sites.filter((s) => s.status === 'incident').length,
    maintenance: sites.filter((s) => s.status === 'maintenance').length,
    unknown: sites.filter((s) => s.status === 'unknown').length,
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600 mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Status Banner */}
      <StatusBanner
        sites={sites}
        isVisible={showBanner}
        onToggle={handleToggleBanner}
      />

      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Status Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">
                Monitoring {sites.length} service{sites.length !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowChatPanel(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
                aria-label="AI Chat Assistant"
                title="AI Chat Assistant"
              >
                💬 AI Chat
              </button>
              <button
                onClick={() => window.open('https://status.dayonebio.com/', '_blank')}
                className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-md hover:bg-teal-700 transition-colors"
                aria-label="View internal services status"
                title="View Day One Bio Internal Services"
              >
                🏢 Internal Services
              </button>
              <button
                onClick={() => setShowAdminModal(true)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                aria-label="Admin settings"
                title="Admin Settings"
              >
                ⚙️ Admin
              </button>
              <button
                onClick={handleToggleBanner}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  showBanner
                    ? 'bg-gray-700 text-white hover:bg-gray-800'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                aria-label={showBanner ? 'Hide status banner' : 'Show status banner'}
                title={showBanner ? 'Hide status banner' : 'Show status banner'}
              >
                {showBanner ? '📊 Hide Banner' : '📊 Show Banner'}
              </button>
              <button
                onClick={handleTogglePause}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isPaused
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-yellow-600 text-white hover:bg-yellow-700'
                }`}
                aria-label={isPaused ? 'Resume polling' : 'Pause polling'}
              >
                {isPaused ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={handleReload}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                aria-label="Reload all sites"
              >
                Reload
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
                aria-label="Add new site"
              >
                + Add Site
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
            {Object.entries(statusCounts).map(([status, count]) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-4 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-colors ${
                  filterStatus === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)} ({count})
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {filteredSites.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">
              {filterStatus === 'all'
                ? 'No sites configured. Click "Add Site" to get started.'
                : `No sites with status "${filterStatus}"`}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
            {filteredSites.map((site) => (
              <SiteCard
                key={site.site_id}
                site={site}
                onPollNow={handlePollNow}
                onViewHistory={setHistoryModalSite}
                onEdit={() => handleEditSite(site)}
                onDelete={() => handleDeleteSite(site.site_id)}
                onRequestPaste={() => setActivePasteService(site)}
                onConfigureModules={() => setModuleConfigSite(site)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Modals */}
      <SiteFormModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddSite}
      />

      <SiteFormModal
        isOpen={!!editingSite}
        onClose={() => setEditingSite(null)}
        onSubmit={handleUpdateSite}
        site={editingSite}
      />

      <HistoryModal
        isOpen={!!historyModalSite}
        onClose={() => setHistoryModalSite(null)}
        site={historyModalSite}
      />

      <AdminSettingsModal
        isOpen={showAdminModal}
        onClose={() => setShowAdminModal(false)}
      />

      <ModuleConfigModal
        isOpen={!!moduleConfigSite}
        onClose={() => setModuleConfigSite(null)}
        site={moduleConfigSite}
      />

      {/* AI Chat Panel */}
      <AdminChatPanel
        isOpen={showChatPanel}
        onClose={() => setShowChatPanel(false)}
      />

      {/* Global Paste Area */}
      <GlobalPasteArea
        activeService={activePasteService}
        onClose={() => setActivePasteService(null)}
        onUploadSuccess={() => {
          setActivePasteService(null);
          loadSites();
        }}
      />
    </div>
  );
}
