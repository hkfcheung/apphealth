import React, { useState, useEffect } from 'react';
import { sitesAPI } from '../services/api';
import StatusBadge from './StatusBadge';
import { formatDateTime } from '../utils/helpers';

export default function HistoryModal({ isOpen, onClose, site }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedReading, setSelectedReading] = useState(null);

  useEffect(() => {
    if (isOpen && site) {
      loadHistory();
    }
  }, [isOpen, site]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await sitesAPI.getHistory(site.site_id, 50);
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !site) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold">History: {site.display_name}</h2>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading history...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No history available
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((reading) => (
                <div
                  key={reading.id}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() =>
                    setSelectedReading(
                      selectedReading?.id === reading.id ? null : reading
                    )
                  }
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <StatusBadge status={reading.status} />
                        <span className="text-xs text-gray-500 font-mono uppercase">
                          {reading.source_type}
                        </span>
                        <span className="text-sm text-gray-600">
                          {formatDateTime(reading.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">{reading.summary}</p>
                      {reading.error_message && (
                        <p className="text-sm text-red-600 mt-2">
                          Error: {reading.error_message}
                        </p>
                      )}
                    </div>
                  </div>

                  {selectedReading?.id === reading.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">
                        Raw Data:
                      </h4>
                      <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto">
                        {JSON.stringify(reading.raw_snapshot, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
